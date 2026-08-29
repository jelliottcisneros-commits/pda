from django.conf import settings
from django.contrib.auth.models import User as AuthUser
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import CharField, EmailField, BooleanField, DateField, OneToOneField, ForeignKey
from django.utils import timezone
from django.utils.translation import ugettext as _
from guardian.shortcuts import *

from .constants import ACCESS_TYPE_PAID, ACCESS_TYPE_INST, USER_ALREADY_EXISTS_MESSAGE
from .demographic_choices import DC


def assessment_pdf_storage():
    if settings.IS_PRODUCTION:
        from TheSum.storage_backends import PrivateMediaStorage

        return PrivateMediaStorage()
    return FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)


POWER_PERSPECTIVES = [("Sensitivity", "Sensitivity"), ("Oneness", "Oneness"), ("Strength", "Strength"),
                      ("Appreciation", "Appreciation"), ("Leveraged", "Leveraged")]
SOCIOCULTURAL_LOCATIONS = [("Religion", "Religion"), ("Disability", "Disability"), ("Culture", "Culture"),
                           ("Gender", "Gender"),
                           ("Race", "Race"), ("Class", "Class"), ("LGBQ+", "LGBQ+")]


class AbstractUser(models.Model):

    def __str__(self):
        return str.format("{} {} ({})", self.first_name, self.last_name, self.email)

    email = EmailField(unique=True)
    first_name = CharField(max_length=50)
    last_name = CharField(max_length=50)
    phone = CharField(max_length=20, help_text='Please enter valid US phone number')

    class Meta:
        abstract = True


class UnverifiedUser(AbstractUser):
    """
    This model will store user's information until their email is confirmed.
    Email is not unique for two reasons:
    - Someone other than the user tries to sign up with the user's email, but the user deletes the verification email
    since he/she didn't try registering.
    - The user registers, but forgets to verify the email or accidentally deletes it.
    In both cases, there should be no user with email already exists error on a subsequent tries.
    """
    email = EmailField()

    def create_user(self):
        if User.objects.filter(email=self.email):
            raise ValidationError(message=_(USER_ALREADY_EXISTS_MESSAGE), code='invalid')
        user = User()
        for name, value in self.__dict__.items():
            user.__setattr__(name, value)
        user.save()
        return user


class User(AbstractUser):
    can_retake = BooleanField(default=False)  # Set by the admin

    def disable_retake(self):
        self.can_retake = False
        self.save(update_fields=['can_retake'])

    def delete_unverified_users_with_same_email(self):
        unverified_users_with_user_email = UnverifiedUser.objects.filter(email=self.email)
        for unverified_user in unverified_users_with_user_email:
            unverified_user.delete()


class Admin(models.Model):
    user = OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    permission1 = BooleanField(default=False)
    permissionx = BooleanField(default=False)


class Consultant(AuthUser):
    class Meta:
        verbose_name = _('consultant')
        verbose_name_plural = _('consultants')

    def __str__(self):
        return str.format("{} {} ({})", self.first_name, self.last_name, self.email)

class ViewOnlyAdmin(AuthUser):
    class Meta:
        verbose_name = ('View Only Admin')
        verbose_name_plural = _('View Only Admins')


class AccessCode(models.Model):  # TODO (nn3un): find better name
    def __str__(self):
        uses_left = str(self.uses_left)
        if self.uses_left == -1:
            uses_left = 'Unlimited'
        if self.name:
            return '%s - Uses Left: %s' % (self.name, uses_left)
        return 'Uses Left: %s' % uses_left

    name = CharField(max_length=50, null=True, blank=True,
                     help_text='Nickname for identification purposes.')  # Something to identify it with
    code = CharField(max_length=12, unique=True)  # TODO: Ask if this is good enough.
    uses_left = IntegerField(default=1, help_text='Enter -1 for unlimited use')


class Assessment(models.Model):
    # ACCESS_TYPES = [(ACCESS_TYPE_FREE, 'Free'), (ACCESS_TYPE_PAID, 'Paid'), (ACCESS_TYPE_INST, 'Institution')]
    ACCESS_TYPES = [(ACCESS_TYPE_PAID, 'Paid'), (ACCESS_TYPE_INST, 'Institution')]
    user = ForeignKey(User, on_delete=models.SET_NULL, primary_key=False, null=True,
                      blank=True)  # many assessments to one user
    access_type = CharField(max_length=4, choices=ACCESS_TYPES, default='Paid')
    email = EmailField()
    date_started = DateField(default=timezone.now)
    last_question = IntegerField(default=0, verbose_name='Last Statement')
    PDF = models.FileField(upload_to='pdfs/', null=True, blank=True, storage=assessment_pdf_storage())
    consultants = models.ManyToManyField(Consultant, blank=True)


