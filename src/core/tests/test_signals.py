from django.test import TestCase
from django.contrib.auth.models import Group as AuthGroup

from core.models import *
from core.tests.utils import *


class ConsultantPostSaveSignalHandlerTests(TestCase):
    def setUp(self):
        self.group = AuthGroup.objects.get(name="Consultants")
        self.client = Client()
        self.username = 'test_consultant'
        self.password = 'test_password'
        self.consultant = Consultant.objects.create(username=self.username, email="test@test.com",
                                                    is_staff=True)
        self.consultant.set_password(self.password)
        self.consultant.save()

    def test_consultant_in_consultants_group(self):
        # should be a member of consultant group
        self.assertIn(self.group, self.consultant.groups.all())

    def test_consultants_can_access_admin_page(self):
        # users in group gets access to admin page
        response = self.client.post('/admin/login/?next=/admin/',
                                    data=dict(username=self.username, password=self.password))
        self.assertEqual(response.status_code, 302)
        self.assertEquals(response.url, '/admin/')

    def test_consultant_has_perm_to_view_all_demographics(self):
        # users in the consultant group do not have ability to view all demographics data
        self.assertFalse(self.consultant.has_perm('core.view_demographic'))

    def test_consultant_has_perm_to_view_score(self):
        # users in the consultant group have the ability to view scores of users
        self.assertTrue(self.consultant.has_perm('core.view_score'))

    def test_consultant_has_perm_to_change_user(self):
        # users in the consultant group DO NOT have ability to change user data
        self.assertFalse(self.consultant.has_perm('core.change_user'))

    def test_consultant_has_perm_to_delete_user(self):
        # users in the consultant group DO NOT have ability to delete scores
        self.assertFalse(self.consultant.has_perm('core.delete_score'))

    def test_consultant_has_perm_to_view_user_data(self):
        # consultant users do not have permission to view all user data
        self.assertFalse(self.consultant.has_perm('core.view_user'))

    def test_consultant_has_perm_to_change_score(self):
        # consultant users shouldn't be able to change scores of any user
        self.assertFalse(self.consultant.has_perm('core.change_score'))

    def test_consultant_no_object_perm(self):
        # check that consultants do not have object permission if it's not assigned to them
        consultant = self.consultant
        a1 = Assessment.objects.create(email='bill@gmail.com')
        self.assertFalse(consultant.has_perm('core.view_assessment', a1))


class AssessmentConsultantM2MChangedSignalHandlerTests(TestCase):
    def setUp(self):
        # created 3 consultants for many-to-many field
        self.consultant1 = Consultant.objects.create(username='consultant1', email="test@test.com",
                                                     is_staff=True)
        self.consultant2 = Consultant.objects.create(username='consultant2', email="test2@test.com",
                                                     is_staff=True)
        self.consultant3 = Consultant.objects.create(username='consultant3', email="test3@test.com",
                                                     is_staff=True)
        # sample assessment 1
        self.assessment1 = Assessment.objects.create(user=None)
        self.assessment1.consultants.add(self.consultant1)
        self.assessment1.consultants.add(self.consultant3)
        self.assessment1.save()  # saving will trigger the m2m_changed signal and run the post_add action

        # sample assessment 2
        self.assessment2 = Assessment.objects.create(user=None)
        self.assessment2.consultants.add(self.consultant1)
        self.assessment2.consultants.add(self.consultant2)
        self.assessment2.save()  # saving will trigger the m2m_changed signal and run the post_add action

    def test_consultant_1_has_perm_on_assessment1(self):
        self.assertTrue(self.consultant1.has_perm('view_assessment', self.assessment1))

    def test_consultant_2_does_not_have_perm_on_assessment1(self):
        self.assertFalse(self.consultant2.has_perm('view_assessment', self.assessment1))

    def test_consultant_2_has_perm_on_assessment2(self):
        self.assertTrue(self.consultant2.has_perm('view_assessment', self.assessment2))

    def test_assessment_added_to_consultant_s_assessment_set(self):
        """consultant will have view permission for assessment"""
        consultant = create_consultant()
        user = create_user()
        assessment_1 = create_assessment(user=user)
        assessment_2 = create_assessment(user=user)
        consultant.assessment_set.add(assessment_1, assessment_2)
        consultant.save()

        self.assertTrue(consultant.has_perm('view_assessment', obj=assessment_1))
        self.assertTrue(consultant.has_perm('view_assessment', obj=assessment_2))

    def test_assessment_removed_from_consultant_s_assessment_set(self):
        """consultant will lose view permission for assessment"""
        consultant = create_consultant()
        user = create_user()
        assessment_1 = create_assessment(user=user)
        assessment_2 = create_assessment(user=user)
        consultant.assessment_set.add(assessment_1, assessment_2)
        consultant.save()
        assert consultant.has_perm('view_assessment', obj=assessment_1)  # sanity check
        assert consultant.has_perm('view_assessment', obj=assessment_2)  # sanity check
        consultant.assessment_set.remove(assessment_1)

        self.assertFalse(consultant.has_perm('view_assessment', obj=assessment_1))  # lost permission
        self.assertTrue(consultant.has_perm('view_assessment', obj=assessment_2))  # still has permission

    def test_consultant_s_assessment_set_is_cleared(self):
        """consultant will lose view permission for all assessment is assessment_set"""
        consultant = create_consultant()
        user = create_user()
        assessments = []

        for i in range(5):
            assessment = create_assessment(user=user)
            assessments.append(assessment)
            consultant.assessment_set.add(assessment)
            consultant.save()

        for assessment in consultant.assessment_set.all():
            assert consultant.has_perm('view_assessment', obj=assessment)  # sanity check

        consultant.assessment_set.clear()

        for assessment in assessments:
            self.assertFalse(consultant.has_perm('view_assessment', obj=assessment))  # lost permission

    def test_consultant_removed_from_assessment_s_consultants(self):
        """consultants will lose view permission for assessment"""
        user = create_user()
        assessment = create_assessment(user)
        consultant_dict = CONSULTANT_DICT.copy()
        consultant_dict.update(dict(username='c1', email='c1@email.com'))
        consultant_1 = create_consultant(consultant_dict)
        consultant_dict.update(dict(username='c2', email='c2@email.com'))
        consultant_2 = create_consultant(consultant_dict)
        assessment.consultants.add(consultant_1, consultant_2)
        assessment.save()
        assert consultant_1.has_perm('view_assessment', obj=assessment)  # sanity check
        assert consultant_2.has_perm('view_assessment', obj=assessment)  # sanity check
        assessment.consultants.remove(consultant_1)

        self.assertFalse(consultant_1.has_perm('view_assessment', obj=assessment))  # lost permission
        self.assertTrue(consultant_2.has_perm('view_assessment', obj=assessment))  # still has permission

    def test_assessment_s_consultants_are_cleared(self):
        """all consultants in assessment.consultants will lose view permission for assessment"""
        user = create_user()
        assessment = create_assessment(user)
        consultants = []
        consultant_dict = CONSULTANT_DICT.copy()

        for i in range(5):
            consultant_dict.update(dict(username='c%d' % i, email='c%d@email.com' % i))
            consultant = create_consultant(consultant_dict)
            assessment.consultants.add(consultant)
            assessment.save()
            consultants.append(consultant)

        for consultant in assessment.consultants.all():
            assert consultant.has_perm('view_assessment', obj=assessment)  # sanity check

        assessment.consultants.clear()

        for consultant in consultants:
            self.assertFalse(consultant.has_perm('view_assessment', obj=assessment))  # lost permission
