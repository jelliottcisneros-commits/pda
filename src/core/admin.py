import io
from django.contrib import admin, messages
from django.contrib.admin import AdminSite
from django.contrib.auth.admin import UserAdmin as AuthUserAdmin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.urls import reverse, path
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.safestring import mark_safe
from guardian.admin import GuardedModelAdmin
from guardian.shortcuts import *

from TheSum import settings
from TheSum.settings import env
from core.constants import COMPLETE_CONSULTANT_REGISTRATION_EMAIL_SUBJECT, \
    VIEW_ONLY_ADMIN_ACCOUNT_CREATED_MESSAGE, COMPLETE_VIEW_ONLY_ADMIN_REGISTRATION_EMAIL_SUBJECT
from core.constants import CONSULTANT_ACCOUNT_CREATED_MESSAGE
from core.forms import ConsultantCreationForm, QuestionAdminForm
from core.forms import ViewOnlyAdminCreationForm
from core.helpers import get_demographic_field_to_choices_map
from core.helpers import is_auth_user_consultant, send_email
from core.models import *


class CustomAdminSite(AdminSite):
    site_header = 'TheSum Assessment'

    def get_urls(self):
        from core.views import AssessmentDetailedView
        from core.views import CompleteConsultantRegistrationView
        from core.views import CompleteViewOnlyAdminRegistrationView
        from core.views import VerifyConsultantRegistrationCompletionLinkView
        from core.views import VerifyViewOnlyAdminRegistrationCompletionLinkView

        # source: https://adriennedomingus.com/blog/adding-custom-views-and-templates-to-django-admin
        urls = super().get_urls()

        custom_urls = [
            path('core/consultant/verify-registration-completion-link/<uidb64>/<token>/',
                 VerifyConsultantRegistrationCompletionLinkView.as_view(),
                 name='core_consultant_verify_registration_completion_link'),
            path('core/consultant/<int:consultant_pk>/complete-registration',
                 self.admin_view(CompleteConsultantRegistrationView.as_view()),
                 name='core_consultant_complete_registration'),
            path('core/view_only_admin/verify-registration-completion-link/<uidb64>/<token>/',
                 VerifyViewOnlyAdminRegistrationCompletionLinkView.as_view(),
                 name='core_view_only_admin_verify_registration_completion_link'),
            path('core/view_only_admin/<int:view_only_admin_pk>/complete-registration',
                 self.admin_view(CompleteViewOnlyAdminRegistrationView.as_view()),
                 name='core_view_only_admin_complete_registration'),
            path('core/assessment/<int:assessment_pk>/detailed_view',
                 self.admin_view(AssessmentDetailedView.as_view()),
                 name='core_assessment_detailed_view'),
        ]
        return custom_urls + urls


admin_site = CustomAdminSite()


# displays the registered users' first and last names, email, and phone number
@admin.register(User, site=admin_site)
class UserAdmin(admin.ModelAdmin):
    user_can_access_owned_objects_only = True

    def has_view_permission(self, request, obj=None):
        # overriding so that consultants can view Assessment
        if is_auth_user_consultant(request.user):
            if obj is None:
                # the user is viewing an index/list page, rather than a specific assessment object.
                return True
            return request.user.consultant.has_perm('core.view_user', obj) or request.user.consultant.has_perm(
                'core.change_user',
                obj)
        return super().has_view_permission(request, obj)

    def get_queryset(self, request):
        # Overriding to use django_guardian function
        # so that consultant can see assessments they have permission to view
        return get_objects_for_user(request.user, 'core.view_user')

    list_display = ['first_name', 'last_name', 'email', 'phone']
    ordering = ['last_name']
    search_fields = ('first_name', 'last_name', 'email', 'phone')


@admin.register(UnverifiedUser, site=admin_site)
class UnverifiedUserAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'phone']
    ordering = ['last_name']
    search_fields = ('first_name', 'last_name', 'email', 'phone')


# displays the question title, number, and type, and orders it numerically
@admin.register(Question, site=admin_site)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'number', 'sociocultural_location', 'title', 'primary_power_perspective',
                    'secondary_power_perspective', 'secondary_demographic_choice']
    ordering = ['number']
    search_fields = ('number', 'sociocultural_location', 'title')

    def get_form(self, request, obj=None, change=False, **kwargs):
        # overriding to allow custom admin form, with all the demographic field info, to be used
        kwargs['form'] = QuestionAdminForm
        return super().get_form(request, obj, change, **kwargs)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        # overriding to pass the context variable demographic_field_to_choices_map that will be required to dynamically
        # fill up the demographic choice options
        extra_context = extra_context or {}
        extra_context['demographic_field_to_choices_map'] = get_demographic_field_to_choices_map()
        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context,
        )



