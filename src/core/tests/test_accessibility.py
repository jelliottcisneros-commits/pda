from django.test import TestCase
from django.urls import reverse

from core.constants import ACCESS_TYPE_FREE
from core.tests.utils import *


class AccessibilityTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['access_type'] = ACCESS_TYPE_FREE
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = 0
        session['access_type'] = ACCESS_TYPE_FREE
        session.save()
        create_question()

    def test_landing_page_logo_has_alt(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get('/')
        self.assertContains(response, 'alt="PDA logo"')

    def test_landing_page_has_role(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get('/')
        self.assertContains(response, 'role="main"')

    def test_registration_has_role(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get('/register')
        self.assertContains(response, 'role="main"')

    def test_choose_access_type_has_role(self):
        delete_session_key_for_client(self.client, 'access_type')
        response = self.client.get(reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))
        self.assertContains(response, 'role="main"')

    def test_demographics_has_role(self):
        delete_session_key_for_client(self.client, 'last_question')
        response = self.client.get(
            reverse('core:demographics', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertContains(response, 'role="form"')

    def test_instructions_has_role(self):
        response = self.client.get(
            reverse('core:instructions', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertContains(response, 'role="heading"')

    def test_finished_has_role(self):
        response = self.client.get(
            reverse('core:finished', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertContains(response, 'role="main"')

    def test_email_has_placeholder(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:register'), follow=True)
        self.assertContains(response, 'placeholder="ex. john.doe@example.com"')

    def test_firstname_has_placeholder(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:register'), follow=True)
        self.assertContains(response, 'placeholder="ex. John"')

    def test_lastname_has_placeholder(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:register'), follow=True)
        self.assertContains(response, 'placeholder="ex. Doe"')

    def test_phone_has_placeholder(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:register'), follow=True)
        self.assertContains(response, 'placeholder="ex. 123-456-7890"')

    def test_email_has_autofocus(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:register'), follow=True)
        self.assertContains(response, 'autofocus="true"')

    def test_question_has_autofocus(self):
        response = self.client.get(
            reverse('core:question',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 100}),
            follow=True)
        self.assertContains(response, 'autofocus="true"')

    def test_retake_has_placeholder(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:register'), follow=True)
        self.assertContains(response, 'placeholder="ex. john.doe@example.com"')

    def test_landing_page_has_title(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get('/')
        self.assertContains(response, 'Power of Difference Assessment - Home')

    def test_registration_has_title(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get('/register')
        self.assertContains(response, 'Power of Difference Assessment - Registration')

    def test_choose_access_type_has_title(self):
        delete_session_key_for_client(self.client, 'access_type')
        response = self.client.get(reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))
        self.assertContains(response, 'Power of Difference Assessment - Choose Access Type')

    def test_demographics_has_title(self):
        delete_session_key_for_client(self.client, 'last_question')
        response = self.client.get(
            reverse('core:demographics', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertContains(response, '<title>Power of Difference Assessment -')

    def test_instructions_has_title(self):
        response = self.client.get(
            reverse('core:instructions', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertContains(response, 'Power of Difference Assessment - Instructions')

    def test_finished_has_title(self):
        response = self.client.get(
            reverse('core:finished', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertContains(response, '<title>Power of Difference Assessment -')

    def test_reverification_has_title(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:retake'))
        self.assertContains(response, 'Power of Difference Assessment - Reverification')

    def test_expired_has_title(self):
        response = self.client.get(reverse('core:expired'))
        self.assertContains(response, 'Power of Difference Assessment - Expired')

    def test_landing_page_has_darkmode(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:index'))
        self.assertContains(response, 'Dark Mode')

    def test_registration_has_darkmode(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:register'))
        self.assertContains(response, 'Dark Mode')

    def test_choose_access_type_has_darkmode(self):
        delete_session_key_for_client(self.client, 'access_type')
        response = self.client.get(reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))
        self.assertContains(response, 'Dark Mode')

    def test_demographics_has_darkmode(self):
        delete_session_key_for_client(self.client, 'assessment_id')
        response = self.client.get(
            reverse('core:demographics', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertContains(response, 'Dark Mode')

    def test_instructions_has_darkmode(self):
        response = self.client.get(
            reverse('core:instructions', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertContains(response, 'Dark Mode')

    def test_finished_has_darkmode(self):
        response = self.client.get(
            reverse('core:finished', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertContains(response, 'Dark Mode')

    def test_reverification_has_darkmode(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get(reverse('core:retake'))
        self.assertContains(response, 'Dark Mode')

    def test_expired_has_darkmode(self):
        response = self.client.get(reverse('core:expired'))
        self.assertContains(response, 'Dark Mode')

    def test_footer_logo_has_alt(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get('/register')
        self.assertContains(response, 'id="footer-img" alt="PDA logo')

    def test_footer_logo_has_role(self):
        delete_session_key_for_client(self.client, 'user_id')
        response = self.client.get('/register')
        self.assertContains(response, 'role="img" id="footer-img"')
