import re

from django.core import mail
from django.test import TestCase
from django.contrib.auth.models import Group as AuthGroup
from django.urls import get_resolver
from django.contrib.messages import ERROR, get_messages, INFO
from django.contrib.messages.storage.base import Message

from core.admin import *
from core.models import *
from core.tests.utils import *


class UnverifiedUserAdminTests(TestCase):
    def test_unverified_user_model_registered(self):
        """Should return a UnverifiedUserModelAdmin obj for the model UnverifiedUser in admin_site.url"""
        unverified_user_admin = admin_site._registry.get(UnverifiedUser)
        self.assertIsNotNone(unverified_user_admin)
        self.assertEquals(unverified_user_admin.__class__, UnverifiedUserAdmin)


class UserAdminTest(TestCase):
    def setUp(self):
        self.admin = Admin.objects.create(
            user=User.objects.create(first_name="", last_name="", email="", phone=""),
            permission1=False,
            permissionx=False,
        )
        self.user_admin = UserAdmin(User, admin_site)
        self.consultant = create_consultant()
        self.site = AdminSite()

    def test_user_model_registered(self):
        """Should return a UserModelAdmin obj for the model User in admin_site.url"""
        user_admin = admin_site._registry.get(User)
        self.assertIsNotNone(user_admin)
        self.assertEquals(user_admin.__class__, UserAdmin)

    def test_admin_redirect_to_user1(self):
        # testing url redirects on admin: 301 (moved permanently), 302 (found/moved temporarily)
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.demographic = create_demographic(self.assessment)
        response = self.client.get('/admin/core/user/1/change')
        expected_url = '/admin/core/user/1/change/'
        self.assertRedirects(response, expected_url, status_code=301,
                             target_status_code=302, msg_prefix='', fetch_redirect_response=True)

    def test_has_view_permission_method_when_obj_is_not_none(self):
        """returns whether the user has obj view permission"""
        user = create_user()
        request = HttpRequest()
        request.user = self.consultant

        assign_perm('view_user', self.consultant, user)
        self.assertTrue(self.user_admin.has_view_permission(request, user))

        remove_perm('view_user', self.consultant, user)
        self.assertFalse(self.user_admin.has_view_permission(request, user))

    def test_get_queryset_method(self):
        user = create_user()
        assign_perm('view_user', self.consultant, user)

        request = HttpRequest()
        request.user = self.consultant  # faking login

        request.user.is_superuser = True
        qs = self.user_admin.get_queryset(request)
        self.assertQuerysetEqual(qs, User.objects.all(), transform=lambda x: x, ordered=False)


class AccessCodeAdminTests(TestCase):
    def test_access_code_model_is_registered(self):
        """there should be an AccessCodeAdmin obj for the model AccessCode in admin_site.url"""
        access_code_admin = admin_site._registry.get(AccessCode)
        self.assertIsNotNone(access_code_admin)
        self.assertEquals(access_code_admin.__class__, AccessCodeAdmin)