# displays the assessment object's attributes and provides a link to access
# demographics entered for that assessment
@admin.register(Assessment, site=admin_site)
class AssessmentAdmin(GuardedModelAdmin):
    user_can_access_owned_objects_only = True
    readonly_fields = ('detailed_view_link',)

    def has_view_permission(self, request, obj=None):
        # overriding so that consultants can view Assessment
        if is_auth_user_consultant(request.user):
            if obj is None:
                # the user is viewing an index/list page, rather than a specific assessment object.
                return True
            return request.user.consultant.has_perm('core.view_assessment', obj) or request.user.consultant.has_perm(
                'core.change_assessment',
                obj)
        return super().has_view_permission(request, obj)

    def get_queryset(self, request):
        # Overriding to use django_guardian function
        # so that consultant can see assessments they have permission to view
        return get_objects_for_user(request.user, 'core.view_assessment')

    list_display = ['__str__', 'user_link', 'access_type', 'email', 'demo_link', 'date_started',
                    'score_link', 'last_question']
    ordering = ['date_started']
    search_fields = ['user__first_name', 'user__last_name',
                     'access_type', 'email', 'last_question']
    actions = ['recalc_score_button', 'remake_pdf',]

    def demo_link(self, obj):
        try:
            return mark_safe('<a href="{}">{}</a>'.format(
                reverse("admin:core_demographic_change", args=(obj.demographic.pk,)),
                obj.demographic
            ))
        except ObjectDoesNotExist:
            return ''

    demo_link.short_description = 'demographic'

    def user_link(self, obj):
        if obj.user is None:
            return "User has been deleted"
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:core_user_change", args=(obj.user.pk,)),
            obj.user
        ))

    user_link.short_description = 'user'

    def score_link(self, obj):
        try:
            return mark_safe('<a href="{}">{}</a>'.format(
                reverse("admin:core_score_change", args=(obj.score.pk,)),
                obj.score
            ))
        except ObjectDoesNotExist:
            return ''

    score_link.short_description = 'Scores'

    def recalc_score_button(self, request, queryset):
        def cleanse(sub_score):
            sub_score.sensitivity = 0
            sub_score.strength = 0
            sub_score.oneness = 0
            sub_score.appreciation = 0
            sub_score.leveraged = 0
            sub_score.save()
        for obj in queryset:
            assessment = Assessment.objects.get(pk=obj.pk)
            try:
                score = Score.objects.get(assessment=assessment)
                score.strength_total = 0
                score.sensitivity_total = 0
                score.oneness_total = 0
                score.appreciation_total = 0
                score.leveraged_total = 0
            except Score.DoesNotExist:
                score = Score(assessment=assessment)
                score.save()
            try:
                gender_score = score.Gender_Score
            except:
                gender_score = Gender_Score()
            try:
                race_score = score.Race_Score
            except:
                race_score = Race_Score()
            try:
                religion_score = score.Religion_Score
            except:
                religion_score = Religion_Score()
            try:
                sexual_orientation_score = score.Sexual_Orientation_Score
            except:
                sexual_orientation_score = Sexual_Orientation_Score()
            try:
                disability_score = score.Disability_Score
            except:
                disability_score = Disability_Score()
            try:
                culture_score = score.Culture_Score
            except:
                culture_score = Culture_Score()
            try:
                class_score = score.Class_Score
            except:
                class_score = Class_Score()

            gender_score.score = score
            race_score.score = score
            religion_score.score = score
            sexual_orientation_score.score = score
            disability_score.score = score
            culture_score.score = score
            class_score.score = score
            cleanse(gender_score)
            cleanse(race_score)
            cleanse(sexual_orientation_score)
            cleanse(religion_score)
            cleanse(disability_score)
            cleanse(culture_score)
            cleanse(class_score)

            responses = Response.objects.filter(assessment=assessment)
            for response in responses:
                # points calculation based off response
                points = 0
                if response.response == "strongly agree":
                    points = 4
                elif response.response == "agree more than disagree":
                    points = 3
                elif response.response == "agree and disagree about the same":
                    points = 2
                elif response.response == "disagree more than agree":
                    points = 1
                elif response.response == "strongly disagree":
                    points = 0
                if response.sociocultural_location == "Gender":
                    if response.power_perspective == "Sensitivity":
                        score.sensitivity_total += points
                        gender_score.sensitivity += points
                    elif response.power_perspective == "Oneness":
                        score.oneness_total += points
                        gender_score.oneness += points
                    elif response.power_perspective == "Strength":
                        score.strength_total += points
                        gender_score.strength += points
                    elif response.power_perspective == "Appreciation":
                        score.appreciation_total += points
                        gender_score.appreciation += points
                    elif response.power_perspective == "Leveraged":
                        score.leveraged_total += points
                        gender_score.leveraged += points
                elif response.sociocultural_location == "Race":
                    if response.power_perspective == "Sensitivity":
                        score.sensitivity_total += points
                        race_score.sensitivity += points
                    elif response.power_perspective == "Oneness":
                        score.oneness_total += points
                        race_score.oneness += points
                    elif response.power_perspective == "Strength":
                        score.strength_total += points
                        race_score.strength += points
                    elif response.power_perspective == "Appreciation":
                        score.appreciation_total += points
                        race_score.appreciation += points
                    elif response.power_perspective == "Leveraged":
                        score.leveraged_total += points
                        race_score.leveraged += points
                elif response.sociocultural_location == "Religion":
                    if response.power_perspective == "Sensitivity":
                        score.sensitivity_total += points
                        religion_score.sensitivity += points
                    elif response.power_perspective == "Oneness":
                        score.oneness_total += points
                        religion_score.oneness += points
                    elif response.power_perspective == "Strength":
                        score.strength_total += points
                        religion_score.strength += points
                    elif response.power_perspective == "Appreciation":
                        score.appreciation_total += points
                        religion_score.appreciation += points
                    elif response.power_perspective == "Leveraged":
                        score.leveraged_total += points
                        religion_score.leveraged += points
                elif response.sociocultural_location == "LGBQ+":
                    if response.power_perspective == "Sensitivity":
                        score.sensitivity_total += points
                        sexual_orientation_score.sensitivity += points
                    elif response.power_perspective == "Oneness":
                        score.oneness_total += points
                        sexual_orientation_score.oneness += points
                    elif response.power_perspective == "Strength":
                        score.strength_total += points
                        sexual_orientation_score.strength += points
                    elif response.power_perspective == "Appreciation":
                        score.appreciation_total += points
                        sexual_orientation_score.appreciation += points
                    elif response.power_perspective == "Leveraged":
                        score.leveraged_total += points
                        sexual_orientation_score.leveraged += points
                elif response.sociocultural_location == "Disability":
                    if response.power_perspective == "Sensitivity":
                        score.sensitivity_total += points
                        disability_score.sensitivity += points
                    elif response.power_perspective == "Oneness":
                        score.oneness_total += points
                        disability_score.oneness += points
                    elif response.power_perspective == "Strength":
                        score.strength_total += points
                        disability_score.strength += points
                    elif response.power_perspective == "Appreciation":
                        score.appreciation_total += points
                        disability_score.appreciation += points
                    elif response.power_perspective == "Leveraged":
                        score.leveraged_total += points
                        disability_score.leveraged += points
                elif response.sociocultural_location == "Culture":
                    if response.power_perspective == "Sensitivity":
                        score.sensitivity_total += points
                        culture_score.sensitivity += points
                    elif response.power_perspective == "Oneness":
                        score.oneness_total += points
                        culture_score.oneness += points
                    elif response.power_perspective == "Strength":
                        score.strength_total += points
                        culture_score.strength += points
                    elif response.power_perspective == "Appreciation":
                        score.appreciation_total += points
                        culture_score.appreciation += points
                    elif response.power_perspective == "Leveraged":
                        score.leveraged_total += points
                        culture_score.leveraged += points
                elif response.sociocultural_location == "Class":
                    if response.power_perspective == "Sensitivity":
                        score.sensitivity_total += points
                        class_score.sensitivity += points
                    elif response.power_perspective == "Oneness":
                        score.oneness_total += points
                        class_score.oneness += points
                    elif response.power_perspective == "Strength":
                        score.strength_total += points
                        class_score.strength += points
                    elif response.power_perspective == "Appreciation":
                        score.appreciation_total += points
                        class_score.appreciation += points
                    elif response.power_perspective == "Leveraged":
                        score.leveraged_total += points
                        class_score.leveraged += points

            score.save()

            gender_score.score = score
            race_score.score = score
            religion_score.score = score
            sexual_orientation_score.score = score
            disability_score.score = score
            culture_score.score = score
            class_score.score = score

            gender_score.save()
            race_score.save()
            religion_score.save()
            sexual_orientation_score.save()
            disability_score.save()
            culture_score.save()
            class_score.save()
        self.message_user(request, 'Selected assessment(s) had score(s) regenerated')
    recalc_score_button.short_description = "Recalculate Selected Score(s)"


    def remake_pdf(self, request, queryset):
        from core.views import generate_pdf

        issue = False
        for obj in queryset:
            # when bad is True, there was an issue. WHen bad if False, there were no issues
            # an issue may be data needed to make PDF has been deleted
            bad = generate_pdf(obj.pk, True)
            if (bad == True):
                issue = True

        # send message to UI once everything is done
        if (issue):
            self.message_user(request, 'Some PDFs could not be regenerated as score data is missing! Please recalculate the scores for any assessments that still do not have any PDFs and try again. Other PDFs have been regenerated successfully.')
        else:
            self.message_user(request, 'Selected assessment(s) had PDF(s) regenerated successfully')
    remake_pdf.short_description = "Remake Selected PDF(s)"


    def detailed_view_link(self, obj):
        if obj is None or obj.pk is None:
            return ''
        return mark_safe('<a href="{}" rel="noopener noreferrer" target="_blank">{}</a>'.format(
            reverse("admin:core_assessment_detailed_view", args=(obj.pk,)),
            "Click here"
        ))

    detailed_view_link.short_description = "More Details"


