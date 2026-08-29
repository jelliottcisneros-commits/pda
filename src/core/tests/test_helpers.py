from django.http import HttpRequest
from django.test import TestCase

from core.helpers import *
from core.models import User


class TestIsRequestFromCoreAppFunction(TestCase):
    def test_request_is_not_from_core_app(self):
        """return false"""
        request = self.client.get(reverse('admin:index'))
        self.assertFalse(is_request_from_core_app(request))

    def test_request_is_from_core_app(self):
        """return true"""
        request = self.client.get(reverse('core:index'))
        self.assertTrue(is_request_from_core_app(request))

    def test_request_has_no_resolver_match(self):
        """return false"""
        request = HttpRequest()
        assert request.resolver_match is None  # sanity check
        self.assertFalse(is_request_from_core_app(request))


class TestFunctionGetDemographicFieldsAsChoices(TestCase):
    def setUp(self):
        self.demographic_fields_as_choices = get_demographic_fields_as_choices()
        self.fields_to_include = set(filter(lambda x: x.choices, Demographic._meta.fields))
        self.fields_to_exclude = set(Demographic._meta.fields) - self.fields_to_include

    def test_exclusion_of_to_exclude_fields(self):
        """Should not be present"""
        for field in self.fields_to_exclude:
            with self.subTest(field=field):
                field_as_choice = (field.name, field.verbose_name)
                self.assertNotIn(field_as_choice, self.demographic_fields_as_choices)

    def test_inclusion_of_to_include_fields(self):
        """Should be present"""
        for field in self.fields_to_include:
            with self.subTest(field=field):
                field_as_choice = (field.name, field.verbose_name)
                self.assertIn(field_as_choice, self.demographic_fields_as_choices)


class GetDemographicFieldToChoicesMapFunctionTests(TestCase):
    def setUp(self):
        self.demographic_field_to_choices_map = get_demographic_field_to_choices_map()
        self.fields_to_include = set(filter(lambda x: x.choices, Demographic._meta.fields))
        self.fields_to_exclude = set(Demographic._meta.fields) - self.fields_to_include

    def test_exclusion_of_to_exclude_fields(self):
        """Should not be present"""
        for field in self.fields_to_exclude:
            with self.subTest(field=field):
                self.assertNotIn(field.name, self.demographic_field_to_choices_map)

    def test_correct_choices_set(self):
        for field in self.fields_to_include:
            with self.subTest(field=field):
                expected = field.choices
                actual = self.demographic_field_to_choices_map[field.name]
                self.assertEqual(expected, actual)


class GetFieldsDictFunctionTests(TestCase):
    def test_function(self):
        user = User(first_name="First", last_name="Last", email='email@domain.com', phone='111-111-1111',
                    can_retake=False)
        fields_to_exclude = ('can_retake', 'id',)
        field_dict = get_field_dict(user, exclude=fields_to_exclude)
        expected = {
            "First name": "First",
            "Last name": "Last",
            "Email": "email@domain.com",
            "Phone": "111-111-1111",
        }
        self.assertEqual(field_dict, expected)