class AssessmentAdminTests(TestCase):
    def setUp(self):
        self.consultant = create_consultant()
        self.assessment_admin = AssessmentAdmin(Assessment, admin_site)

    def test_assessment_model_registered(self):
        """should be a AssessmentAdmin obj for the model Assessment in admin_site.url"""
        assessment_admin = admin_site._registry.get(Assessment)
        self.assertIsNotNone(assessment_admin)
        self.assertEquals(assessment_admin.__class__, AssessmentAdmin)

    def test_has_view_permission_method_when_obj_is_none(self):
        """return True"""
        request = HttpRequest()
        request.user = self.consultant
        self.assertTrue(self.assessment_admin.has_view_permission(request))

    def test_has_view_permission_method_when_obj_is_not_none(self):
        """returns whether the user has obj view permission"""
        user = create_user()
        assessment = create_assessment(user)
        request = HttpRequest()
        request.user = self.consultant

        assign_perm('view_assessment', self.consultant, assessment)
        self.assertTrue(self.assessment_admin.has_view_permission(request, assessment))

        remove_perm('view_assessment', self.consultant, assessment)
        self.assertFalse(self.assessment_admin.has_view_permission(request, assessment))

    def test_accessing_assessment_changelist_view_when_consultant_logged_in(self):
        """Status code is 200"""
        self.client.force_login(self.consultant)
        response = self.client.get(reverse('admin:core_assessment_changelist'))
        self.assertEquals(response.status_code, 200)

    def test_accessing_assessment_change_view_when_logged_in_consultant_has_no_view_permission(self):
        """Status code is not 200"""
        self.client.force_login(self.consultant)
        assessment = create_assessment(user=create_user())
        assert self.consultant.has_perm('view_assessment', assessment) is False  # sanity check

        response = self.client.get(reverse('admin:core_assessment_change', kwargs=dict(object_id=assessment.pk)))
        self.assertNotEquals(response.status_code, 200)

    def test_accessing_assessment_change_view_when_logged_in_consultant_has_view_permission(self):
        """Status code is 200"""
        self.client.force_login(self.consultant)
        assessment = create_assessment(user=create_user())
        assign_perm('view_assessment', self.consultant, assessment)
        assert self.consultant.has_perm('view_assessment', assessment) is True  # sanity check

        response = self.client.get(reverse('admin:core_assessment_change', kwargs=dict(object_id=assessment.pk)))
        self.assertEquals(response.status_code, 200)

    def test_get_queryset_method(self):
        """Return only the assessments the consultant has permission for, and for superuser return all"""
        user = create_user()
        assessment_with_view_permission_1 = create_assessment(user=user)
        assign_perm('view_assessment', self.consultant, assessment_with_view_permission_1)
        assessment_with_view_permission_2 = create_assessment(user=user)
        assign_perm('view_assessment', self.consultant, assessment_with_view_permission_2)
        assessment_without_view_permission = create_assessment(user=user)

        request = HttpRequest()
        request.user = self.consultant  # faking login
        qs = self.assessment_admin.get_queryset(request)
        self.assertNotIn(assessment_without_view_permission, qs)
        self.assertQuerysetEqual(qs, {assessment_with_view_permission_1, assessment_with_view_permission_2},
                                 transform=lambda x: x, ordered=False)

        request.user.is_superuser = True
        qs = self.assessment_admin.get_queryset(request)
        self.assertQuerysetEqual(qs, Assessment.objects.all(), transform=lambda x: x, ordered=False)

    def test_demo_link_method_when_demographic_is_none(self):
        """return empty string"""
        user = create_user()
        assessment = create_assessment(user)
        expected = ''
        self.assertEquals(expected, self.assessment_admin.demo_link(assessment))

    def test_demo_link_method_when_demographic_is_not_none(self):
        """return link to demographic"""
        user = create_user()
        assessment = create_assessment(user)
        demographic = create_demographic(assessment)
        expected = mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:core_demographic_change", kwargs=(dict(object_id=demographic.pk))), demographic))
        self.assertEquals(expected, self.assessment_admin.demo_link(assessment))

    def test_score_link_method_when_score_is_none(self):
        """return empty string"""
        user = create_user()
        assessment = create_assessment(user)
        expected = ''
        self.assertEquals(expected, self.assessment_admin.score_link(assessment))

    def test_score_link_method_when_score_is_not_none(self):
        """return link to score"""
        user = create_user()
        assessment = create_assessment(user)
        score = Score.objects.create(assessment=assessment)
        score.save()
        demographic = create_demographic(assessment)
        expected = mark_safe(
            '<a href="{}">{}</a>'.format(reverse("admin:core_score_change", kwargs=(dict(object_id=score.pk))), score))
        self.assertEquals(expected, self.assessment_admin.score_link(assessment))

    def test_user_link_method_when_user_is_none(self):
        """return empty string"""
        user = create_user()
        assessment = create_assessment(user=user)
        user.delete()
        user.save()
        assessment = Assessment.objects.get(pk=assessment.pk)  # refetching since assessment's user has been altered
        expected = 'User has been deleted'
        self.assertEquals(expected, self.assessment_admin.user_link(assessment))

    def test_user_link_method_when_score_is_not_none(self):
        """return link to user"""
        user = create_user()
        assessment = create_assessment(user)
        expected = mark_safe(
            '<a href="{}">{}</a>'.format(reverse("admin:core_user_change", kwargs=(dict(object_id=user.pk))), user))
        self.assertEquals(expected, self.assessment_admin.user_link(assessment))

    def test_recalculate_score_method_when_score_is_none(self):
        """create new score object with the correct values for the subscores"""
        assessment = create_assessment(user=create_user())
        Response.objects.create(assessment=assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        queryset = Assessment.objects.filter(pk=assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        self.assessment_admin.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assertIsNotNone(assessment.score)
        try:
            score = assessment.score
        except Score.DoesNotExist:
            self.fail('Score object was not created')
        self.assertEquals(score.strength_total, 8)
        gender_score = Gender_Score.objects.get(score=score)
        self.assertEquals(gender_score.strength, 4)
        race_score = Race_Score.objects.get(score=score)
        self.assertEquals(race_score.strength, 4)

    # in the event that all the subscores were deleted but we still have the responses
    def test_recalc_when_all_subscore_missing(self):
        user = create_user()
        assessment = create_assessment(user)
        Response.objects.create(assessment=assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=user.pk, assessment_id=assessment.pk)))
        Score.objects.filter(assessment=assessment).delete()
        Gender_Score.objects.filter(score__assessment=assessment).delete()
        Religion_Score.objects.filter(score__assessment=assessment).delete()
        Class_Score.objects.filter(score__assessment=assessment).delete()
        Disability_Score.objects.filter(score__assessment=assessment).delete()
        Race_Score.objects.filter(score__assessment=assessment).delete()
        Sexual_Orientation_Score.objects.filter(score__assessment=assessment).delete()
        Culture_Score.objects.filter(score__assessment=assessment).delete()
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        assessment = Assessment.objects.get(pk=assessment.pk)
        self.assertTrue(assessment.score is not None)
        self.assertEquals(assessment.score.strength_total, 8)
        self.assertEquals(assessment.score.Race_Score.strength, 4)
        self.assertEquals(assessment.score.Gender_Score.strength, 4)
        self.assertEquals(assessment.score.Religion_Score.strength, 0)
        self.assertEquals(assessment.score.Class_Score.strength, 0)
        self.assertEquals(assessment.score.Disability_Score.strength, 0)
        self.assertEquals(assessment.score.Sexual_Orientation_Score.strength, 0)
        self.assertEquals(assessment.score.Culture_Score.strength, 0)

        # in the event that some of the subscores were deleted but we still have the responses
    def test_recalc_when_some_subscore_missing(self):
        user = create_user()
        assessment = create_assessment(user)
        Response.objects.create(assessment=assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=user.pk, assessment_id=assessment.pk)))
        Score.objects.filter(assessment=assessment).delete()
        Religion_Score.objects.filter(score__assessment=assessment).delete()
        Class_Score.objects.filter(score__assessment=assessment).delete()
        Disability_Score.objects.filter(score__assessment=assessment).delete()
        Race_Score.objects.filter(score__assessment=assessment).delete()
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        assessment = Assessment.objects.get(pk=assessment.pk)
        self.assertTrue(assessment.score is not None)
        self.assertEquals(assessment.score.strength_total, 8)
        self.assertEquals(assessment.score.Race_Score.strength, 4)
        self.assertEquals(assessment.score.Gender_Score.strength, 4)
        self.assertEquals(assessment.score.Religion_Score.strength, 0)
        self.assertEquals(assessment.score.Class_Score.strength, 0)
        self.assertEquals(assessment.score.Disability_Score.strength, 0)
        self.assertEquals(assessment.score.Sexual_Orientation_Score.strength, 0)
        self.assertEquals(assessment.score.Culture_Score.strength, 0)


    def test_method_detailed_view_link_when_obj_pk_is_none(self):
        """Return empty string"""
        assessment = Assessment(user=create_user(), email='')
        assert assessment.pk is None # sanity check
        self.assertEquals('', self.assessment_admin.detailed_view_link(assessment))

    def test_method_detailed_view_link_when_obj_pk_is_not_none(self):
        """Return empty string"""
        assessment = create_assessment(user=create_user())
        detailed_view_link = reverse('admin:core_assessment_detailed_view', kwargs=dict(assessment_pk=assessment.pk))
        self.assertIn(detailed_view_link, self.assessment_admin.detailed_view_link(assessment))


