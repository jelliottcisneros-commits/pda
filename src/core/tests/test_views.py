import random
import re
from datetime import datetime
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.messages import ERROR, DEFAULT_TAGS
from django.contrib.messages.storage.base import Message
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse, get_resolver
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from paypal.standard.pdt.models import PayPalPDT
from paypal.standard.pdt.tests.test_pdt import DummyPayPalPDT

from TheSum.settings import PAYPAL_RECIEVER_EMAIL
from core.constants import *
from core.forms import DemographicForm, ResponseForm, UnverifiedUserForm
from core.models import Race_Score, Score, AccessCode, Disability_Score, Sexual_Orientation_Score, \
    Class_Score, Gender_Score, Religion_Score, Culture_Score, CoreGroupuser
from core.tests.utils import *
from core.tokens import token_generator_for_abstract_user
from core.views import custom_server_error, CompleteConsultantRegistrationView, CompleteViewOnlyAdminRegistrationView, \
    AssessmentDetailedView


# from paypal.standard.pdt.tests import tempates


class ContinueViewTests(TestCase):
    def test_user_id_is_none(self):
        """Redirect to register"""
        response = self.client.get(reverse('core:continue'))
        expected_url = reverse('core:index')
        self.assertRedirects(response=response, expected_url=expected_url)

    def test_access_type_is_none(self):
        """Redirect to choose_access_type"""
        user = create_user()
        session = self.client.session
        session['user_id'] = user.pk
        session.save()
        response = self.client.get(reverse('core:continue'))
        expected_url = reverse('core:choose_access_type', kwargs=dict(user_id=user.pk))
        self.assertRedirects(response=response, expected_url=expected_url)

    def test_assessment_id_is_none(self):
        """Redirect to create_assessment"""
        user = create_user()
        session = self.client.session
        session['user_id'] = user.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()
        response = self.client.get(reverse('core:continue'), follow=False)
        expected_url = reverse('core:create_assessment', kwargs=dict(user_id=user.pk))
        self.assertRedirects(response=response, expected_url=expected_url, target_status_code=302)

    def test_last_question_is_none(self):
        """Redirect to demographic"""
        user = create_user()
        assessment = create_assessment(user)
        session = self.client.session
        session['user_id'] = user.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['assessment_id'] = assessment.pk
        session.save()
        response = self.client.get(reverse('core:continue'))
        expected_url = reverse('core:demographics', kwargs=dict(user_id=user.pk, assessment_id=assessment.pk))
        self.assertRedirects(response=response, expected_url=expected_url)

    def test_last_question_is_not_none(self):
        "Redirect to question with number=last_question+1"
        user = create_user()
        assessment = create_assessment(user)
        create_question()
        last_question = 0
        session = self.client.session
        session['user_id'] = user.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['assessment_id'] = assessment.pk
        session['last_question'] = last_question
        session.save()
        response = self.client.get(reverse('core:continue'))
        expected_url = reverse('core:question',
                               kwargs=dict(user_id=user.pk, assessment_id=assessment.pk, number=last_question + 1))
        self.assertRedirects(response=response, expected_url=expected_url)