class Demographic(models.Model):
    age = CharField(choices=DC.AGE_CHOICES, max_length=255, verbose_name="Age")
    religion = CharField(choices=DC.RELIGION_CHOICES, max_length=255, verbose_name="Religion")
    area = CharField(choices=DC.AREA_CHOICES, max_length=255, verbose_name="Area (suburb/rural etc.)")
    disability = CharField(choices=DC.DISABILITY_CHOICES, max_length=255, verbose_name="Disability")
    # how you grew up
    socioeconomic = CharField(choices=DC.ECONOMIC_CHOICES, max_length=255, verbose_name="Current socioeconomic status")
    # current socioeconomic
    status = CharField(choices=DC.ECONOMIC_CHOICES, max_length=255, verbose_name="Socioeconomic Status growing up")
    employment = CharField(choices=DC.EMPLOYMENT_CHOICES, max_length=255, verbose_name="Employment Status")
    education = CharField(choices=DC.EDUCATION_CHOICES, max_length=255, verbose_name="Highest degree of education")
    marital = CharField(choices=DC.MARITAL_CHOICES, max_length=255, verbose_name="Relational/Marital Status")
    race_or_culture = CharField(choices=DC.RACE_CULTURE_CHOICES, max_length=255,
                                verbose_name="Racial/Cultural Heritage")
    perception = CharField(choices=DC.PERCEPTION_CHOICES, max_length=255, verbose_name="Race (as perceived by others)")
    sexual_orientation = CharField(choices=DC.SEXUAL_ORIENTATION_CHOICES, max_length=255,
                                   verbose_name="Sexual Orientation")  # (LGBTQ)
    gender = CharField(choices=DC.GENDER_CHOICES, max_length=255, verbose_name="Gender (self-identification)")
    gender_perception = CharField(choices=DC.GENDER_PERCEPTION_CHOICES, max_length=255,
                                  verbose_name="Gender (as perceived by others)")
    country_of_birth = CharField(choices=DC.COB_CHOICES, max_length=255, verbose_name="Country of birth")
    country_of_birth_state = CharField(choices=DC.STATE_CHOICES, max_length=255,
                                       verbose_name="State of Birth (if US born)")
    clocation = CharField(choices=DC.COB_CHOICES, max_length=255, verbose_name="Current country of residence")
    cstate = CharField(choices=DC.STATE_CHOICES, max_length=255, verbose_name="Current state of residence (if in US)")
    purpose = CharField(choices=DC.PURPOSE_CHOICES, max_length=255,
                        verbose_name="Feeling a sense of purpose (as a percentage of time)")
    safety = CharField(choices=DC.SAFETY_CHOICES, max_length=255, verbose_name="Complete this phrase: Safety comes...")
    assessment = OneToOneField(Assessment, on_delete=models.CASCADE)


class Score(models.Model):
    sensitivity_total = IntegerField(default=0)
    oneness_total = IntegerField(default=0)
    strength_total = IntegerField(default=0)
    appreciation_total = IntegerField(default=0)
    leveraged_total = IntegerField(default=0)
    assessment = OneToOneField(Assessment, on_delete=models.CASCADE)


class Gender_Score(models.Model):
    sensitivity = IntegerField(default=0)
    oneness = IntegerField(default=0)
    strength = IntegerField(default=0)
    appreciation = IntegerField(default=0)
    leveraged = IntegerField(default=0)
    score = OneToOneField(Score, on_delete=models.CASCADE, related_name="Gender_Score")


class Race_Score(models.Model):
    sensitivity = IntegerField(default=0)
    oneness = IntegerField(default=0)
    strength = IntegerField(default=0)
    appreciation = IntegerField(default=0)
    leveraged = IntegerField(default=0)
    score = OneToOneField(Score, on_delete=models.CASCADE, related_name="Race_Score")


class Religion_Score(models.Model):
    sensitivity = IntegerField(default=0)
    oneness = IntegerField(default=0)
    strength = IntegerField(default=0)
    appreciation = IntegerField(default=0)
    leveraged = IntegerField(default=0)
    score = OneToOneField(Score, on_delete=models.CASCADE, related_name="Religion_Score")


class Sexual_Orientation_Score(models.Model):
    sensitivity = IntegerField(default=0)
    oneness = IntegerField(default=0)
    strength = IntegerField(default=0)
    appreciation = IntegerField(default=0)
    leveraged = IntegerField(default=0)
    score = OneToOneField(Score, on_delete=models.CASCADE, related_name="Sexual_Orientation_Score")


class Disability_Score(models.Model):
    sensitivity = IntegerField(default=0)
    oneness = IntegerField(default=0)
    strength = IntegerField(default=0)
    appreciation = IntegerField(default=0)
    leveraged = IntegerField(default=0)
    score = OneToOneField(Score, on_delete=models.CASCADE, related_name="Disability_Score")


class Culture_Score(models.Model):
    sensitivity = IntegerField(default=0)
    oneness = IntegerField(default=0)
    strength = IntegerField(default=0)
    appreciation = IntegerField(default=0)
    leveraged = IntegerField(default=0)
    score = OneToOneField(Score, on_delete=models.CASCADE, related_name="Culture_Score")


class Class_Score(models.Model):
    sensitivity = IntegerField(default=0)
    oneness = IntegerField(default=0)
    strength = IntegerField(default=0)
    appreciation = IntegerField(default=0)
    leveraged = IntegerField(default=0)
    score = OneToOneField(Score, on_delete=models.CASCADE, related_name="Class_Score")