class DemographicAdminTest(TestCase):
    def setUp(self):
        self.admin = Admin.objects.create(
            user=User.objects.create(first_name="", last_name="", email="", phone=""),
            permission1=False,
            permissionx=False,
        )
        self.site = AdminSite()
        self.consultant = create_consultant()
        self.demographic_admin = admin_site._registry.get(Demographic)

    def test_has_view_permission_method_when_obj_is_not_none(self):
        """returns whether the user has obj view permission"""
        user = create_user()
        assessment = create_assessment(user)
        demographic = create_demographic(assessment)
        request = HttpRequest()
        request.user = self.consultant

        assign_perm('view_demographic', self.consultant, demographic)
        self.assertTrue(self.demographic_admin.has_view_permission(request, demographic))

        remove_perm('view_demographic', self.consultant, demographic)
        self.assertFalse(self.demographic_admin.has_view_permission(request, demographic))

    def test_get_queryset_method(self):
        user = create_user()
        assessment = create_assessment(user)
        demographic_with_view_permission_1 = create_demographic(assessment=assessment)
        assign_perm('view_demographic', self.consultant, demographic_with_view_permission_1)

        request = HttpRequest()
        request.user = self.consultant  # faking login  

        request.user.is_superuser = True
        qs = self.demographic_admin.get_queryset(request)
        self.assertQuerysetEqual(qs, Demographic.objects.all(), transform=lambda x: x, ordered=False)

    def test_admin_redirect_to_demographic_obj(self):
        # testing url redirects on admin: 301 (moved permanently), 302 (found/moved temporarily)
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.demographic = create_demographic(self.assessment)
        response = self.client.get('/admin/core/demographic/1/change')
        expected_url = '/admin/core/demographic/1/change/'
        self.assertRedirects(response, expected_url, status_code=301,
                             target_status_code=302, msg_prefix='', fetch_redirect_response=True)

    def test_demographic_model_is_registered(self):
        """Should find a DemographicAdmin object for Demographic model in admin_site's registry"""
        demographic_admin = admin_site._registry.get(Demographic)
        self.assertIsNotNone(demographic_admin)
        self.assertEquals(demographic_admin.__class__, DemographicAdmin)

    def test_assessment_link_method(self):
        assessment = create_assessment(user=create_user())
        demographic = create_demographic(assessment=assessment)
        expected = mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:core_assessment_change", args=(assessment.pk,)), assessment))
        self.assertEquals(expected, self.demographic_admin.assessment_link(demographic))


