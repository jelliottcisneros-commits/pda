from django.contrib.messages import ERROR, DEFAULT_TAGS
from django.contrib.messages.storage.base import Message
from django.test import TestCase, modify_settings
from django.urls import reverse

from core.constants import ACCESS_TYPE_PAID, ACCESS_TYPE_FREE, MISSING_PERMISSION_ERROR_MESSAGE, \
    QUESTIONS_MISSING_FROM_DB_ERROR_MESSAGE
from core.tests.utils import *


@modify_settings(MIDDLEWARE={
    'prepend': 'core.middleware.RequiredDataMiddleware',
})
class RequiredDataMiddlewareTest(TestCase):
    def test_no_questions_in_db_for_core_url(self):
        """ Throw AssertionError of Questions not loaded """
        self.assertEqual(Question.objects.count(), 0)
        with self.assertRaisesMessage(AssertionError, QUESTIONS_MISSING_FROM_DB_ERROR_MESSAGE):
            response = self.client.get(reverse('core:index'))

    def test_no_questions_in_db_for_non_core_url(self):
        """ Successfully access the page """
        self.assertEqual(Question.objects.count(), 0)
        response = self.client.get(reverse('admin:login'))
        self.assertEqual(response.status_code, 200)

    def test_question_in_db_for_core_url(self):
        """ Successfully access the page """
        create_question()
        self.assertGreater(Question.objects.count(), 0)
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)




class PermissionMiddlewareTest(TestCase):

    def setUp(self):
        self.client = Client()

    def test_user_is_not_registered_public_page(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_user_is_not_registered_private_page(self):
        """Redirect to register"""
        path = reverse('core:choose_access_type', kwargs=dict(user_id=0))
        self.assertRedirects(self.client.get(path, follow=False), reverse('core:register'))

    def test_user_is_registered_private_page(self):
        """Access page successfully"""
        user = create_user()
        session = self.client.session
        session['user_id'] = user.pk
        session.save()
        path = reverse('core:choose_access_type', kwargs=dict(user_id=user.pk))
        self.assertEqual(self.client.get(path, follow=False).status_code, 200)

    def test_wrong_user(self):
        """Redirect to continue with error message"""
        user = create_user()
        session = self.client.session
        session['user_id'] = user.pk
        session.save()
        kwargs = dict(user_id=user.pk + 1)  # here using a different user_id
        response = self.client.get(reverse('core:choose_access_type', kwargs=kwargs), follow=True)
        self.assertGreater(len(response.redirect_chain), 0)
        expected_url = reverse('core:continue')
        self.assertEqual(response.redirect_chain[0], (expected_url, 302))  # check if redirects to continue first,
        # more explanation in docs: https://docs.djangoproject.com/en/2.2/topics/testing/tools/#django.test.Client.get
        messages = list(response.context.get('messages'))
        expected_message = Message(level=ERROR, message=MISSING_PERMISSION_ERROR_MESSAGE)
        self.assertIn(expected_message, messages)

    def test_user_without_access_type_accessing_assessment_urls(self):
        """Redirect to choose_access_type"""
        user = create_user()
        session = self.client.session
        session['user_id'] = user.pk
        session.save()
        path = reverse('core:demographics', kwargs=dict(user_id=user.pk, assessment_id=0))
        response = self.client.get(path, follow=False)
        self.assertRedirects(response, reverse('core:choose_access_type', kwargs={'user_id': user.pk}))

    def test_user_without_assessment_id_accessing_assessment_urls(self):
        """Redirect to create_assessment"""
        user = create_user()
        session = self.client.session
        session['user_id'] = user.pk
        session['access_type'] = ACCESS_TYPE_FREE
        session.save()
        path = reverse('core:demographics', kwargs=dict(user_id=user.pk, assessment_id=0))
        response = self.client.get(path, follow=False)
        self.assertRedirects(response, reverse('core:create_assessment', kwargs={'user_id': user.pk}),
                             target_status_code=302)

    def test_user_with_assessment_id_accessing_assessment_urls(self):
        """Redirect to create_assessment"""
        user = create_user()
        assessment = create_assessment(user)
        session = self.client.session
        session['user_id'] = user.pk
        session['access_type'] = ACCESS_TYPE_FREE
        session['assessment_id'] = assessment.pk
        session.save()
        path = reverse('core:demographics', kwargs=dict(user_id=user.pk, assessment_id=assessment.pk))
        self.assertEqual(self.client.get(path, follow=False).status_code, 200)

    def test_user_with_assessment_id_accessing_assessment_urls_with_different_assessment_id(self):
        """Redirect to continue with error message"""
        user = create_user()
        assessment = create_assessment(user)
        session = self.client.session
        session['user_id'] = user.pk
        session['access_type'] = ACCESS_TYPE_FREE
        session['assessment_id'] = assessment.pk
        session.save()
        kwargs = dict(user_id=user.pk, assessment_id=assessment.pk + 1)  # here setting different assessment_id
        response = self.client.get(reverse('core:demographics', kwargs=kwargs), follow=True)
        self.assertGreater(len(response.redirect_chain), 0)
        expected_url = reverse('core:continue')
        self.assertEqual(response.redirect_chain[0], (expected_url, 302))  # check if redirects to continue first,
        # more explanation in docs: https://docs.djangoproject.com/en/2.2/topics/testing/tools/#django.test.Client.get
        messages = list(response.context.get('messages'))
        expected_message = Message(level=ERROR, message=MISSING_PERMISSION_ERROR_MESSAGE)
        self.assertIn(expected_message, messages)


class SessionExpirationMiddlewareTests(TestCase):
    # proceed when we have enough time
    def test_next_with_variables(self):
        self.client = Client()
        session = self.client.session
        session['year'] = 4000
        session['month'] = 12
        session['day'] = 2
        session['hour'] = 6
        session['minute'] = 7
        session['second'] = 8
        session.save()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "In the reported results you will encounter information")

    # expire when it has been too long
    def test_expiration(self):
        self.client = Client()
        session = self.client.session
        session['year'] = 2000
        session['month'] = 12
        session['day'] = 2
        session['hour'] = 6
        session['minute'] = 7
        session['second'] = 8
        session.save()
        response = self.client.get('/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "expired")

    # no time? like hitting the landing page or refreshing on 10 to 8, allow it to go through
    def test_next_no_variables(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "In the reported results you will encounter information")

    # test for timer session variable deletion (it should happen here)
    def test_timer_deletion(self):
        self.client = Client()
        session = self.client.session
        session['year'] = 2000
        session['month'] = 12
        session['day'] = 2
        session['hour'] = 6
        session['minute'] = 7
        session['second'] = 8
        user = create_user()
        assessment = create_assessment(user)
        session['user_id'] = user.pk
        session['assessment_id'] = assessment.pk
        session['last_question'] = len(Question.objects.all())
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()
        self.client.get(reverse('core:score', kwargs=dict(user_id=user.pk, assessment_id=assessment.pk)))
        session = self.client.session
        self.assertTrue('year' not in session)

    def test_timer_set(self):
        self.client = Client()
        self.user = create_user()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['access_type'] = ACCESS_TYPE_FREE
        session.save()
        self.client.post(reverse('core:create_assessment', kwargs=dict(user_id=self.user.pk)))
        session = self.client.session
        self.assertTrue('year' in session)