# displays all data about access codes on one page
@admin.register(AccessCode, site=admin_site)
class AccessCodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'uses_left']
    ordering = ['name']
    search_fields = ('name', 'code', 'uses_left')


@admin.register(Response, site=admin_site)
class ResponseAdmin(admin.ModelAdmin):
    def user_link(self, obj):
        if obj.assessment.user is None:
            return "User has been deleted"
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:core_user_change", args=(obj.assessment.user.pk,)),
            obj.assessment.user
        ))

    user_link.allow_tags = True
    user_link.short_description = 'user'

    list_display = ['__str__', 'user_link', 'question_number', 'response',
                    'power_perspective', 'sociocultural_location']
    ordering = ['assessment', 'question_number']
    search_fields = ('assessment__id', 'response',
                     'power_perspective', 'sociocultural_location')


@admin.register(Demographic, site=admin_site)
class DemographicAdmin(admin.ModelAdmin):
    user_can_access_owned_objects_only = True

    def has_view_permission(self, request, obj=None):
        # overriding so that consultants can view Assessment
        if is_auth_user_consultant(request.user):
            if obj is None:
                # the user is viewing an index/list page, rather than a specific assessment object.
                return True
            return request.user.consultant.has_perm('core.view_demographic', obj) or request.user.consultant.has_perm(
                'core.change_demographic',
                obj)
        return super().has_view_permission(request, obj)

    def get_queryset(self, request):
        # Overriding to use django_guardian function
        # so that consultant can see assessments they have permission to view
        return get_objects_for_user(request.user, 'core.view_demographic')

    list_display = ['__str__', 'assessment_link', 'age', 'religion', 'area', 'disability', 'socioeconomic', 'status',
                    'employment', 'education',
                    'marital', 'race_or_culture', 'perception', 'sexual_orientation', 'gender', 'country_of_birth',
                    'country_of_birth_state', 'clocation', 'cstate', 'purpose', 'safety']
    search_fields = ['age', 'religion', 'area', 'disability', 'socioeconomic', 'status', 'employment', 'education',
                     'marital', 'race_or_culture', 'perception', 'sexual_orientation', 'gender', 'country_of_birth',
                     'country_of_birth_state', 'clocation', 'cstate', 'purpose', 'safety']

    def assessment_link(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:core_assessment_change", args=(obj.assessment.pk,)),
            obj.assessment
        ))

    assessment_link.short_description = 'assessment'