class QuestionAdminTests(TestCase):
    def test_question_model_is_registered(self):
        """there should be a QuestionAdmin obj for the model Question in admin_site.url"""
        question_admin = admin_site._registry.get(Question)
        self.assertIsNotNone(question_admin)
        self.assertEquals(question_admin.__class__, QuestionAdmin)

    def test_change_view(self):
        login_as_super_user(self.client)
        question = create_question()
        response = self.client.get(reverse('admin:core_question_change', args=(question.pk,)))
        self.assertEquals(response.status_code, 200)


class ScoreAdminTest(TestCase):
    def setUp(self):
        self.admin = Admin.objects.create(
            user=User.objects.create(first_name="", last_name="", email="", phone=""),
            permission1=False,
            permissionx=False,
        )
        self.site = AdminSite()
        self.score_admin = ScoreAdmin(Score, admin_site=admin_site)

    def test_score_model_is_registered(self):
        """there should be a ScoreAdmin obj for the model Score in admin_site.url"""
        score_admin = admin_site._registry.get(Score)
        self.assertIsNotNone(score_admin)
        self.assertEquals(score_admin.__class__, ScoreAdmin)

    def test_admin_recalculate_score(self):
        # makes sure the recalculating score button returns the correct, matching score
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = len(Question.objects.all())
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)

        a = AssessmentAdmin(Assessment, AdminSite())
        queryset = Assessment.objects.filter(pk = 1)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assertEqual(self.score.strength_total, 8)

    def test_admin_recalculate_subscore(self):
        # makes sure the recalculating score button returns the correct, matching subscores
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = len(Question.objects.all())
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        self.race_score = Race_Score.objects.get(score=self.score)
        self.gender_score = Gender_Score.objects.get(score=self.score)

        a = AssessmentAdmin(Assessment, AdminSite())
        queryset = Assessment.objects.filter(pk = 1)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assertEqual(self.gender_score.leveraged, 0)

    def test_admin_comprehensive_score_recalculation(self):
        # goes through each path in thescore calculation to make sure it works, similar test in test_views
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = len(Question.objects.all())
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()

        i = 1
        # social culture location
        for scl in ["Gender", "Race", "Religion", "LGBQ+", "Disability", "Culture", "Class"]:
            # power perspective
            for pp in ["Sensitivity", "Oneness", "Strength", "Appreciation", "Leveraged"]:
                # amount of agreement/response level... a single set of the response level to a single attribute scores 10 points
                for rl in ["strongly agree", "agree more than disagree", "agree and disagree about the same",
                           "disagree more than agree", "strongly disagree"]:
                    Response.objects.create(assessment=self.assessment, question_number=i, response=rl,
                                            power_perspective=pp, sociocultural_location=scl)
                    i = i + 1
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        a = AssessmentAdmin(Assessment, AdminSite())
        queryset = Assessment.objects.filter(pk = 1)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        # a few checks to make sure things got added up properly
        self.race_score = Race_Score.objects.get(score=self.score)
        self.assertEqual(self.race_score.strength, 10)
        self.assertEqual(self.race_score.oneness, 10)
        self.assertEqual(self.race_score.appreciation, 10)
        self.assertEqual(self.race_score.sensitivity, 10)
        self.assertEqual(self.race_score.leveraged, 10)

        self.gender_score = Gender_Score.objects.get(score=self.score)
        self.assertEqual(self.gender_score.strength, 10)
        self.assertEqual(self.gender_score.oneness, 10)
        self.assertEqual(self.gender_score.appreciation, 10)
        self.assertEqual(self.gender_score.sensitivity, 10)
        self.assertEqual(self.gender_score.leveraged, 10)

        self.class_score = Class_Score.objects.get(score=self.score)
        self.assertEqual(self.class_score.strength, 10)
        self.assertEqual(self.class_score.oneness, 10)
        self.assertEqual(self.class_score.appreciation, 10)
        self.assertEqual(self.class_score.sensitivity, 10)
        self.assertEqual(self.class_score.leveraged, 10)

        self.culture_score = Culture_Score.objects.get(score=self.score)
        self.assertEqual(self.culture_score.strength, 10)
        self.assertEqual(self.culture_score.oneness, 10)
        self.assertEqual(self.culture_score.appreciation, 10)
        self.assertEqual(self.culture_score.sensitivity, 10)
        self.assertEqual(self.culture_score.leveraged, 10)

        self.disability_score = Disability_Score.objects.get(score=self.score)
        self.assertEqual(self.disability_score.strength, 10)
        self.assertEqual(self.disability_score.oneness, 10)
        self.assertEqual(self.disability_score.appreciation, 10)
        self.assertEqual(self.disability_score.sensitivity, 10)
        self.assertEqual(self.disability_score.leveraged, 10)

        self.religion_score = Religion_Score.objects.get(score=self.score)
        self.assertEqual(self.religion_score.strength, 10)
        self.assertEqual(self.religion_score.oneness, 10)
        self.assertEqual(self.religion_score.appreciation, 10)
        self.assertEqual(self.religion_score.sensitivity, 10)
        self.assertEqual(self.religion_score.leveraged, 10)

        self.sex_score = Sexual_Orientation_Score.objects.get(score=self.score)
        self.assertEqual(self.sex_score.strength, 10)
        self.assertEqual(self.sex_score.oneness, 10)
        self.assertEqual(self.sex_score.appreciation, 10)
        self.assertEqual(self.sex_score.sensitivity, 10)
        self.assertEqual(self.sex_score.leveraged, 10)

        # 7 social culture locations
        # 10 points for each run in the innermost for loop
        # 7*10 = 70 points in each area
        self.assertEqual(self.score.strength_total, 70)
        self.assertEqual(self.score.oneness_total, 70)
        self.assertEqual(self.score.leveraged_total, 70)
        self.assertEqual(self.score.appreciation_total, 70)
        self.assertEqual(self.score.sensitivity_total, 70)

    def test_assessment_link_method(self):
        assessment = create_assessment(user=create_user())
        score = Score.objects.create(assessment=assessment)
        expected = mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:core_assessment_change", args=(assessment.pk,)), assessment))
        self.assertEquals(expected, self.score_admin.assessment_link(score))


