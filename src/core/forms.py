from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.forms import UserCreationForm as AuthUserCreationForm, UsernameField
from django.contrib.auth.models import User as AuthUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import ModelForm, RadioSelect, TextInput, CharField, EmailField, Form, ChoiceField, Select
from django.utils.crypto import get_random_string

from core.helpers import get_demographic_fields_as_choices
from .models import Demographic, Response, UnverifiedUser, Consultant, Question
from .models import ViewOnlyAdmin

phone_regex = r'^\(?[0-9]{3}\)?[-.●]?[0-9]{3}[-.●]?[0-9]{4}$'  # source: https://www.oreilly.com/library/view/regular


# -expressions-cookbook/9781449327453/ch04s02.html


class PhoneField(CharField):
    default_validators = [RegexValidator(regex=phone_regex, message="Phone number is not a valid US Phone number")]
    widget = TextInput(
        attrs=dict(title="Examples: 1234567890, 123-456-7890, 123.456.7890, 123 456 7890 or (123) 456 7890",
                   pattern="^\(?[0-9]{3}\)?[-.●]?[0-9]{3}[-.●]?[0-9]{4}$", placeholder="ex. 123-456-7890"))


class UnverifiedUserForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(UnverifiedUserForm, self).__init__(*args, **kwargs)
        self.fields['email'].widget.attrs['autofocus'] = 'true'
        self.fields['email'].widget.attrs['placeholder'] = 'ex. john.doe@example.com'
        self.fields['first_name'].widget.attrs['placeholder'] = 'ex. John'
        self.fields['last_name'].widget.attrs['placeholder'] = 'ex. Doe'

    class Meta:
        model = UnverifiedUser
        fields = ['email', 'first_name', 'last_name', 'phone']
        field_classes = {
            'phone': PhoneField,
            'email': CharField
        }

        # fields['email'].widget.attrs['autofocus'] = 'true'
        # fields['email'].widget.attrs['placeholder'] = 'true'
        # fields['first_name'].widget.attrs['placeholder'] = 'true'
        # fields['last_name'].widget.attrs['placeholder'] = 'true'


class UserForm(Form):
    email = EmailField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'placeholder': 'ex. john.doe@example.com'})


# a form for the demographics Each one has answers based upon what is on the current POD site defaults to None which
# will throw errors (on purpose), form cannot be submitted until then (handled properly in html and view)
class DemographicForm(ModelForm):
    class Meta:
        model = Demographic
        fields = '__all__'
        exclude = ['assessment']
        labels = {
            "age": "Age",
            "religion": "Current religious/non-religious identification",
            "area": "Which of the following best describes the area in which you live?",
            "disability": "Ability/disability status/identification",
            "socioeconomic": "Which most closely describes your current socioeconomic status?",
            "status": "How would you describe your primary socioeconomic background -how you grew up-?",
            "employment": "Employment Status: Are you currenty...?",
            "education": "What is the highest degree or level of school you have completed?",
            "marital": "Relational/Marital Status",
            "race_or_culture": "If you live in the United States, which of the following best represents your "
                               "racial or cultural heritage?",
            "perception": "How are you most often perceived related to skin color",
            "sexual_orientation": "Sexual Orientation",
            "gender": "What is closest to how you primarily identify with regard to gender?",
            "gender_perception": "I tend to be viewed by society…",
            "country_of_birth": "What is the country of your birth?",
            "country_of_birth_state": "If you are from the United States--which state?",
            "clocation": "Country in which you live currently",
            "cstate": "If you live in the United States currently, which state?",
            "purpose": "What percentage of the time are you deeply engaged with a clear personal sense of purpose?",
            "safety": "Which of the following sentences do you think best completes this phrase: Safety comes...",
        }


class ResponseForm(ModelForm):
    class Meta:
        model = Response
        fields = ['response']
        widgets = {
            'response': RadioSelect(attrs={'onclick': "enableButton()", 'autofocus': 'true'})
        }


class ConsultantCreationForm(ModelForm):
    """Form used by admin for adding new consultants"""

    class Meta:
        model = Consultant
        fields = ('email',)
        field_classes = {'email': EmailField}

    @staticmethod
    def generate_unique_username_from_email(email):
        def is_username_unique_among_consultants(username):
            return AuthUser.objects.filter(username=username).count() == 0

        username = email.split('@')[0]
        validator = UnicodeUsernameValidator()
        try:
            validator(username)  # ensure the username is valid unicode
        except ValidationError:
            username = get_random_string()  # if not generate a random one that is valid
        while not is_username_unique_among_consultants(username):
            username += get_random_string(
                length=1)  # trying to make it unique while not going too far from the original
        return username

    def save(self, commit=True):
        # Overriding so that admin only has to provide an email, and all the other fields will be generated
        self.instance.username = self.generate_unique_username_from_email(
            self.cleaned_data['email'])  # setting username from the user in the email
        self.instance.is_staff = True
        consultant = super().save(commit=False)
        consultant.set_password(BaseUserManager().make_random_password())  # setting random password,
        # consultant will get to reset later.
        if commit:
            consultant.save()
        return consultant


class CompleteConsultantRegistrationForm(AuthUserCreationForm):
    """Form used by consultant to fill in their information when they first log in"""

    class Meta:
        model = Consultant
        fields = ('username', 'first_name', 'last_name', 'email')
        field_classes = {'email': EmailField, 'username': UsernameField}


class ViewOnlyAdminCreationForm(ModelForm):
    """Form used by admin for adding new consultants"""

    class Meta:
        model = ViewOnlyAdmin
        fields = ('email',)
        field_classes = {'email': EmailField}

    @staticmethod
    def generate_unique_username_from_email(email):
        def is_username_unique_among_view_only_admins(username):
            return AuthUser.objects.filter(username=username).count() == 0

        username = email.split('@')[0]
        validator = UnicodeUsernameValidator()
        try:
            validator(username)  # ensure the username is valid unicode
        except ValidationError:
            username = get_random_string()  # if not generate a random one that is valid
        while not is_username_unique_among_view_only_admins(username):
            username += get_random_string(
                length=1)  # trying to make it unique while not going too far from the original
        return username

    def save(self, commit=True):
        # Overriding so that admin only has to provide an email, and all the other fields will be generated
        self.instance.username = self.generate_unique_username_from_email(
            self.cleaned_data['email'])  # setting username from the user in the email
        self.instance.is_staff = True
        view_only_admin = super().save(commit=False)
        view_only_admin.set_password(BaseUserManager().make_random_password())  # setting random password,
        # consultant will get to reset later.
        if commit:
            view_only_admin.save()
        return view_only_admin


class CompleteViewOnlyAdminRegistrationForm(AuthUserCreationForm):
    class Meta:
        model = ViewOnlyAdmin
        fields = ('username', 'first_name', 'last_name', 'email')
        field_classes = {'email': EmailField, 'username': UsernameField}


class DemographicChoiceField(ChoiceField):
    choices = [(field.name, field.name) for field in Demographic._meta.fields]


class QuestionAdminForm(ModelForm):
    """Form that overrides the secondary_demographic_type and secondary_demographic_choice_fields to be select widgets
    with correct initial values """
    class Meta:
        model = Question
        fields = '__all__'
        widgets = {
            'secondary_demographic_type': Select(choices=[(None, '-----')] + get_demographic_fields_as_choices()),
            'secondary_demographic_choice': Select(choices=[(None, '-----')])
        }