class IndexViewTests(TestCase):
    def test_go_to_home(self):
        """Returns the index template"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "In the reported results you will encounter information")

    def test_home_has_PDA_purpose(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "disability, culture, religion, gender, and class. This information")


@override_settings(SEND_PDF_EMAIL='ON')
class PDFEmailTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        # commented out as these actually prevent score from running
        # self.score = Score()
        # self.score.assessment = self.assessment
        # self.score.save()
        # Religion_Score.objects.create(score = self.score)
        # Gender_Score.objects.create(score = self.score)
        # Race_Score.objects.create(score = self.score)
        # Sexual_Orientation_Score.objects.create(score = self.score)
        # Disability_Score.objects.create(score = self.score)
        # Culture_Score.objects.create(score = self.score)
        # Class_Score.objects.create(score = self.score)
        # self.assessment.refresh_from_db()
        create_question()

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_email_sends_to_user(self, mock_save):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()
        response = self.client.get(
            reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
            follow=True)
        email = mail.outbox[0]
        self.assertEqual(email.to[0], self.user.email)
        mock_save.assert_called_once()  # No file saved!

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_single_email(self, mock_save):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()
        response = self.client.get(
            reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
            follow=True)
        self.assertEqual(len(mail.outbox), 1)
        mock_save.assert_called_once()  # No file saved!

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_email_pdf_attachment(self, mock_save):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()
        response = self.client.get(
            reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
            follow=True)
        email = mail.outbox[0]
        self.assertEqual(len(email.attachments), 2)
        self.assertEqual(
            email.attachments[0][0],
            'PDM_Summary.pdf'
        )
        self.assertEqual(
            email.attachments[1][0],
            f'test@email.com_{self.assessment.pk}_results.pdf'
        )
        mock_save.assert_called_once()  # No file saved!

    @patch('core.views.group_result')
    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_group_participant_does_not_receive_individual_results_email(
        self,
        mock_save,
        mock_group_result,
    ):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming

        access_code = AccessCode.objects.create(
            name="Group Email Test",
            code="!GROUPMAIL",
            uses_left=1,
        )
        CoreGroupuser.objects.create(
            user=self.user,
            accesscode=access_code,
            assessment=self.assessment,
        )

        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_INST
        session['last_question'] = len(Question.objects.all())
        session.save()

        self.client.get(
            reverse(
                'core:score',
                kwargs=dict(
                    user_id=self.user.pk,
                    assessment_id=self.assessment.pk,
                ),
            ),
            follow=True,
        )

        mock_group_result.assert_called_once_with(self.assessment.pk)
        self.assertEqual(len(mail.outbox), 0)
        mock_save.assert_called_once()

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_email_sends_bcc_admin(self, mock_save):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()
        response = self.client.get(
            reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
            follow=True)
        email = mail.outbox[0]
        self.assertEqual(email.bcc[0], settings.BCC_EMAIL)
        mock_save.assert_called_once()  # No file saved!

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_email_correct_subject(self, mock_save):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()
        response = self.client.get(
            reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
            follow=True)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "PDA Results")
        mock_save.assert_called_once()  # No file saved!

    @patch('django.core.files.storage.FileSystemStorage.save')
    def test_email_correct_message(self, mock_save):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()
        response = self.client.get(
            reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
            follow=True)
        email = mail.outbox[0]
        self.assertIn("A PDF containing", email.body)
        mock_save.assert_called_once()  # No file saved!


class RegistrationViewTests(TestCase):
    def test_invalid_form(self):
        form = UnverifiedUserForm(
            data={'email': "ss3fg@virginia.edu", 'first_name': "Sam", 'last_name': 'S', 'is_email_verified': False,
                  'phone': 'bad'})
        self.assertFalse(form.is_valid())

    def test_email_already_exists(self):
        """A new unverified user is not created and error gets thrown"""
        user = create_user()
        self.assertEqual(len(UnverifiedUser.objects.filter(email=user.email)), 0)
        post_body = dict(user.__dict__)
        response = self.client.post(reverse('core:register'), post_body, follow=True)
        self.assertRedirects(response, reverse('core:register'))
        self.assertEqual(len(UnverifiedUser.objects.filter(email=user.email)), 0)
        messages = list(response.context.get('messages'))
        self.assertEqual(len(messages), 1)
        message = messages[0]
        self.assertEqual(message.tags, DEFAULT_TAGS.get(ERROR))
        self.assertEqual(message.message, USER_ALREADY_EXISTS_MESSAGE)

    def test_valid_form(self):
        """Create unverified user, send email with correct token, and show verification instruction"""
        user_dict = USER_DICT
        self.assertEqual(len(UnverifiedUser.objects.filter(email=user_dict['email'])), 0)

        response = self.client.post(reverse('core:register'), user_dict, follow=True)
        self.assertRedirects(response, reverse('core:verify_email_instructions'))
        # check if email is sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, VERIFICATION_EMAIL_SUBJECT)
        # check if email contains correct verification link
        self.assertEqual(len(UnverifiedUser.objects.filter(email=user_dict['email'])), 1)
        unverified_user = UnverifiedUser.objects.get(email=user_dict['email'])
        uidb64 = urlsafe_base64_encode(force_bytes(unverified_user.pk))
        domain = self.client._base_environ()['SERVER_NAME']
        url_prefix = 'http://%s/verify_email/%s/' % (domain, uidb64)
        verification_url = next(
            line for line in email.body.splitlines()
            if line.startswith(url_prefix)
        )
        token = verification_url[len(url_prefix):].rstrip('/')
        self.assertTrue(
            token_generator_for_abstract_user.check_token(
                unverified_user,
                token,
            )
        )


class RetakeViewTests(TestCase):
    def test_user_with_email_does_not_exist(self):
        """Redirects to register page with error message"""
        response = self.client.post(reverse('core:retake'), data=dict(email=USER_DICT['email']), follow=True)
        self.assertRedirects(response, reverse('core:register'))
        messages = list(response.context.get('messages'))
        expected_message = Message(level=ERROR, message=USER_WITH_EMAIL_DOES_NOT_EXIST)
        self.assertIn(expected_message, messages)

    def test_user_who_cannot_retake(self):
        """Redirect to retake with error message"""
        user_dict = USER_DICT.copy()
        user_dict['can_retake'] = False
        user = create_user(user_dict)
        response = self.client.post(reverse('core:retake'), data=dict(email=user.email), follow=True)

        self.assertRedirects(response, reverse('core:retake'))
        messages = list(response.context.get('messages'))
        expected_message = Message(level=ERROR, message=USER_CANNOT_RETAKE_MESSAGE)
        self.assertIn(expected_message, messages)

    def test_success(self):
        user_dict = USER_DICT.copy()
        user_dict['can_retake'] = True
        user = create_user(user_dict)
        response = self.client.post(reverse('core:retake'), data=dict(email=user.email), follow=True)
        self.assertRedirects(response, reverse('core:verify_email_instructions'))
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, RE_VERIFICATION_EMAIL_SUBJECT)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        domain = self.client._base_environ()['SERVER_NAME']
        url_prefix = 'http://%s/re_verify_email/%s/' % (domain, uidb64)
        verification_url = next(
            line for line in email.body.splitlines()
            if line.startswith(url_prefix)
        )
        token = verification_url[len(url_prefix):].rstrip('/')
        self.assertTrue(
            token_generator_for_abstract_user.check_token(
                user,
                token,
            )
        )


class EmailVerificationViewTests(TestCase):

    def test_invalid_link_if_url_incorrect(self):
        """Show invalid link message"""
        unverified_user = create_unverified_user()
        token = token_generator_for_abstract_user.make_token(unverified_user)
        uidb64 = urlsafe_base64_encode(force_bytes(unverified_user.pk + 2))  # making the link invalid
        response = self.client.get(reverse('core:verify_email', kwargs=dict(uidb64=uidb64, token=token)), follow=True)
        self.assertContains(response, INVALID_LINK_MESSAGE)

    def test_invalid_link_if_unverified_user_deleted(self):
        """Show invalid link message"""
        unverified_user = create_unverified_user()
        token = token_generator_for_abstract_user.make_token(unverified_user)
        uidb64 = urlsafe_base64_encode(force_bytes(unverified_user.pk))
        unverified_user.delete()
        response = self.client.get(reverse('core:verify_email', kwargs=dict(uidb64=uidb64, token=token)), follow=True)
        self.assertContains(response, INVALID_LINK_MESSAGE)

    def test_email_already_exists(self):
        """Redirect to register with error message"""
        user_dict = USER_DICT
        unverified_user = create_unverified_user(user_dict)
        token = token_generator_for_abstract_user.make_token(unverified_user)
        uidb64 = urlsafe_base64_encode(force_bytes(unverified_user.pk))
        user = create_user(user_dict)  # using same email as unverified_user
        self.assertEqual(len(UnverifiedUser.objects.filter(email=user.email)),
                          1)
        response = self.client.get(reverse('core:verify_email', kwargs=dict(uidb64=uidb64, token=token)), follow=True)
        self.assertRedirects(response, reverse('core:register'))
        self.assertEqual(len(UnverifiedUser.objects.filter(email=user.email)),
                          0)  # checking if all the unverified_user s get deleted
        messages = list(response.context.get('messages'))
        expected_message = Message(level=ERROR, message=USER_ALREADY_EXISTS_MESSAGE)
        self.assertIn(expected_message, messages)

    def test_valid_link(self):
        """Redirect to choose_access_type, and delete all unverified user with same email"""
        unverified_user = create_unverified_user()
        create_unverified_user()  # second unverified user with same email
        self.assertEqual(len(UnverifiedUser.objects.filter(email=unverified_user.email)), 2)
        token = token_generator_for_abstract_user.make_token(unverified_user)
        uidb64 = urlsafe_base64_encode(force_bytes(unverified_user.pk))
        response = self.client.get(reverse('core:verify_email', kwargs=dict(uidb64=uidb64, token=token)), follow=True)
        user_id = self.client.session.get('user_id')
        self.assertIsNotNone(user_id)
        self.assertRedirects(response,
                             reverse('core:choose_access_type', kwargs=dict(user_id=user_id)))
        self.assertEqual(len(UnverifiedUser.objects.filter(email=unverified_user.email)),
                          0)  # checking all other users are deleted


class EmailReVerificationViewTests(TestCase):
    def test_user_who_can_no_longer_retake(self):
        """Show  invalid link message"""
        user_dict = USER_DICT.copy()
        user_dict['can_retake'] = True
        user = create_user(user_dict)
        token = token_generator_for_abstract_user.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        user.can_retake = False
        user.save()
        response = self.client.get(reverse('core:re_verify_email', kwargs=dict(uidb64=uidb64, token=token)),
                                   follow=True)
        self.assertContains(response, INVALID_LINK_MESSAGE)

    def test_valid_link(self):
        """Set user_id session key, set can_retake to false, and redirect to choose_access_type"""
        user_dict = USER_DICT.copy()
        user_dict['can_retake'] = True
        user = create_user(user_dict)
        token = token_generator_for_abstract_user.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        response = self.client.get(reverse('core:re_verify_email', kwargs=dict(uidb64=uidb64, token=token)),
                                   follow=True)
        user_id = self.client.session.get('user_id')
        self.assertIsNotNone(user_id)
        user = User.objects.get(pk=user_id)
        self.assertFalse(user.can_retake)
        self.assertRedirects(response,
                             reverse('core:choose_access_type', kwargs=dict(user_id=user_id)))


class ChooseAccessTypeTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session.save()

    def test_success_response(self):
        """
        Test whether page returns 200
        """
        response = self.client.get(reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose an access type')

    def test_corrected_paid_text(self):
        """
        Test whether page returns 200
        """
        response = self.client.get(reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'If you want to take the PDA and receive an hour-long results consultation')

    # def test_corrected_free_text(self):
    #     """
    #     Test whether page returns 200
    #     """
    #     response = self.client.get(reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, 'By choosing this free option, you can receive results and schedule a 10 ')


class VerifyAccessTokenTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.code = 'test'
        self.uses_left = 1
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session.save()
        access_code = AccessCode(code=self.code, uses_left=self.uses_left)
        access_code.save()

    def test_request_missing_access_code(self):
        """Redirect to choose_access_type"""
        response = self.client.post(reverse('core:verify_access_code', kwargs=dict(user_id=self.user.pk)),
                                    {}, follow=False)
        expected_url = reverse('core:choose_access_type', kwargs=(dict(user_id=self.user.pk)))
        self.assertRedirects(response, expected_url)

    def test_valid_access_code(self):
        """Decreases uses_left, set session key access_type to INST, redirect to creat_assessment"""
        self.assertFalse('access_type' in self.client.session)
        response = self.client.post(reverse('core:verify_access_code', kwargs=dict(user_id=self.user.pk)),
                                    {'access_code': self.code}, follow=False)
        access_code = AccessCode.objects.get(code=self.code)
        self.assertEqual(access_code.uses_left, self.uses_left - 1)
        access_type = self.client.session.get('access_type')
        self.assertIsNotNone(access_type)
        self.assertEqual(access_type, ACCESS_TYPE_INST)
        expected_url = reverse('core:create_assessment', kwargs=dict(user_id=self.user.pk))
        self.assertRedirects(response, expected_url, target_status_code=302)

    def test_group_access_code_creates_group_user_and_session_key(self):
        access_code = AccessCode.objects.get(code=self.code)
        access_code.code = '!GROUPTEST'
        access_code.save()

        response = self.client.post(
            reverse('core:verify_access_code', kwargs=dict(user_id=self.user.pk)),
            {'access_code': '!GROUPTEST'},
            follow=False
        )

        group_user = CoreGroupuser.objects.get(user=self.user)
        self.assertEqual(group_user.accesscode, access_code)
        self.assertEqual(self.client.session['accesscode_id'], access_code.pk)
        self.assertEqual(self.client.session['access_type'], ACCESS_TYPE_INST)

        expected_url = reverse('core:create_assessment', kwargs=dict(user_id=self.user.pk))
        self.assertRedirects(response, expected_url, target_status_code=302)

    def test_group_access_code_links_created_assessment_to_group_user(self):
        access_code = AccessCode.objects.get(code=self.code)
        access_code.code = '!GROUPTEST'
        access_code.save()

        self.client.post(
            reverse('core:verify_access_code', kwargs=dict(user_id=self.user.pk)),
            {'access_code': '!GROUPTEST'},
            follow=False
        )

        response = self.client.get(
            reverse('core:create_assessment', kwargs=dict(user_id=self.user.pk)),
            follow=False
        )

        group_user = CoreGroupuser.objects.get(user=self.user, accesscode=access_code)
        self.assertIsNotNone(group_user.assessment)
        self.assertEqual(group_user.assessment.pk, self.client.session['assessment_id'])

        expected_url = reverse(
            'core:demographics',
            kwargs=dict(user_id=self.user.pk, assessment_id=group_user.assessment.pk)
        )
        self.assertRedirects(response, expected_url)

    def test_invalid_access_code(self):
        """redirect to choose_access_type, while not decreasing uses_left, and not setting session_key"""
        response = self.client.post(reverse('core:verify_access_code', kwargs=dict(user_id=self.user.pk)),
                                    {'access_code': 'invalid'})
        self.assertRedirects(response, reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))
        self.assertFalse('access_type' in self.client.session)
        access_code = AccessCode.objects.get(code=self.code)
        self.assertEqual(access_code.uses_left, self.uses_left)

    def test_no_uses_left(self):
        """Redirect to choose_access_type without setting session key"""
        self.assertFalse('access_type' in self.client.session)
        access_code = AccessCode.objects.get(code=self.code)
        access_code.uses_left = 0
        access_code.save()
        response = self.client.post(reverse('core:verify_access_code', kwargs=dict(user_id=self.user.pk)),
                                    {'access_code': self.code}, follow=False)
        self.assertRedirects(response, reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))
        self.assertFalse('access_type' in self.client.session)

    def test_unlimited_use_access_code(self):
        """Redirect to create_assessment, leave uses_left stays as -1"""
        self.assertFalse('access_type' in self.client.session)
        access_code = AccessCode.objects.get(code=self.code)
        access_code.uses_left = -1
        access_code.save()
        response = self.client.post(reverse('core:verify_access_code', kwargs=dict(user_id=self.user.pk)),
                                    {'access_code': self.code})
        self.assertTrue('access_type' in self.client.session)
        expected_url = reverse('core:create_assessment'
                               , kwargs=dict(user_id=self.user.pk))
        self.assertRedirects(response, expected_url, target_status_code=302)
        access_code = AccessCode.objects.get(code=self.code)
        self.assertEqual(access_code.uses_left, -1)
        self.assertEqual(self.client.session['access_type'], ACCESS_TYPE_INST)


# PayPal payment tests
class PayTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session.save()

    # PayPal button shows up
    def test_BuyNow_button(self):
        response = self.client.get(reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'input type="hidden" name="cmd"')

    # CANCELLATION TESTS
    # cancellation of payment will redirect
    def test_cancel_redirect(self):
        response = self.client.post(reverse('core:payment_cancelled', kwargs=dict(user_id=self.user.pk)))
        self.assertEqual(response.status_code, 302)

    # cancellation of payment redirects to choose_access_type
    def test_cancel_redirect2(self):
        expected_url = reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk))
        response = self.client.post(reverse('core:payment_cancelled', kwargs=dict(user_id=self.user.pk)))
        self.assertRedirects(response, expected_url, target_status_code=200)

    # cancellation of payment displays correct error message
    def test_cancel_message(self):
        response = self.client.get(reverse('core:payment_cancelled', kwargs=dict(user_id=self.user.pk)), follow=True)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), CANCELLED_PAYMENT_MESSAGE)


class DummyPaymentTestValid(TestCase):
    def setUp(self):
        # set up some dummy PDT get parameters
        self.get_params = {"tx": "4WJ86550014687441", "st": "Completed", "amt": PDA_PRICE, "cc": "EUR",
                           "cm": "a3e192b8-8fea-4a86-b2e8-d5bf502e36be", "item_number": "",
                           "sig": "blahblahblah"}

        # monkey patch the PayPalPDT._postback function
        self.dpppdt = DummyPayPalPDT(update_context_dict={'business': PAYPAL_RECIEVER_EMAIL, 'mc_gross': PDA_PRICE})
        self.dpppdt.update_with_get_params(self.get_params)
        PayPalPDT._postback = self.dpppdt._postback
        self.user = create_user()
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session.save()

    # returning after valid payment will redirect
    def test_return_payment(self):
        kwargs = dict(user_id=self.user.pk)
        response = self.client.get(f'/users/{self.user.pk}/payment?tx=4WJ86550014687441')
        self.assertEqual(response.status_code, 302)

    # returning after valid payment will redirect to create_assessment
    def test_valid_payment_redirect(self):
        expected_url = reverse('core:create_assessment', kwargs=dict(user_id=self.user.pk))
        kwargs = dict(user_id=self.user.pk)
        response = self.client.get(f'/users/{self.user.pk}/payment?tx=7H969661S6756943M')
        self.assertRedirects(response, expected_url, target_status_code=302)

    # returning after valid payment will display "Payment Recieved" 
    def test_valid_message(self):
        response = self.client.get(f'/users/{self.user.pk}/payment?tx=4WJ86550014687441', follow=True)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Payment Received")


class DummyPaymentTestInvalidBusiness(TestCase):
    def setUp(self):
        # set up some dummy PDT get parameters
        self.get_params = {"tx": "4WJ86550014687441", "st": "Completed", "amt": PDA_PRICE, "cc": "EUR",
                           "cm": "a3e192b8-8fea-4a86-b2e8-d5bf502e36be", "item_number": "",
                           "sig": "blahblahblah"}

        # monkey patch the PayPalPDT._postback function
        self.dpppdt = DummyPayPalPDT(update_context_dict={'business': "email@test.com", 'mc_gross': PDA_PRICE})
        self.dpppdt.update_with_get_params(self.get_params)
        PayPalPDT._postback = self.dpppdt._postback
        self.user = create_user()
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session.save()

    # returning after payment with invalid business will redirect 
    def test_return_payment_invalid_business(self):
        kwargs = dict(user_id=self.user.pk)
        response = self.client.get(f'/users/{self.user.pk}/payment?tx=2')
        self.assertEqual(response.status_code, 302)

    # returning after payment with invalid business will redirect to choose_access_type
    def test_return_payment_invalid_business_redirect(self):
        expected_url = reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk))
        kwargs = dict(user_id=self.user.pk)
        response = self.client.get(f'/users/{self.user.pk}/payment?tx=2')
        self.assertRedirects(response, expected_url, target_status_code=200)

    # returning after payment with invlaid business will display error message
    def test_return_payment_invalid_business_message(self):
        response = self.client.get(f'/users/{self.user.pk}/payment?tx=2', follow=True)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), INVALID_PAYMENT_MESSAGE)