class SubScoreAdminTest(TestCase):
    sub_score_models = [Gender_Score, Race_Score, Culture_Score, Religion_Score, Sexual_Orientation_Score,
                        Disability_Score, Class_Score]

    def setUp(self):
        self.sub_score_model_to_model_admin_map = {}
        for model in self.sub_score_models:
            self.sub_score_model_to_model_admin_map[model] = SubScoreAdmin(model, admin_site=admin_site)

    def test_sub_score_models_are_registered(self):
        """Should find a SubScoreAdmin object for each SubScore model in admin_site's registry"""
        for model in self.sub_score_models:
            with self.subTest(model=model):
                sub_score_admin = admin_site._registry.get(model)
                self.assertIsNotNone(sub_score_admin)
                self.assertEquals(sub_score_admin.__class__, SubScoreAdmin)

    def test_score_link_methods_for_each_sub_score_model(self):
        """return link to score"""
        user = create_user()
        assessment = create_assessment(user)
        score = Score.objects.create(assessment=assessment)
        score.save()
        expected = mark_safe(
            '<a href="{}">{}</a>'.format(reverse("admin:core_score_change", kwargs=(dict(object_id=score.pk))),
                                         score))
        for model, model_admin in self.sub_score_model_to_model_admin_map.items():
            sub_score = model.objects.create(score=score)
            with self.subTest(model=model):
                self.assertEquals(expected, model_admin.score_link(sub_score))


