from django.test import TestCase

from core.forms import ConsultantCreationForm, ViewOnlyAdminCreationForm
from core.models import Consultant, ViewOnlyAdmin


class ConsultantCreationFormTest(TestCase):

    def test_generate_unique_username_from_email_staticmethod_when_username_in_email_is_invalid_unicode(self):
        # create a username that is different from the one embedded in the email
        invalid_unicode_username = "en\u2013dash"
        email = f'{invalid_unicode_username}@email.com'
        form = ConsultantCreationForm()
        generated_username = form.generate_unique_username_from_email(email)
        self.assertNotEqual(generated_username, invalid_unicode_username)

    def test_generate_unique_username_from_email_staticmethod_when_username_in_email_is_valid_but_not_unique(self):
        # create a username that is at least one random character longer than the one passed in
        consultant = Consultant.objects.create(username='test', email='test@test.com')
        non_unique_username = consultant.username
        email = f'{non_unique_username}@email.com'
        generated_username = ConsultantCreationForm().generate_unique_username_from_email(email)
        self.assertNotEqual(non_unique_username, generated_username)
        self.assertIn(non_unique_username, generated_username)  # checking if part of the original is in the generated

    def test_generate_unique_username_from_email_staticmethod_when_username_is_valid_and_unique(self):
        # create a username from the username in email
        username = 'test'
        email = f'{username}@email.com'
        generated_username = ConsultantCreationForm().generate_unique_username_from_email(email)
        self.assertEqual(generated_username, username)

    def test_save_method(self):
        # creates a consultant with username from email, and sets is_staff to true
        email = 'test@test.com'
        form = ConsultantCreationForm(data=dict(email=email))
        self.assertTrue(form.is_valid())
        consultant = form.save()
        self.assertEqual(consultant.email, email)
        self.assertEqual(consultant.username, email.split('@')[0])
        self.assertTrue(consultant.is_staff)

class ViewOnlyAdminCreationFormTest(TestCase):
    
    def test_generate_unique_username_from_email_staticmethod_when_username_in_email_is_invalid_unicode(self):
        # create a username that is different from the one embedded in the email
        invalid_unicode_username = "en\u2013dash"
        email = f'{invalid_unicode_username}@email.com'
        form = ViewOnlyAdminCreationForm()
        generated_username = form.generate_unique_username_from_email(email)
        self.assertNotEqual(generated_username, invalid_unicode_username)

    def test_generate_unique_username_from_email_staticmethod_when_username_in_email_is_valid_but_not_unique(self):
        # create a username that is at least one random character longer than the one passed in
        view_only_admin = ViewOnlyAdmin.objects.create(username='test', email='test@test.com')
        non_unique_username = view_only_admin.username
        email = f'{non_unique_username}@email.com'
        generated_username = ViewOnlyAdminCreationForm().generate_unique_username_from_email(email)
        self.assertNotEqual(non_unique_username, generated_username)
        self.assertIn(non_unique_username, generated_username)  # checking if part of the original is in the generated

    def test_generate_unique_username_from_email_staticmethod_when_username_is_valid_and_unique(self):
        # create a username from the username in email
        username = 'test'
        email = f'{username}@email.com'
        generated_username = ViewOnlyAdminCreationForm().generate_unique_username_from_email(email)
        self.assertEqual(generated_username, username)

    def test_save_method(self):
        # creates a view-only admin with username from email, and sets is_staff to true
        email = 'test@test.com'
        form = ViewOnlyAdminCreationForm(data=dict(email=email))
        self.assertTrue(form.is_valid())
        view_only_admin = form.save()
        self.assertEqual(view_only_admin.email, email)
        self.assertEqual(view_only_admin.username, email.split('@')[0])
        self.assertTrue(view_only_admin.is_staff)