class DummyPaymentTestInvalidAmount(TestCase):
    def setUp(self):
        # set up some dummy PDT get parameters
        self.get_params = {"tx": "4WJ86550014687441", "st": "Completed", "amt": "750.00", "cc": "EUR",
                           "cm": "a3e192b8-8fea-4a86-b2e8-d5bf502e36be", "item_number": "",
                           "sig": "blahblahblah"}

        # monkey patch the PayPalPDT._postback function
        self.dpppdt = DummyPayPalPDT(update_context_dict={'business': PAYPAL_RECIEVER_EMAIL, 'mc_gross': PDA_PRICE})
        self.dpppdt.update_with_get_params(self.get_params)
        PayPalPDT._postback = self.dpppdt._postback
        self.user = create_user()
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session.save()

    # returning after payment with invalid amt will redirect 
    def test_return_payment_invalid_amount(self):
        kwargs = dict(user_id=self.user.pk)
        response = self.client.get(f'/users/{self.user.pk}/payment?tx=3')
        self.assertEqual(response.status_code, 302)

    # returning after payment with invalid amt will redirect to choose_access_type
    def test_return_payment_invalid_amount_redirect(self):
        expected_url = reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk))
        kwargs = dict(user_id=self.user.pk)
        response = self.client.get(f'/users/{self.user.pk}/payment?tx=3')
        self.assertRedirects(response, expected_url, target_status_code=200)

    # returning after payment with invalid amt will display invalid error
    def test_return_payment_invalid_amount_message(self):
        response = self.client.get(f'/users/{self.user.pk}/payment?tx=3', follow=True)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), INVALID_PAYMENT_MESSAGE)


class CreateAssessmentTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.access_type = ACCESS_TYPE_PAID
        self.client = Client()

    def test_access_type_not_set(self):
        """Redirect to choose_access_type"""
        session = self.client.session
        session['user_id'] = self.user.pk
        session.save()
        response = self.client.get(reverse('core:create_assessment', kwargs=dict(user_id=self.user.pk)), follow=False)
        self.assertRedirects(response, reverse('core:choose_access_type', kwargs=dict(user_id=self.user.pk)))

    def test_success_response(self):
        """Redirect to demographics, set assessment_id session key"""
        session = self.client.session
        session['user_id'] = self.user.pk
        session['access_type'] = self.access_type
        session.save()
        response = self.client.get(reverse('core:create_assessment', kwargs=dict(user_id=self.user.pk)), follow=False)
        self.assertTrue('assessment_id' in self.client.session)
        assessment_id = self.client.session['assessment_id']
        kwargs = dict(user_id=self.user.pk, assessment_id=assessment_id)
        self.assertRedirects(response, reverse('core:demographics', kwargs=kwargs))

    def test_session_expiration_set(self):
        session = self.client.session
        session['user_id'] = self.user.pk
        session['access_type'] = self.access_type
        session.save()
        response = self.client.get(reverse('core:create_assessment', kwargs=dict(user_id=self.user.pk)), follow=True)
        session = self.client.session
        self.assertTrue(session.get_expiry_age() <= 86400)
        self.assertTrue(session.get_expiry_age() >= 86200)


class DemographicTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()
        create_question()

    # testing to make sure the page is setup right
    def test_demo_page(self):
        response = self.client.get(
            reverse('core:demographics', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "19 demographics questions")

    def test_demo_page_copyright_not_in_body(self):
        response = self.client.get(
            reverse('core:demographics', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response,
                               "<p>COPYRIGHT 2016 THE SUM—ALL RIGHTS RESERVED: Because of the complexity of the survey structure, results, interpretation,")

    def test_if_demographics_view_redirects_when_assessment_already_has_demographic(self):
        create_demographic(self.assessment)
        session = self.client.session
        session['last_question'] = 0
        session.save()
        self.client.session.save()
        kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk)
        response = self.client.get(reverse('core:demographics', kwargs=kwargs), follow=True)
        kwargs.update({'number': self.client.session['last_question'] + 1})
        expected_url = reverse('core:question', kwargs=kwargs)
        self.assertRedirects(response, expected_url)

    # testing to make sure our demographic object gets added when a form is submitted with good data
    def test_demo_form_good(self):
        dict_data = DEMOGRAPHIC_DICT
        kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk)
        response = self.client.post(
            reverse('core:demographics_submit', kwargs=kwargs),
            dict_data)
        expected_url = reverse('core:instructions', kwargs=kwargs)
        self.assertRedirects(response, expected_url)
        demographic = Assessment.objects.get(pk=self.assessment.pk).demographic
        self.assertIsNotNone(demographic)
        self.assertEqual(demographic.gender, 'Male')

    # making sure a demographic form with bad data would get rejected
    def test_demo_form_bad(self):
        data = {'age': ''}
        form = DemographicForm(data=data)
        self.assertFalse(form.is_valid())
        response = self.client.post(reverse('core:demographics_submit',
                                            kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
                                    data, follow=True)
        self.assertContains(response, "19 demographics questions")
        messages = list(response.context.get('messages'))
        expected_message = Message(level=ERROR, message=DEMOGRAPHICS_FORM_ERROR_MESSAGE)
        self.assertIn(expected_message, messages)


class QuestionDisplayTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = 0
        session.save()

    # make sure the question gets displayed
    def test_displays_question(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        Question.objects.create(number=2, title="question 2", sociocultural_location="test2",
                                primary_power_perspective="test2")
        response = self.client.get(
            reverse('core:question',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "question 1")

    def test_displays_sociocultural_location(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        response = self.client.get(
            reverse('core:question',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test")

    # make sure the next button appears when it should
    # text has changed and this test is no longer valid
    # def test_next_appears(self):
    # Question.objects.create(number=1, title="question 1", type="test", primary_power_perspective = "test")
    # Question.objects.create(number=2, title="question 2", type="test2", primary_power_perspective = "test2")
    # response = self.client.get('/question/1')
    # self.assertEqual(response.status_code, 200)
    # self.assertContains(response, "Next Question")
    # make sure the submit button appears when it should

    def test_submit_appears(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        response = self.client.get(
            reverse('core:question',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Submit")

    # make sure next button appears when not on last question
    def test_next_appears(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        Question.objects.create(number=2, title="question 2", sociocultural_location="test2",
                                primary_power_perspective="test2")
        response = self.client.get(
            reverse('core:question',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Next")

    # Make sure a user cannot access a future question
    def test_access_future_question_redirect(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        Question.objects.create(number=50, title="question 50", sociocultural_location="test2",
                                primary_power_perspective="test2")
        response = self.client.get(
            reverse('core:question',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 50}))
        self.assertEqual(response.status_code, 302)  # Status code 302 is an http redirect

    # Make sure a user cannot access a previous question
    def test_access_previous_question_redirect(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        Question.objects.create(number=0, title="question 0", sociocultural_location="test2",
                                primary_power_perspective="test2")
        response = self.client.get(
            reverse('core:question',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 0}))
        self.assertEqual(response.status_code, 302)

    # makes sure that next/submit button is disabled if no choice selected
    def test_button_disabled(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        response = self.client.get(
            reverse('core:question',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 1}),
            follow=True)
        self.assertContains(response, "disabled")

    # makes sure that next/submit button is enabled if choice selected
    def test_button_enabled(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="Race",
                                primary_power_perspective="Strength")
        dict_data = {
            'response': "strongly agree",
        }
        response = self.client.post(
            reverse('core:question_submit',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 1}), dict_data,
            follow=True)

        self.assertNotContains(response, "disabled")


class QuestionResponseTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.demographic = create_demographic(self.assessment)

        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = 0
        session.save()

    # users/<int:user_id>/assessments/<int:assessment_id>/question/<int:number>
    # 'users/'+self.user.pk+"/assessments/"+self.assessment.pk+"/demographics_submit"
    # testing to make sure the question form responses is setup right
    def test_response_page(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        response = self.client.get(
            reverse('core:question',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 1}),
            follow=True)

        # response = self.client.get('users/'+str(self.user.pk)+'/assessments/'+str(self.assessment.pk)+"/question/1")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "strongly agree")

    # testing to make sure submit works and processes data in new Response Object
    # TODO: fix submission to match everything else
    def test_response_form_good(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        Question.objects.create(number=2, title="question 2", sociocultural_location="test2",
                                primary_power_perspective="test2")
        dict_data = {
            'response': "strongly agree",
        }
        response = self.client.post(
            reverse('core:question_submit',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk, 'number': 1}), dict_data,
            follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Response.objects.get(question_number="1").sociocultural_location, 'test')

    # making sure a response form with bad data would get rejected with error message
    def test_response_form_bad(self):
        create_question()
        data = {'response': "Wrongfully Agree"}
        form = ResponseForm(data=data)
        self.assertFalse(form.is_valid())
        response = self.client.post(reverse('core:question_submit',
                                            kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk,
                                                    'number': 1}), data, follow=True)
        self.assertRedirects(response, reverse('core:question',
                                               kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk,
                                                       'number': 1}))
        messages = list(response.context.get('messages'))
        expected_message = Message(level=ERROR, message=INCORRECT_RESPONSE_MESSAGE)
        self.assertIn(expected_message, messages)

    def test_question_number_not_equals_to_last_question_plus_one(self):
        """Redirect to question with number = last_question + 1"""
        create_question()
        last_question = self.client.session['last_question']
        number = last_question + 2  # ensuring number is not equal to last_question + 1
        dict_data = dict(response='strongly agree')
        kwargs = {'user_id': self.user.pk, 'assessment_id': self.assessment.pk,
                  'number': number}
        response = self.client.post(reverse('core:question_submit',
                                            kwargs=kwargs), dict_data)
        kwargs.update({'number': last_question + 1})
        self.assertRedirects(response, reverse('core:question', kwargs=kwargs))

    def test_secondary_demographic_choice_same_as_assessment_demographic_choice(self):
        """
        Test if, when secondary_power_perspective is set,
        and secondary_demographic_choice matches assessment.demogrpahic.secondary_demographic_type,
        response gets set to secondary_power_perspective
        """
        question = Question.objects.create(number=1,
                                           title="question 1",
                                           sociocultural_location="Class",
                                           primary_power_perspective="Sensitivity",
                                           secondary_power_perspective="Oneness",
                                           secondary_demographic_type='age',
                                           secondary_demographic_choice=self.demographic.age)
        body = dict(response='strongly agree')
        kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk, number=question.number)
        response = self.client.post(reverse('core:question_submit', kwargs=kwargs), body, follow=True)
        self.assertEqual(response.status_code, 200)
        response = Response.objects.get(question_number=question.number, assessment_id=self.assessment.pk)
        self.assertEqual(response.power_perspective, question.secondary_power_perspective)

    def test_secondary_demographic_choice_different_from_assessment_demographic_choice(self):
        """
        Test if, when secondary_power_perspective is set,
        and secondary_demographic_choice is different from assessment.demogrpahic.secondary_demographic_type,
        response gets set to primary_power_perspective
        """
        question = Question.objects.create(number=1,
                                           title="question 1",
                                           sociocultural_location="Class",
                                           primary_power_perspective="Oneness",
                                           secondary_power_perspective="Strength",
                                           secondary_demographic_type='age',
                                           secondary_demographic_choice=self.demographic.age + '_not')
        body = dict(response='strongly agree')
        kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk, number=question.number)
        response = self.client.post(reverse('core:question_submit', kwargs=kwargs), body, follow=True)
        self.assertEqual(response.status_code, 200)
        response = Response.objects.get(question_number=question.number, assessment_id=self.assessment.pk)
        self.assertEqual(response.power_perspective, question.primary_power_perspective)


#
# class CalendartestsFREE(TestCase):
#
#     def setUp(self):
#         self.user = create_user()
#         self.assessment = create_assessment(self.user)
#         self.client = Client()
#         create_question()
#         session = self.client.session
#         session['user_id'] = self.user.pk
#         session['assessment_id'] = self.assessment.pk
#         session['last_question'] = len(Question.objects.all())
#         session['access_type'] = ACCESS_TYPE_PAID
#         session.save()
#
#     # test to make sure page is setup properly
#     def test_page_setup_finished(self):
#         kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk)
#         response = self.client.get(reverse('core:finished', kwargs=kwargs), Follow=False)
#         self.assertEqual(response.status_code, 200)
#         self.assertContains(response, "online, hour-long consultation")


class CalendartestsPAID(TestCase):
    def setUp(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        create_question()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = len(Question.objects.all())
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()

    # test to make sure page is setup properly
    def test_page_setup_finished(self):
        kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk)
        response = self.client.get(reverse('core:finished', kwargs=kwargs), Follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assessment complete")
        self.assertNotContains(response, "10to8")

    def test_group_finished_page_is_rendered_when_accesscode_id_in_session(self):
        session = self.client.session
        session['accesscode_id'] = 123
        session.save()

        kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk)
        response = self.client.get(reverse('core:finished', kwargs=kwargs), follow=False)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/finished_group.html')

    @override_settings(SCHEDULING_URL='https://example.com/schedule')
    def test_paid_finished(self):
        session = self.client.session
        session.save()
        kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk)
        response = self.client.get(reverse('core:finished', kwargs=kwargs), Follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Schedule Consultation")
        self.assertContains(response, "https://example.com/schedule")


class CalendartestsERRORS(TestCase):

    def setUp(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session.save()

    # if there is no last question go to demographic
    def test_redirct_to_dem_from_calendar(self):
        self.client = Client()
        session = self.client.session
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()
        kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk)
        response = self.client.get(reverse('core:finished', kwargs=kwargs), Follow=False)
        # should redirect
        self.assertEqual(response.status_code, 302)

    # if the last question is not the last in the set of questions, go to next question
    def test_redirect_to_question_from_calendar(self):
        self.client = Client()
        session = self.client.session
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()
        Question.objects.create(number=1, title="question 1", sociocultural_location="test",
                                primary_power_perspective="test")
        kwargs = dict(user_id=self.user.pk, assessment_id=self.assessment.pk)
        response = self.client.get(reverse('core:finished', kwargs=kwargs), Follow=False)
        # should redirect
        self.assertEqual(response.status_code, 302)


class ScoreTests(TestCase):

    def setUp(self):
        self.user = create_user()
        self.user.save()
        self.assessment = create_assessment(self.user)
        self.assessment.save()
        self.client = Client()
        create_question()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = len(Question.objects.all())
        session.save()

    # test if score url exists
    def test_score_url_exists(self):
        response = self.client.post(
            reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)), follow=True)
        self.assertRedirects(response,
                             reverse('core:finished',
                                     kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))

    # tests if score object is created
    def test_score_exists(self):
        session = self.client.session
        dt = str(datetime.now())
        session['year'] = int(dt[0:4]) + 1
        session['month'] = 1
        session['day'] = 1
        session['hour'] = 1
        session['minute'] = 1
        session['second'] = 1
        session.save()
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.assertEqual(Score.objects.count(), 1)

    # test no duplicate score object created
    def test_assessment_has_score(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.assertTrue(self.assessment.score is not None)

    # tests sensitivity subscore
    def test_score_sub_score_race_sensitivity_test(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Sensitivity", sociocultural_location="Race")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        self.race_score = Race_Score.objects.get(score=self.score)
        self.assertEqual(self.race_score.sensitivity, 4)

    # tests oneness subscore
    def test_score_sub_score_race_oneness_test(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Oneness", sociocultural_location="Race")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        self.race_score = Race_Score.objects.get(score=self.score)
        self.assertEqual(self.race_score.oneness, 4)

    # tests strength subscore
    def test_score_sub_score_race_strength_test(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        self.race_score = Race_Score.objects.get(score=self.score)
        self.assertEqual(self.race_score.strength, 4)

    # tests appreciation subscore
    def test_score_sub_score_race_appreciation_test(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Appreciation", sociocultural_location="Race")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        self.race_score = Race_Score.objects.get(score=self.score)
        self.assertEqual(self.race_score.appreciation, 4)

    # tests leveraged subscore
    def test_score_sub_score_race_leveraged_test(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Leveraged", sociocultural_location="Race")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        self.race_score = Race_Score.objects.get(score=self.score)
        self.assertEqual(self.race_score.leveraged, 4)

    # tests main score
    def test_score_main_score(self):
        Response.objects.create(assessment=self.assessment, question_number=1, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Race")
        Response.objects.create(assessment=self.assessment, question_number=2, response="strongly agree",
                                power_perspective="Strength", sociocultural_location="Gender")
        self.client.post(reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)))
        self.score = Score.objects.get(assessment=self.assessment)
        self.assertEqual(self.score.strength_total, 8)

    def test_verbose_score_test(self):
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


class RedirectionTest(TestCase):
    # redirections from various parts of the PDA to see if user can go from start to finish successfully

    def test_redirect_to_registration_from_creating_assessment(self):
        session = self.client.session
        session['access_type'] = ACCESS_TYPE_PAID
        session['user_id'] = 1
        session.save()
        response = self.client.get(reverse('core:create_assessment', kwargs=dict(user_id=1)), follow=True)
        expected_url = reverse('core:register')
        self.assertRedirects(response=response, expected_url=expected_url)

    def test_redirect_to_access_type_from_demographic_submit(self):
        dict_data = DEMOGRAPHIC_DICT
        session = self.client.session
        session['user_id'] = 1
        session['assessment_id'] = 1
        session['access_type'] = ACCESS_TYPE_PAID
        session.save()
        kwargs = dict(user_id=1, assessment_id=1)
        response = self.client.post(
            reverse('core:demographics_submit', kwargs=kwargs),
            dict_data, follow=True)
        expected_url = reverse('core:choose_access_type', kwargs={'user_id': 1})
        self.assertRedirects(response=response, expected_url=expected_url)

    def test_redirect_to_access_type_from_question_submit(self):
        self.user = create_user()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = 1
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = 0
        session.save()
        Question.objects.create(number=1, title="question 1", sociocultural_location="Race",
                                primary_power_perspective="Strength")
        dict_data = {
            'response': "strongly agree",
        }
        response = self.client.post(
            reverse('core:question_submit',
                    kwargs={'user_id': self.user.pk, 'assessment_id': 1, 'number': 1}), dict_data,
            follow=True)
        expected_url = reverse('core:choose_access_type', kwargs={'user_id': self.user.pk})
        self.assertRedirects(response=response, expected_url=expected_url)

    def test_redirect_to_access_type_from_score(self):
        Question.objects.create(number=1, title="question 1", sociocultural_location="Race",
                                primary_power_perspective="Strength")
        self.user = create_user()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = 1
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()

        response = self.client.get(
            reverse('core:score',
                    kwargs={'user_id': self.user.pk, 'assessment_id': 1}), follow=True)
        expected_url = reverse('core:choose_access_type', kwargs={'user_id': self.user.pk})
        self.assertRedirects(response=response, expected_url=expected_url)

    def test_redirect_to_finished_from_score(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()
        self.score = Score.objects.create(assessment=self.assessment)
        response = self.client.get(
            reverse('core:score',
                    kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}), follow=True)
        expected_url = reverse('core:finished', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk})
        self.assertRedirects(response=response, expected_url=expected_url)

    def test_redirect_to_register_from_score(self):
        session = self.client.session
        session['user_id'] = 1
        session['assessment_id'] = 1
        session['access_type'] = ACCESS_TYPE_PAID
        session['last_question'] = len(Question.objects.all())
        session.save()
        response = self.client.get(
            reverse('core:score',
                    kwargs={'user_id': 1, 'assessment_id': 1}), follow=True)
        expected_url = reverse('core:register')
        self.assertRedirects(response=response, expected_url=expected_url)


class ClearSessionViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_is_finished_session_key_absent(self):
        """Leave session as is and redirect to continue"""
        self.assertNotIn('is_finished', self.client.session)  # sanity check
        set_session_key_for_client(self.client, key='key',
                                   value='value')  # fill up with dummy data in order to later check if they are still there
        items_before_visiting = self.client.session.items()

        response = self.client.get(reverse('core:clear_session'))
        items_after_visiting = self.client.session.items()
        self.assertEqual(items_before_visiting, items_after_visiting)
        self.assertRedirects(response, reverse('core:continue'), target_status_code=302)

    def test_is_finished_session_key_present(self):
        """Clear session and redirect to index"""
        set_session_key_for_client(self.client, key='is_finished', value=True)
        self.assertFalse(self.client.session.is_empty())  # sanity check

        response = self.client.get(reverse('core:clear_session'))
        self.assertTrue(self.client.session.is_empty())
        self.assertRedirects(response, reverse('core:index'))


# tests related to generating PDF report
class PDFTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        self.score = Score()
        self.score.assessment = self.assessment
        self.score.save()
        # theres a problem here ... tests fail because the related scores aren't being made.
        self.score.refresh_from_db()
        create_question()

    # tests that button appears on finished template
    # def test_report_button_appears(self):
    #     session = self.client.session
    #     session['user_id'] = self.user.pk
    #     session['assessment_id'] = self.assessment.pk
    #     session['access_type'] = ACCESS_TYPE_PAID
    #     session['last_question'] = len(Question.objects.all())
    #     session.save()
    #     response = self.client.post(
    #         reverse('core:finished', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)), follow=True)
    #     self.assertContains(response, "Get a PDF Report")

    # test no longer works, downloading file is not necessary - saves to model with push of button
    # tests that response is attachment type with correct name
    # def test_report_file_response(self):
    #     session = self.client.session
    #     session['user_id'] = self.user.pk
    #     session['assessment_id'] = self.assessment.pk
    #     session['access_type'] = ACCESS_TYPE_PAID
    #     session['last_question'] = len(Question.objects.all())
    #     session.save()
    #     response = self.client.get(
    #         reverse('core:pdf_results', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
    #         follow=True)
    #     self.assertEqual(response.get("Content-Disposition"),
    #                       'attachment; filename="tj3va@virginia.edu_1_results.pdf"')

    # tests that response has successful status code (200)
    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_report_response_code(self, mock_save):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming
        session = self.client.session
        session['user_id'] = self.user.pk
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = len(Question.objects.all())
        session.save()
        response = self.client.get(
            reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk)),
            follow=True)
        self.assertEqual(response.status_code, 200)

    # tests that attempting to view pdf with no assessment redirects to choose_access_type
    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_report_no_assessment(self, mock_save):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming
        session = self.client.session
        session['user_id'] = self.user.pk
        session.save()
        path = reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=0))
        self.assertRedirects(self.client.get(path, follow=False),
                             reverse('core:choose_access_type', kwargs={'user_id': self.user.pk}))

    # tests that attempting to view pdf with no last_question set redirects to demographics
    @patch('storages.backends.s3boto3.S3Boto3Storage.save')
    def test_report_no_last_question(self, mock_save):
        naming = "pdfs/" + "tj3vavirginia.edu" + "_" + str(self.assessment.pk) + "_results.pdf"
        mock_save.return_value = naming
        session = self.client.session
        session['user_id'] = self.user.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['assessment_id'] = self.assessment.pk
        session.save()
        path = reverse('core:score', kwargs=dict(user_id=self.user.pk, assessment_id=self.assessment.pk))
        self.assertRedirects(self.client.get(path, follow=False), reverse('core:demographics',
                                                                          kwargs={'user_id': self.user.pk,
                                                                                  'assessment_id': self.assessment.pk}))


# tests related to generating PDF report
class InstructionsTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.assessment = create_assessment(self.user)
        self.client = Client()
        session = self.client.session
        session['user_id'] = self.user.pk
        session['access_type'] = ACCESS_TYPE_PAID
        session['assessment_id'] = self.assessment.pk
        session['last_question'] = 0
        session.save()
        create_question()

    def test_PDA_purpose_not_in_instructions(self):
        response = self.client.get(
            reverse('core:instructions', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "The PDA has 70 items and requires between 20 and 60 minutes to complete")

    def test_correct_text(self):
        response = self.client.get(
            reverse('core:instructions', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<b>DIRECTIONS:</b> For each numbered item below, place the let")

    def test_must_do_demographics(self):
        session = self.client.session
        del session['last_question']
        session.save()
        response = self.client.get(
            reverse('core:instructions', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "19 demographics questions")

    def test_instructions_go_to_correct_question(self):
        Question.objects.create(number=2, title="question 2", sociocultural_location="test2",
                                primary_power_perspective="test2")
        session = self.client.session
        session['last_question'] = 1
        session.save()
        response = self.client.get(
            reverse('core:instructions', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "test2")

    def test_instructions_go_to_score(self):
        session = self.client.session
        session['last_question'] = 1
        session.save()
        response = self.client.get(
            reverse('core:instructions', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
            follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "online, hour-long consultation")

    def test_instructions_serv_err(self):
        session = self.client.session
        last_question = 100
        session['last_question'] = last_question
        session.save()
        with self.assertRaisesMessage(AssertionError, INVALID_LAST_QUESTION_ERROR_MESSAGE % last_question):
            self.client.get(
                reverse('core:instructions', kwargs={'user_id': self.user.pk, 'assessment_id': self.assessment.pk}),
                follow=True)


class CustomErrorHandlerTest(TestCase):
    def setUp(self):
        self.client = Client()

    @override_settings(DEBUG=False)
    def test_custom_page_not_found_view(self):
        """Render 'core/404.hmtl' and throw a 404 """
        response = self.client.get('/does_not_exist')
        self.assertContains(response, 'continue with the assessment', status_code=404)

    def test_custom_server_error_view_when_debug_is_true(self):
        """Render 'core/500.hmtl' and throw a 500 """
        request = HttpRequest()
        response = custom_server_error(request)  # TODO: Find better way to test
        self.assertContains(response, 'something went wrong', status_code=500)

    def test_custom_server_error_view_when_debug_is_false(self):
        """Render 'core/500.hmtl' and throw a 500, and log an error """
        settings.DEBUG = False  # @override_settings decorator doesn't work for DEBUG=False, so overriding here
        logger_name = 'core.views'
        logger = logging.getLogger(logger_name)
        disable_console_logging(logger)
        level = 'ERROR'
        with self.assertLogs(logger=logger, level=level) as cm:
            request = HttpRequest()
            response = custom_server_error(request)  # TODO: Find better way to test
            self.assertContains(response, 'something went wrong', status_code=500)
        self.assertEqual(len(cm.records), 1, "Wrong number of calls for logger %r in %r level." % (logger, level))
        self.assertEqual(cm.output, [f'ERROR:{logger_name}:{INTERNAL_SERVER_ERROR_LOG_MESSAGE}'])


class CompleteConsultantRegistrationViewTest(TestCase):
    def setUp(self):
        self.pseudo_consultant_admin = CompleteConsultantRegistrationView().pseudo_consultant_admin

    def test_is_view_wrapped_by_admin_view(self):
        """Return true"""
        resolver = get_resolver()
        resolver_match = resolver.resolve(
            reverse('admin:core_consultant_complete_registration', kwargs=dict(consultant_pk=0)))
        self.assertTrue(is_function_wrapped_by_decorator(resolver_match.func, 'AdminSite.admin_view'))

    def test_member_variable_pseudo_consultant_admin_s_has_perm_method_when_incorrect_user_logged_in(self):
        """Return false"""
        consultant_dict = CONSULTANT_DICT.copy()
        consultant_dict.update(dict(username='c1', email='c1@email.com'))
        consultant_1 = create_consultant(consultant_dict)
        consultant_dict.update(dict(username='c2', email='c2@email.com'))
        consultant_2 = create_consultant(consultant_dict)
        request = HttpRequest()
        request.user = consultant_2  # faking login
        self.assertFalse(self.pseudo_consultant_admin.has_perm(request, consultant_1))

    def test_member_variable_pseudo_consultant_admin_s_has_perm_method_when_correct_user_logged_in(self):
        """Return true"""
        consultant = create_consultant()
        request = HttpRequest()
        request.user = consultant  # faking login
        self.assertTrue(CompleteConsultantRegistrationView().pseudo_consultant_admin.has_perm(request, consultant))

    def test_valid_get_request(self):
        """Successfully render page"""
        consultant = create_consultant()
        self.client.force_login(consultant)
        response = self.client.get(
            reverse('admin:core_consultant_complete_registration', kwargs=dict(consultant_pk=consultant.pk)))
        self.assertEqual(response.status_code, 200)

    def test_valid_post_request(self):
        """Successfully update consultant"""
        consultant = create_consultant()
        updated_username = consultant.username + '_updated'
        self.client.force_login(consultant)

        data = dict(username=updated_username,
                    email=consultant.email,
                    password1='test_password123',
                    password2='test_password123')
        self.client.post(
            reverse('admin:core_consultant_complete_registration', kwargs=dict(consultant_pk=consultant.pk)), data=data)
        updated_consultant = Consultant.objects.get(pk=consultant.pk)

        self.assertEqual(updated_consultant.username, updated_username)


class VerifyCompleteConsultantRegistrationLinkViewTest(TestCase):
    def test_invalid_uid(self):
        """Show invalid link message"""
        consultant = create_consultant()
        token = default_token_generator.make_token(consultant)
        uidb64 = urlsafe_base64_encode(force_bytes(consultant.pk + 2))  # making the link invalid
        response = self.client.get(reverse('admin:core_consultant_verify_registration_completion_link',
                                           kwargs=dict(uidb64=uidb64, token=token)))
        self.assertContains(response, INVALID_LINK_MESSAGE)

    def test_valid_link(self):
        """Redirect to complete_registration"""
        consultant = create_consultant()
        token = default_token_generator.make_token(consultant)
        uidb64 = urlsafe_base64_encode(force_bytes(consultant.pk))
        response = self.client.get(reverse('admin:core_consultant_verify_registration_completion_link',
                                           kwargs=dict(uidb64=uidb64, token=token)))
        self.assertRedirects(response, reverse('admin:core_consultant_complete_registration',
                                               kwargs=dict(consultant_pk=consultant.pk)))

    def test_already_used_link(self):
        """Show invalid link message"""
        consultant = create_consultant()
        token = default_token_generator.make_token(consultant)
        uidb64 = urlsafe_base64_encode(force_bytes(consultant.pk))
        url = reverse('admin:core_consultant_verify_registration_completion_link',
                      kwargs=dict(uidb64=uidb64, token=token))
        self.client.get(url)
        response = self.client.get(url)  # visiting the link twice invalidates it
        self.assertContains(response, INVALID_LINK_MESSAGE)


class CompleteViewOnlyAdminRegistrationViewTest(TestCase):
    def setUp(self):
        self.pseudo_view_only_admin = CompleteViewOnlyAdminRegistrationView().pseudo_view_only_admin_admin

    def test_is_view_wrapped_by_admin_view(self):
        """Return true"""
        resolver = get_resolver()
        resolver_match = resolver.resolve(
            reverse('admin:core_view_only_admin_complete_registration', kwargs=dict(view_only_admin_pk=0)))
        self.assertTrue(is_function_wrapped_by_decorator(resolver_match.func, 'AdminSite.admin_view'))

    def test_member_variable_pseudo_view_only_admin_s_has_perm_method_when_incorrect_user_logged_in(self):
        """Return false"""
        view_only_admin_dict = VIEW_ONLY_ADMIN_DICT.copy()
        view_only_admin_dict.update(dict(username='v1', email='v1@email.com'))
        view_only_admin_1 = create_view_only_admin(view_only_admin_dict)
        view_only_admin_dict.update(dict(username='v2', email='v2@email.com'))
        view_only_admin_2 = create_view_only_admin(view_only_admin_dict)
        request = HttpRequest()
        request.user = view_only_admin_2  # faking login
        self.assertFalse(self.pseudo_view_only_admin.has_perm(request, view_only_admin_1))

    def test_member_variable_pseudo_view_only_admin_s_has_perm_method_when_correct_user_logged_in(self):
        """Return true"""
        view_only_admin = create_view_only_admin()
        request = HttpRequest()
        request.user = view_only_admin  # faking login
        self.assertTrue(
            CompleteViewOnlyAdminRegistrationView().pseudo_view_only_admin_admin.has_perm(request, view_only_admin))

    def test_valid_get_request(self):
        """Successfully render page"""
        view_only_admin = create_view_only_admin()
        self.client.force_login(view_only_admin)
        response = self.client.get(
            reverse('admin:core_view_only_admin_complete_registration',
                    kwargs=dict(view_only_admin_pk=view_only_admin.pk)))
        self.assertEqual(response.status_code, 200)


class VerifyCompleteViewOnlyAdminRegistrationLinkViewTest(TestCase):
    def test_invalid_uid(self):
        """Show invalid link message"""
        view_only_admin = create_view_only_admin()
        token = default_token_generator.make_token(view_only_admin)
        uidb64 = urlsafe_base64_encode(force_bytes(view_only_admin.pk + 2))  # making the link invalid
        response = self.client.get(reverse('admin:core_view_only_admin_verify_registration_completion_link',
                                           kwargs=dict(uidb64=uidb64, token=token)))
        self.assertContains(response, INVALID_LINK_MESSAGE)

    def test_valid_link(self):
        """Redirect to complete_registration"""
        view_only_admin = create_view_only_admin()
        token = default_token_generator.make_token(view_only_admin)
        uidb64 = urlsafe_base64_encode(force_bytes(view_only_admin.pk))
        response = self.client.get(reverse('admin:core_view_only_admin_verify_registration_completion_link',
                                           kwargs=dict(uidb64=uidb64, token=token)))
        self.assertRedirects(response, reverse('admin:core_view_only_admin_complete_registration',
                                               kwargs=dict(view_only_admin_pk=view_only_admin.pk)))

    def test_already_used_link(self):
        """Show invalid link message"""
        view_only_admin = create_view_only_admin()
        token = default_token_generator.make_token(view_only_admin)
        uidb64 = urlsafe_base64_encode(force_bytes(view_only_admin.pk))
        url = reverse('admin:core_view_only_admin_verify_registration_completion_link',
                      kwargs=dict(uidb64=uidb64, token=token))
        self.client.get(url)
        response = self.client.get(url)  # visiting the link twice invalidates it
        self.assertContains(response, INVALID_LINK_MESSAGE)


class CustomPasswordResetViewsTests(TestCase):
    client = Client()
    disable_console_logging(logging.getLogger())

    def test_valid_get_request(self):
        """Successfully retrieves page"""
        response = self.client.get(reverse('admin_password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reset my password')


class CustomPasswordResetRelatedViewsTests(TestCase):
    """Tests the various password reset related views namely, CustomPasswordResetView,
    CustomPasswordResetDoneView, CustomPasswordResetConfirmView, CustomPasswordResetCompleteView
    (Only tests happy path, since Django has already tested the base View classes extensively) """
    client = Client()
    disable_console_logging(logging.getLogger())

    def test_get_password_reset_page(self):
        """Successfully render page"""
        response = self.client.get(reverse('admin_password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reset my password')

    def test_valid_password_reset_request(self):
        """Send email with valid reset link, and successfully reset password"""
        # modified from: django/tests/auth_tests/test_views.py
        old_password = 'old_password_123'
        new_password = 'new_password_123'
        user = AuthUser.objects.create(username='test', email='test@test.com')
        user.set_password(old_password)
        user.save()
        assert self.client.login(username=user.username, password=old_password)  # sanity check, password works

        # send a password reset request
        response = self.client.post(reverse('admin_password_reset'), data=dict(email=user.email))
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        urlmatch = re.search(r"https?://[^/]*(/.*reset/\S*)", mail.outbox[0].body)
        self.assertIsNotNone(urlmatch, "No URL found in sent email")

        # follow reset url to go to set new password page
        path = urlmatch.groups()[0]
        response = self.client.get(path)
        self.assertEqual(response.resolver_match.view_name, 'password_reset_confirm')

        # post new password
        path = response.url
        response = self.client.post(path, {
            'new_password1': new_password,
            'new_password2': new_password,
        })
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.assertFalse(self.client.login(username=user.username, password=old_password))
        self.assertTrue(self.client.login(username=user.username, password=new_password))


class AssessmentDetailedViewTest(TestCase):
    def test_is_view_wrapped_by_admin_view(self):
        """Return true"""
        resolver = get_resolver()
        resolver_match = resolver.resolve(
            reverse('admin:core_assessment_detailed_view', kwargs=dict(assessment_pk=0)))
        self.assertTrue(is_function_wrapped_by_decorator(resolver_match.func, 'AdminSite.admin_view'))

    def test_method_get_permission_object_when_assessment_does_not_exist(self):
        """Return None"""
        assessment_pk = 1
        assert len(Assessment.objects.filter(pk=assessment_pk)) == 0  # sanity check
        view = AssessmentDetailedView(kwargs=dict(assessment_pk=assessment_pk))
        self.assertIsNone(view.get_permission_object())

    def test_method_get_permission_object_when_assessment_exists(self):
        """Returns assessment"""
        assessment = create_assessment(user=create_user())
        view = AssessmentDetailedView(kwargs=dict(assessment_pk=assessment.pk))
        self.assertEqual(view.get_permission_object(), assessment)

    def test_staticmethod_sort_responses_by_response_choice(self):
        """Should return responses sorted by their response choice score"""
        assessment = create_assessment()
        response_with_score_0 = create_response(assessment,
                                                {**RESPONSE_DICT, 'response': "strongly disagree"})
        response_with_score_1 = create_response(assessment,
                                                {**RESPONSE_DICT, 'response': "disagree more than agree"})
        response_with_score_2 = create_response(assessment,
                                                {**RESPONSE_DICT, 'response': "agree and disagree about the same"})
        response_with_score_3 = create_response(assessment,
                                                {**RESPONSE_DICT, 'response': "agree more than disagree"})
        response_with_score_4 = create_response(assessment,
                                                {**RESPONSE_DICT, 'response': "strongly agree"})
        responses = [response_with_score_2,
                     response_with_score_0,
                     response_with_score_1,
                     response_with_score_4,
                     response_with_score_3, ]

        expected = [response_with_score_0,
                    response_with_score_1,
                    response_with_score_2,
                    response_with_score_3,
                    response_with_score_4, ]
        actual = AssessmentDetailedView.sort_responses_by_response_choice(responses)
        self.assertEqual(actual, expected)

    def test_staticmethod_get_pdf_link_when_PDF_exists(self):
        """Return value includes PDF file path"""
        assessment = create_assessment()
        file_path = "path/report.pdf"
        assessment.PDF = file_path
        assessment.save()
        self.assertIn(file_path, AssessmentDetailedView.get_pdf_link_for_assessment(assessment))

    def test_staticmethod_get_pdf_link_when_PDF_does_not_exist(self):
        """Return no report available"""
        assessment = create_assessment()
        self.assertEqual("No report available", AssessmentDetailedView.get_pdf_link_for_assessment(assessment))

    def test_staticmethod_get_consultants_for_assessment_when_no_consultants(self):
        """Should return No consultants assigned"""
        assessment = create_assessment()
        self.assertEqual("No consultants assigned", AssessmentDetailedView.get_consultants_for_assessment(assessment))

    def test_staticmethod_get_consultants_for_assessment(self):
        """Should return comma seperated list of consultants"""
        assessment = create_assessment()
        consultant_1 = create_consultant(
            {**CONSULTANT_DICT, 'username': 'c1', 'first_name': "consultant", 'last_name': "one",
             'email': "consultant1@email.com"})
        consultant_2 = create_consultant(
            {**CONSULTANT_DICT, 'username': 'c2', 'first_name': "consultant", 'last_name': "two",
             'email': "consultant2@email.com"})
        assessment.consultants.add(consultant_1, consultant_2)
        assessment.save()
        self.assertEqual("consultant one (consultant1@email.com), consultant two (consultant2@email.com)",
                          AssessmentDetailedView.get_consultants_for_assessment(assessment))

    def test_response_when_user_is_none(self):
        """Page should render with message saying user does not exist"""
        login_as_super_user(self.client)
        assessment = create_assessment()
        assert assessment.user is None  # sanity check
        response = self.client.get(
            reverse('admin:core_assessment_detailed_view', kwargs=dict(assessment_pk=assessment.pk)))
        self.assertContains(response, "Assessment %s Details" % assessment.pk)
        self.assertContains(response, "User no longer exists")

    def test_response_when_demographics_is_none(self):
        """Page should render with message saying demographics info does not exist"""
        login_as_super_user(self.client)
        assessment = create_assessment()
        assert len(Demographic.objects.filter(assessment=assessment)) == 0  # sanity check
        response = self.client.get(
            reverse('admin:core_assessment_detailed_view', kwargs=dict(assessment_pk=assessment.pk)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assessment %s Details" % assessment.pk)
        self.assertContains(response, "No demographic information available")

    def test_response_when_user_and_demographic_present(self):
        """Page should render"""
        login_as_super_user(self.client)
        assessment = create_assessment(user=create_user())
        create_demographic(assessment=assessment)
        for i in range(70):
            question_number = i + 1
            create_question({**QUESTION_DICT,
                             'number': question_number,
                             'primary_power_perspective': POWER_PERSPECTIVES[i % 5][0],
                             'sociocultural_location': SOCIOCULTURAL_LOCATIONS[i % 7][0]
                             }
                            )
            create_response(assessment=assessment, response_dict={**RESPONSE_DICT,
                                                                  'question_number': question_number,
                                                                  'response': random.choice(
                                                                      Response.RESPONSE_CHOICES)[0]
                                                                  })
        response = self.client.get(
            reverse('admin:core_assessment_detailed_view', kwargs=dict(assessment_pk=assessment.pk)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assessment %s Details" % assessment.pk)