class Question(models.Model):
    number = IntegerField(default=0)  # (now unique)
    title = CharField(max_length=200, default='')  # (actual question)
    sociocultural_location = CharField(choices=SOCIOCULTURAL_LOCATIONS, max_length=50, default="test")
    primary_power_perspective = CharField(choices=POWER_PERSPECTIVES, max_length=50, default="test")
    secondary_power_perspective = CharField(choices=POWER_PERSPECTIVES, max_length=50, null=True,
                                            blank=True,
                                            help_text="If power perspective is independent of demographics, leave blank. "
                                                      "Otherwise, first set the related demographic field on which the power perspective will depend on. "
                                                      "Then set the single demographic choice for which power perspective should be set to "
                                                      "secondary power perspective instead of primary power perspective. "
                                                      "Then set the secondary power perspective")  # IMPORTANT: This is
    # the field that will be checked to see if the answer should depend on demographics. If it's None or '' it's not
    # a demographic dependent question. otherwise it is
    '''
    If secondary_power_perspective is set, then we need to look at demographics.
    secondary_demographic_type tells us which of the fields under Demographic will we have to look at.
    secondary_demographic_choice tells us within that Demographic.field, which choice, when set, would mean the user has
    the secondary_power_perspective instead of the primary_power_pespective
    Example:
    primary_power_perspective: 'Strength'
    secondary_power_perspective: 'Appreciation'
    secondary_demographic_type: 'gender'
    secondary_demographic_choice: 'Male'
    Scenario 1: assessment.demographic.gender != 'Male'
        response.power_perspective = question.primary_power_perspective = Strength
    Scenario 2: assessment.demographic.gender == 'Male'
        response.power_perspective = question.secondary_power_perspective = Appreciation
    '''

    secondary_demographic_type = CharField(max_length=255, null=True,
                                           blank=True, verbose_name='Related Demographic Field',
                                           help_text='Not required if secondary power perspective is not set')
    secondary_demographic_choice = CharField(null=True, blank=True, max_length=255,
                                             verbose_name='Field choice that should lead to secondary power perspective instead of primary power perspective being set',
                                             help_text='Not required if secondary power perspective is not set')

    class Meta:
        # change appearance from questions to statements in the UI
        verbose_name = "Statement"
        verbose_name_plural = "Statements"

    def __str__(self):
        return "Statement " + str(self.pk)

    def clean(self):
        # must perform checks to ensure secondary demographic choice is actually a valid choice under secondary demographic type
        if self.secondary_power_perspective is None:
            # This is not one of the demographic dependent questions, so no check required
            return
        if self.secondary_demographic_type is None or self.secondary_demographic_type == '' or \
                self.secondary_demographic_choice is None or self.secondary_demographic_choice == '':
            raise ValidationError(
                _('Related demographic field (secondary_demographic_type) and corresponding Field choice '
                  '(secondary_demographic_choice) must be filled out when Secondary power perspective is filled out'),
                code='empty',
            )

        demographic_fields = [field.name for field in Demographic._meta.fields]
        if self.secondary_demographic_type not in demographic_fields:
            raise ValidationError(
                _('Invalid value. secondary_demographic_type must be from : %(demographic_fields)s'),
                code='invalid',
                params={'demographic_fields': demographic_fields},
            )

        selected_demographic_field = Demographic._meta.get_field(self.secondary_demographic_type)
        valid_choices = [choice[0] for choice in selected_demographic_field.choices]
        if self.secondary_demographic_choice not in valid_choices:
            raise ValidationError(
                _('Invalid value. secondary_demographic_choice must be from : %(valid_choices)s'),
                code='invalid',
                params={'valid_choices': valid_choices},
            )


class Response(models.Model):
    assessment = ForeignKey(Assessment, on_delete=models.CASCADE, primary_key=False, null=True, blank=True)
    question_number = IntegerField(default=0,
                                   verbose_name='Statement Number')  # if we need to reference a response back to a question.
    RESPONSE_CHOICES = [("strongly agree", "Strongly agree"),
                        ("agree more than disagree", "Agree more than disagree"),
                        ("agree and disagree about the same", "Agree and disagree about the same"),
                        ("disagree more than agree", "Disagree more than agree"),
                        ("strongly disagree", "Strongly disagree")]
    response = CharField(choices=RESPONSE_CHOICES, max_length=50, default="test")  # stores the choice
    power_perspective = CharField(choices=POWER_PERSPECTIVES, max_length=50)
    sociocultural_location = CharField(choices=SOCIOCULTURAL_LOCATIONS, max_length=50)  # (race, religion, etc)


class CoreGroupuser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    accesscode = models.ForeignKey(AccessCode, on_delete=models.CASCADE)
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )


class Group(models.Model):
    accesscode = models.ForeignKey(AccessCode, on_delete=models.CASCADE)
    PDF = models.FileField(
        upload_to='group_pdfs/',
        null=True,
        blank=True,
        storage=assessment_pdf_storage(),
    )