class ConsultantAdminTest(TestCase):
    def setUp(self):
        admin = AuthUser.objects.create(
            username='admin',
            password='password',
            email='admin@email.com',
            is_superuser=True,
            is_staff=True
        )
        admin.save()
        self.client.force_login(admin)

    def test_consultant_model_is_registered(self):
        """there should be a ConsultantAdmin obj for the model Consultant in admin_site.url"""
        consultant_admin = admin_site._registry.get(Consultant)
        self.assertIsNotNone(consultant_admin)
        self.assertEquals(consultant_admin.__class__, ConsultantAdmin)

    def test_response_add(self):
        # redirects to core_consultant_changelist and sends email with verify_registration_completion_link

        consultant_email = 'email@email.com'
        response = self.client.post(reverse('admin:core_consultant_add'), data={'email': consultant_email}, follow=True)

        self.assertRedirects(response, reverse('admin:core_consultant_changelist'))

        self.assertEquals(len(mail.outbox), 1)
        sent_email = mail.outbox[-1]
        self.assertEquals(len(sent_email.to), 1)
        self.assertEquals(sent_email.to[0], consultant_email)

        verify_registration_completion_link_url_pattern = r'http://testserver(?P<verify_registration_completion_link_url>/[\S]+)'
        m = re.search(verify_registration_completion_link_url_pattern, sent_email.body)
        self.assertIsNotNone(m)
        resolver = get_resolver()
        resolver_match = resolver.resolve(m.group('verify_registration_completion_link_url'))
        self.assertEquals(resolver_match.view_name, 'admin:core_consultant_verify_registration_completion_link')
        new_consultant = Consultant.objects.get(email=consultant_email)
        self.assertEquals(resolver_match.kwargs['token'], default_token_generator.make_token(new_consultant))
        self.assertEquals(resolver_match.kwargs['uidb64'], urlsafe_base64_encode(force_bytes(new_consultant.pk)))