# displays the total scores from a user assessment
@admin.register(Score, site=admin_site)
class ScoreAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'assessment_link', 'sensitivity_total', 'oneness_total', 'strength_total',
                    'appreciation_total',
                    'leveraged_total']
    search_fields = ['assessment', 'sensitivity_total', 'oneness_total', 'strength_total',
                     'appreciation_total',
                     'leveraged_total']

    def assessment_link(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:core_assessment_change", args=(obj.assessment.pk,)),
            obj.assessment
        ))


@admin.register(Gender_Score, site=admin_site)
@admin.register(Race_Score, site=admin_site)
@admin.register(Religion_Score, site=admin_site)
@admin.register(Sexual_Orientation_Score, site=admin_site)
@admin.register(Disability_Score, site=admin_site)
@admin.register(Culture_Score, site=admin_site)
@admin.register(Class_Score, site=admin_site)
class SubScoreAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'score_link', 'sensitivity', 'oneness', 'strength', 'appreciation', 'leveraged']
    search_fields = ['score__pk', 'sensitivity', 'oneness', 'strength', 'appreciation', 'leveraged']
    ordering = ['score__pk']

    def score_link(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(
            reverse("admin:core_score_change", args=(obj.score.pk,)),
            obj.score
        ))


# displays the consultants and types of privileges they hold (currently unfinished)
@admin.register(Consultant, site=admin_site)
class ConsultantAdmin(AuthUserAdmin):
    # Overriding default UserAdmin, since it has a lot of functionality we don't need
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email',),
            # The admin only specifies the email, the other fields are either filled out, or left empty
        }),
    )

    def response_add(self, request, obj, post_url_continue=None):
        # overriding to send complete registration email to consultant after add is successful
        current_site = get_current_site(request)
        site_name = current_site.name
        domain = current_site.domain
        context = {
            'domain': domain,
            'site_name': site_name,
            'uid': urlsafe_base64_encode(force_bytes(obj.pk)),
            'token': default_token_generator.make_token(obj),
            'protocol': settings.PROTOCOL,
            'email_subject': COMPLETE_CONSULTANT_REGISTRATION_EMAIL_SUBJECT
        }
        send_email(subject_template_name='core/email_subject.html',
                                      email_template_name='core/consultant_account_creation_email.html',
                                      context=context,
                                      from_email=settings.FROM_EMAIL,
                                      to_email=obj.email,
                                      )
        messages.success(request, CONSULTANT_ACCOUNT_CREATED_MESSAGE)
        return HttpResponseRedirect(reverse('admin:core_consultant_changelist'))

    add_form_template = None  # overriding to show default instead of auth/user/add_form.html
    add_form = ConsultantCreationForm  # overriding to show a form with only the email field

    list_display = ['__str__', 'assigned_users']

    def assigned_users(self, obj):
        assessments = get_objects_for_user(obj.consultant, 'core.view_assessment')
        users = {assessment.user for assessment in assessments}
        return list(users)


