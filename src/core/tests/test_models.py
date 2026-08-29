from django.core.exceptions import ValidationError
from django.test import TestCase

from core.demographic_choices import DC
from core.models import AccessCode, AbstractUser
from core.tests.utils import *


class AccessCodeModelTest(TestCase):
    def test_str_method_when_access_code_is_negative_1(self):
        """Return value contains the word Unlimited"""
        access_code = AccessCode(uses_left=-1)
        self.assertIn('Uses Left: Unlimited', str(access_code))

    def test_accesscode_has_name(self):
        """Tests if name attribute works"""
        access_code = AccessCode(name="Bob", uses_left=1)
        self.assertIn('Bob - Uses Left: 1', str(access_code))


class AbstractUserModelTest(TestCase):
    def test_abstractuser_has_name(self):
        """Tests if name attribute works"""
        abstract_user = AbstractUser(first_name="Bob", last_name="Smith", email="fake@email.com")
        self.assertIn('Bob Smith (fake@email.com)', str(abstract_user))


class QuestionModelTest(TestCase):

    def test_question_has_name(self):
        """Tests if name attribute works"""
        question = Question(number=1,
                            title="question 1",
                            sociocultural_location='Gender',
                            primary_power_perspective="Strength",
                            pk=1)
        self.assertIn('Statement 1', str(question))

    def test_clean_method_when_secondary_power_perspective_not_set(self):
        """Create question"""
        question = Question(number=1,
                            title="question 1",
                            sociocultural_location='Gender',
                            primary_power_perspective="Strength")
        try:
            question.clean()
        except ValidationError:
            self.fail("Unexpectedly raised error")

    def test_clean_method_when_secondary_power_perspective_set_secondary_demographic_choice_not(self):
        """Raise validation error empty"""
        question = Question(number=1,
                            title="question 1",
                            sociocultural_location='Gender',
                            primary_power_perspective="Strength",
                            secondary_power_perspective="Appreciation")
        with self.assertRaises(ValidationError) as cm:
            question.clean()
        self.assertEquals(cm.exception.code, 'empty')

    def test_clean_method_when_invalid_demographic_type(self):
        """Raise validation error invalid"""
        question = Question(number=1,
                            title="question 1",
                            sociocultural_location='Gender',
                            primary_power_perspective="Strength",
                            secondary_power_perspective="Appreciation",
                            secondary_demographic_type='not a valid demographic field',
                            secondary_demographic_choice='not a valid choice')
        with self.assertRaises(ValidationError) as cm:
            question.clean()
        self.assertEquals(cm.exception.code, 'invalid')

    def test_clean_method_when_valid_demographic_type_but_invalid_demographic_choice(self):
        """Raise validation error invalid"""
        question = Question(number=1,
                            title="question 1",
                            sociocultural_location='Gender',
                            primary_power_perspective="Strength",
                            secondary_power_perspective="Appreciation",
                            secondary_demographic_type='gender_perception',
                            secondary_demographic_choice='not a valid choice')
        with self.assertRaises(ValidationError) as cm:
            question.clean()
        self.assertEquals(cm.exception.code, 'invalid')

    def test_clean_method_when_valid_demographic_type_and_choice(self):
        """Raise no error"""
        question = Question(number=1,
                            title="question 1",
                            sociocultural_location='Gender',
                            primary_power_perspective="Strength",
                            secondary_power_perspective="Appreciation",
                            secondary_demographic_type='gender_perception',
                            secondary_demographic_choice=DC.GENDER_PERCEPTION_CHOICES[0][0])
        try:
            question.clean()
        except ValidationError:
            self.fail("Unexpectedly raised error")