class RecalculationTest(TestCase):

    def setUp(self):
        self.user = create_user()
        self.user.save()
        self.assessment = create_assessment(self.user)
        self.assessment.save()
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()

    def test_regenerate_pdf_all_scores_present(self):
        i = 1
        # social culture location
        for scl in ["Gender", "Race", "Religion", "LGBQ+", "Disability", "Culture", "Class"]:
            # power perspective
            for pp in ["Sensitivity", "Oneness", "Strength", "Appreciation", "Leveraged"]:
                # amount of agreement/response level... a single set of the response level to a single attribute scores 10 points
                for rl in ["strongly agree", "agree more than disagree", "agree and disagree about the same",
                           "disagree more than agree", "strongly disagree"]:
                    Response.objects.create(assessment=self.assessment, question_number=i, response=rl,
                                            power_perspective=pp, sociocultural_location=scl)
                    i = i + 1
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.assessment.PDF = None
        self.assessment.save()
        self.assertFalse(bool(self.assessment.PDF))
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=self.assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had PDF(s) regenerated successfully')
        a.remake_pdf(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assessment = Assessment.objects.get(pk=self.assessment.pk)
        self.assertTrue(bool(self.assessment.PDF))

    def test_regenerate_pdf_all_scores_present_no_user(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.assessment.PDF = None
        self.assessment.user = None
        self.assessment.save()
        self.assertIsNone(self.assessment.user)
        self.assertFalse(bool(self.assessment.PDF))
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=self.assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had PDF(s) regenerated successfully')
        a.remake_pdf(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assessment = Assessment.objects.get(pk=self.assessment.pk)
        self.assertTrue(bool(self.assessment.PDF))

    def test_regenerate_pdf_missing_score_failure(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        Score.objects.filter(assessment=self.assessment).delete()
        self.assessment.PDF = None
        self.assessment.save()
        self.assertFalse(bool(self.assessment.PDF))
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=self.assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Some PDFs could not be regenerated as score data is missing! Please recalculate the scores for any assessments that still do not have any PDFs and try again. Other PDFs have been regenerated successfully.')
        a.remake_pdf(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assessment = Assessment.objects.get(pk=self.assessment.pk)
        self.assertFalse(bool(self.assessment.PDF))

    def test_regenerate_pdf_missing_SUBscore_failure(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        Gender_Score.objects.filter(score__assessment=self.assessment).delete()
        self.assessment.PDF = None
        self.assessment.save()
        self.assertFalse(bool(self.assessment.PDF))
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=self.assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Some PDFs could not be regenerated as score data is missing! Please recalculate the scores for any assessments that still do not have any PDFs and try again. Other PDFs have been regenerated successfully.')
        a.remake_pdf(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assessment = Assessment.objects.get(pk=self.assessment.pk)
        self.assertFalse(bool(self.assessment.PDF))

    # recalculating score when score was already correct
    def test_recalc_correct_score(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=self.assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assertEqual(self.score.strength_total, 8)

    def test_recalc_diff_score(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly disagree",
                                power_perspective="Strength", sociocultural_location="Race")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=self.assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assertTrue(self.assessment.score is not None)

    # in the event that the score was incorrectly changed to 0, score recalculation will repopulate scores
    def test_recalc_from_zero(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = 0
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=self.assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assertTrue(self.assessment.score is not None)

    # make sure recalculating the score doesn't create another score object entirely
    def test_recalc_score_no_addition(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=self.assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assertNotEqual(Score.objects.count(), 2)

    def test_recalc_main_score(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Sensitivity", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly agree",
                                power_perspective="Sensitivity", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        a = AssessmentAdmin(Assessment, AdminSite)
        queryset = Assessment.objects.filter(pk=self.assessment.pk)
        request = MockHttpRequest()
        expected_message = Message(level=INFO, message='Selected assessment(s) had score(s) regenerated')
        a.recalc_score_button(request,queryset)
        messages = list(get_messages(request))
        self.assertIn(expected_message, messages)
        self.assertEqual(self.score.sensitivity_total, 8)


class ResponseAdminTests(TestCase):
    def setUp(self):
        self.response_admin = ResponseAdmin(Response, admin_site=admin_site)

    def test_score_response_is_registered(self):
        """there should be a ResponseAdmin obj for the model Response in admin_site.url"""
        response_admin = admin_site._registry.get(Response)
        self.assertIsNotNone(response_admin)
        self.assertEquals(response_admin.__class__, ResponseAdmin)

    def test_user_link_method_when_user_is_none(self):
        """return empty string"""
        user = create_user()
        assessment = create_assessment(user=user)
        response = create_response(assessment)
        user.delete()
        user.save()
        response = Response.objects.get(pk=response.pk)  # refetching since assessment's user has been altered
        expected = 'User has been deleted'
        self.assertEquals(expected, self.response_admin.user_link(response))

    def test_user_link_method_when_score_is_not_none(self):
        """return link to user"""
        user = create_user()
        assessment = create_assessment(user)
        response = create_response(assessment)
        expected = mark_safe(
            '<a href="{}">{}</a>'.format(reverse("admin:core_user_change", kwargs=(dict(object_id=user.pk))), user))
        self.assertEquals(expected, self.response_admin.user_link(response))


class ViewOnlyAdminTests(TestCase):
    def setUp(self):
        self.view_Only_Admin = ViewOnlyAdminAdmin(ViewOnlyAdmin, admin_site=admin_site)
        self.group = AuthGroup.objects.get(name="View-Only Admin Group")
        self.client = Client()
        self.username = 'test_org'
        self.password = 'test_password'
        self.org = ViewOnlyAdmin.objects.create(username=self.username, email="org@test.com",
                                                is_staff=True)
        self.org.set_password(self.password)
        self.org.save()

        admin = AuthUser.objects.create(
            username='admin',
            password='password',
            email='admin@email.com',
            is_superuser=True,
            is_staff=True
        )
        admin.save()
        self.client.force_login(admin)

    def test_View_Only_Admin_model_is_registered(self):
        """there should be a View_Only_Admin obj for the model View_Only_Admins in admin_site.url"""
        view_Only_Admin = admin_site._registry.get(ViewOnlyAdmin)
        self.assertIsNotNone(view_Only_Admin)
        self.assertEquals(view_Only_Admin.__class__, ViewOnlyAdminAdmin)

    def test_View_Only_Admin_view_assessment_perm(self):
        # View_Only_Admins should have permission to view assessments
        self.assertTrue(self.org.has_perm('core.view_assessment'))

    def test_View_Only_Admin_change_assessment_perm(self):
        # View_Only_Admins do not have permission to change assessments
        self.assertFalse(self.org.has_perm('core.change_assessment'))

    def test_response_add(self):
        voa_email = 'email@email.com'
        response = self.client.post(reverse('admin:core_view_only_admin_add'), data={'email': voa_email}, follow=True)

        self.assertRedirects(response, reverse('admin:core_view_only_admin_changelist'))

        self.assertEquals(len(mail.outbox), 1)
        sent_email = mail.outbox[-1]
        self.assertEquals(len(sent_email.to), 1)
        self.assertEquals(sent_email.to[0], voa_email)

        verify_registration_completion_link_url_pattern = r'http://testserver(?P<verify_registration_completion_link_url>/[\S]+)'
        m = re.search(verify_registration_completion_link_url_pattern, sent_email.body)
        self.assertIsNotNone(m)
        resolver = get_resolver()
        resolver_match = resolver.resolve(m.group('verify_registration_completion_link_url'))
        self.assertEquals(resolver_match.view_name, 'admin:core_view_only_admin_verify_registration_completion_link')
        new_view_only_admin = ViewOnlyAdmin.objects.get(email=voa_email)
        self.assertEquals(resolver_match.kwargs['token'], default_token_generator.make_token(new_view_only_admin))
        self.assertEquals(resolver_match.kwargs['uidb64'], urlsafe_base64_encode(force_bytes(new_view_only_admin.pk)))