@admin.register(ViewOnlyAdmin, site=admin_site)
class ViewOnlyAdminAdmin(AuthUserAdmin):
    ViewOnlyAdmin._meta.model_name = 'view_only_admin'
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email',),
        }),
    )

    def response_add(self, request, obj, post_url_continue=None):
        # overriding to send complete registration email to consultant after add is successful
        current_site = get_current_site(request)
        site_name = current_site.name
        domain = current_site.domain
        context = {
            'domain': domain,
            'site_name': site_name,
            'uid': urlsafe_base64_encode(force_bytes(obj.pk)),
            'token': default_token_generator.make_token(obj),
            'protocol': settings.PROTOCOL,
            'email_subject': COMPLETE_VIEW_ONLY_ADMIN_REGISTRATION_EMAIL_SUBJECT
        }
        send_email(subject_template_name='core/email_subject.html',
                                      email_template_name='core/view_only_admin_creation_email.html',
                                      context=context,
                                      from_email=settings.FROM_EMAIL,
                                      to_email=obj.email,
                                      )
        messages.success(request, VIEW_ONLY_ADMIN_ACCOUNT_CREATED_MESSAGE)
        return HttpResponseRedirect(reverse('admin:core_view_only_admin_changelist'))

    add_form_template = None  # overriding to show default instead of auth/user/add_form.html
    add_form = ViewOnlyAdminCreationForm  # overriding to show a form with only the email field

    list_display = ['__str__']
