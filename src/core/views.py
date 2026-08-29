import io
import logging
from collections import OrderedDict
from datetime import datetime

from django.conf import settings
from django.conf.global_settings import AUTHENTICATION_BACKENDS
from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.auth import login
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, \
    PasswordResetCompleteView
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.http import FileResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_decode
from django.utils.safestring import mark_safe
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.defaults import server_error, page_not_found
from django.views.generic import FormView, TemplateView
from django.views.generic.base import ContextMixin
from guardian.mixins import PermissionRequiredMixin
from paypal.standard.forms import PayPalPaymentsForm
from paypal.standard.pdt.views import process_pdt

from TheSum.settings import PAYPAL_RECIEVER_EMAIL
from .constants import *
from .decorators import assessment_completion_required, incomplete_assessment_required, require_session_key_absence
from .forms import CompleteViewOnlyAdminRegistrationForm
from .forms import DemographicForm, ResponseForm, UnverifiedUserForm, UserForm, CompleteConsultantRegistrationForm
from .helpers import *
from .models import *
from .payments import build_absolute_url, is_valid_pdt_payment
from .tokens import token_generator_for_abstract_user
from .utilities import group_result


def pdf_static_path(path):
    found_path = finders.find(path)
    return found_path or path


class ContinueView(View):
    session_key_to_redirect_url_upon_session_key_absence_map = OrderedDict(dict(
        user_id='core:index',
        access_type='core:choose_access_type',
        assessment_id='core:create_assessment',
        last_question='core:demographics'
    ))

    url_param_keys = {'user_id', 'assessment_id', 'number'}

    def get(self, request, *_kwargs):
        kwargs = dict()
        session = request.session
        for session_key, absence_redirect_url in self.session_key_to_redirect_url_upon_session_key_absence_map.items():
            if session_key not in session.keys():
                return HttpResponseRedirect(reverse(absence_redirect_url, kwargs=kwargs))
            if session_key in self.url_param_keys:
                # only update the url kwarg if it is a url_param_key and skip for things like access_type, last_question
                kwargs.update({session_key: session[session_key]})
        # coming this far means last_question is in session
        kwargs.update(dict(number=session['last_question'] + 1))
        return HttpResponseRedirect(reverse('core:question', kwargs=kwargs))


@method_decorator(require_session_key_absence('user_id'), name='dispatch')
class IndexView(TemplateView):
    template_name = 'core/landingpage.html'


@method_decorator(require_session_key_absence('user_id'), name='dispatch')
class RegisterView(FormView):
    form_class = UnverifiedUserForm
    template_name = 'core/register.html'
    success_url = reverse_lazy('core:verify_email_instructions')
    email_template_name = 'core/verification_email_plain.html'
    html_email_template_name = 'core/verification_email.html'
    email_subject = VERIFICATION_EMAIL_SUBJECT

    def form_valid(self, form):
        if User.objects.filter(email=form.cleaned_data['email']):
            return redirect_with_error_message(request=self.request, error_message=USER_ALREADY_EXISTS_MESSAGE,
                                               redirect_url='core:register')
        unverified_user = form.save()
        domain = get_current_site(self.request).domain
        email_verification_token_to_abstract_user(domain=domain,
                                                  abstract_user=unverified_user,
                                                  email_subject=self.email_subject,
                                                  email_template_name=self.email_template_name,
                                                  html_email_template_name=self.html_email_template_name)
        return super().form_valid(form)


@method_decorator(require_session_key_absence('user_id'), name='dispatch')  # user_id must not be set for this to work
class EmailVerificationView(View):
    def get_abstract_user(self, abstract_user_model: callable):
        try:
            uid = urlsafe_base64_decode(self.kwargs['uidb64']).decode()
            return abstract_user_model.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, abstract_user_model.DoesNotExist, ValidationError):
            return None

    def get_unverified_user(self):
        return self.get_abstract_user(UnverifiedUser)

    def is_link_valid_for_abstract_user(self, abstract_user):
        if abstract_user is not None:
            return token_generator_for_abstract_user.check_token(abstract_user, self.kwargs['token'])
        return False

    def get(self, request, **_kwargs):
        unverified_user = self.get_unverified_user()
        if self.is_link_valid_for_abstract_user(unverified_user):
            try:
                user = unverified_user.create_user()
                user.delete_unverified_users_with_same_email()  # We don't want the other unverified users to be able
                # to verify anymore. So deleting them.
                setup_session_for_user(request, user)
                return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=dict(user_id=user.pk)))
            except ValidationError as error:
                # Most likely user with email already exists, so redirecting back to register page
                unverified_user.delete()
                return redirect_with_error_message(request=request, error_message=error.message,
                                                   redirect_url='core:register')
        else:
            return handle_invalid_link_error(request)


@method_decorator(require_session_key_absence('user_id'), name='dispatch')
class RetakeView(FormView):
    form_class = UserForm
    template_name = 'core/retake.html'
    success_url = reverse_lazy('core:verify_email_instructions')
    email_template_name = 'core/re_verification_email_plain.html'
    html_email_template_name = 'core/re_verification_email.html'
    email_subject = RE_VERIFICATION_EMAIL_SUBJECT

    def form_valid(self, form):
        try:
            user = User.objects.get(email=form.cleaned_data['email'])
        except User.DoesNotExist:
            # If the email does not exist in the database they should register
            return redirect_with_error_message(request=self.request, error_message=USER_WITH_EMAIL_DOES_NOT_EXIST,
                                               redirect_url='core:register')
        if user.can_retake:
            domain = get_current_site(self.request).domain
            email_verification_token_to_abstract_user(domain=domain, abstract_user=user,
                                                      email_subject=self.email_subject,
                                                      email_template_name=self.email_template_name,
                                                      html_email_template_name=self.html_email_template_name)
            return super().form_valid(form)
        else:
            return redirect_with_error_message(request=self.request, error_message=USER_CANNOT_RETAKE_MESSAGE,
                                               redirect_url='core:retake')


@method_decorator(require_session_key_absence('user_id'), name='dispatch')  # user_id must not be set for this to work
class EmailReVerificationView(EmailVerificationView):
    def get_user(self):
        return self.get_abstract_user(abstract_user_model=User)

    def get(self, request, **_kwargs):
        user = self.get_user()
        if self.is_link_valid_for_abstract_user(user):
            user.disable_retake()  # They shouldn't be able to retake again.
            setup_session_for_user(request=request, user=user)
            return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=dict(user_id=user.pk)))
        else:
            return handle_invalid_link_error(request)


@require_http_methods(["POST"])
@require_session_key_absence('access_type')
def verify_access_code(request, user_id):
    if 'access_code' not in request.POST:
        return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=dict(user_id=user_id)))
    access_codes = AccessCode.objects.filter(code=request.POST['access_code'])
    if len(access_codes) > 0:
        access_code = access_codes[0]
        if access_code.uses_left == -1 or access_code.uses_left > 0:
            request.session['access_type'] = ACCESS_TYPE_INST

            accesscode_text = access_code.code
            find_exclamation_mark = accesscode_text.startswith("!")

            if find_exclamation_mark:
                accesscode_id = access_code.id
                group_users = CoreGroupuser.objects.filter(user=user_id)

                if len(group_users) > 0:
                    group_users.update(
                        accesscode=AccessCode.objects.get(pk=accesscode_id),
                        assessment=None
                    )
                    request.session['accesscode_id'] = accesscode_id
                else:
                    blank_group_users = CoreGroupuser()
                    blank_group_users.user = User.objects.get(pk=user_id)
                    blank_group_users.accesscode = AccessCode.objects.get(pk=accesscode_id)
                    blank_group_users.save()
                    request.session['accesscode_id'] = accesscode_id

            else:
                group_users = CoreGroupuser.objects.filter(user=user_id)
                if len(group_users) > 0:
                    group_users.delete()

            if access_code.uses_left != -1:
                access_code.uses_left -= 1
                access_code.save(update_fields=['uses_left'])

            return HttpResponseRedirect(reverse('core:create_assessment', kwargs=dict(user_id=user_id)))
        else:
            messages.error(request, ACCESS_CODE_NO_USE_LEFT_MESSAGE)
    else:
        messages.error(request, INVALID_ACCESS_CODE_MESSAGE)
    return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=dict(user_id=user_id)))


@require_session_key_absence('access_type')
def choose_access_type(request, user_id):
    # setup PayPal "Buy Now" button
    payment_kwargs = dict(user_id=user_id)
    paypal_dict = {
        "business": PAYPAL_RECIEVER_EMAIL,
        "amount": "150.00",
        "item_name": "Power of Difference Assessment and Consulation",
        'return_url': build_absolute_url(request, 'core:payment', **payment_kwargs),
        'cancel_return': build_absolute_url(request, 'core:payment_cancelled', **payment_kwargs),
        "custom": user_id,
    }
    paypal_dict_100 = {
        "business": PAYPAL_RECIEVER_EMAIL,
        "amount": "100.00",
        "item_name": "Power of Difference Assessment and Consulation",
        'return_url': build_absolute_url(request, 'core:payment', **payment_kwargs),
        'cancel_return': build_absolute_url(request, 'core:payment_cancelled', **payment_kwargs),
        "custom": user_id,
    }
    paypal_dict_50 = {
        "business": PAYPAL_RECIEVER_EMAIL,
        "amount": "50.00",
        "item_name": "Power of Difference Assessment and Consulation",
        'return_url': build_absolute_url(request, 'core:payment', **payment_kwargs),
        'cancel_return': build_absolute_url(request, 'core:payment_cancelled', **payment_kwargs),
        "custom": user_id,
    }
    form = PayPalPaymentsForm(initial=paypal_dict)
    form100 = PayPalPaymentsForm(initial=paypal_dict_100)
    form50 = PayPalPaymentsForm(initial=paypal_dict_50)
    context = {"user_id": user_id, "form": form, "form100": form100, "form50": form50}
    return render(request, 'core/choose_access_type.html', context)


# redirects here after payment on PayPal
@require_session_key_absence('access_type')
@csrf_exempt
def payment(request, user_id):
    pdt_obj, failed = process_pdt(request)
    kwargs = dict(user_id=user_id)
    if not failed and is_valid_pdt_payment(pdt_obj, expected_user_id=user_id):
        messages.success(request, "Payment Received")
        request.session['access_type'] = ACCESS_TYPE_PAID
        return HttpResponseRedirect(reverse('core:create_assessment', kwargs=kwargs))

    messages.error(request, INVALID_PAYMENT_MESSAGE)
    return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=kwargs))


# if the payment is cancelled redirect back to choose access type
@require_session_key_absence('access_type')
@csrf_exempt
def payment_cancelled(request, user_id):
    kwargs = dict(user_id=user_id)
    messages.error(request, CANCELLED_PAYMENT_MESSAGE)
    return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=kwargs))


# @require_session_key_absence('access_type')
# def take_free_version(request, user_id):  # TODO (nn3un): find better name
#     request.session['access_type'] = ACCESS_TYPE_FREE
#     return HttpResponseRedirect(reverse('core:create_assessment', kwargs=dict(user_id=user_id)))


@require_session_key_absence('assessment_id')
def create_assessment(request, user_id):
    if 'access_type' not in request.session:
        return HttpResponseRedirect(
            reverse('core:choose_access_type', kwargs=dict(user_id=user_id)))
    try:
        user = User.objects.get(pk=user_id)
        email = user.email
        access_type = request.session['access_type']
        assessment = Assessment(user=user, email=email, access_type=access_type)
        assessment.save()
        if 'last_question' in request.session:
            del request.session['last_question']
        request.session['assessment_id'] = assessment.pk
        if 'accesscode_id' in request.session:
            accesscode_id = request.session['accesscode_id']
            # save assessment id to group user
            group_users = CoreGroupuser.objects.filter(user=user_id, accesscode=accesscode_id)
            group_users.update(assessment=Assessment.objects.get(pk=assessment.pk))
        # setup the timer here
        dt = str(datetime.now())
        # we have to break apart the datetime as it is not JSON serializable
        request.session['year'] = int(dt[0:4])
        request.session['month'] = int(dt[5:7])
        request.session['day'] = int(dt[8:10])
        request.session['hour'] = int(dt[11:13])
        request.session['minute'] = int(dt[14:16])
        request.session['second'] = int(dt[17:19])
        request.session.set_expiry(86400)
        kwargs = dict(user_id=user_id, assessment_id=assessment.pk)
        return HttpResponseRedirect(reverse('core:demographics', kwargs=kwargs))
    except User.DoesNotExist:
        request.session.flush()
        return HttpResponseRedirect(reverse('core:register'))


@require_session_key_absence('last_question')
def demographics(request, user_id, assessment_id):
    form = DemographicForm()
    context = dict(user_id=user_id, assessment_id=assessment_id, form=form)
    return render(request, 'core/demographics.html', context)


@require_session_key_absence('last_question')
@require_http_methods(["POST"])
def demographics_submit(request, user_id, assessment_id):
    try:
        assessment = Assessment.objects.get(pk=assessment_id)
    except Assessment.DoesNotExist:
        if 'access_type' in request.session:
            del request.session['access_type']
        if 'assessment_id' in request.session:
            del request.session['assessment_id']
        return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=dict(user_id=user_id)))
    demographic = Demographic(assessment=assessment)
    # check for the form and validate it
    form = DemographicForm(request.POST, instance=demographic)
    if form.is_valid():
        form.save()
        last_question = 0
        request.session['last_question'] = last_question
        kwargs = dict(user_id=user_id, assessment_id=assessment_id)
        return HttpResponseRedirect(reverse('core:instructions', kwargs=kwargs))
    messages.error(request, DEMOGRAPHICS_FORM_ERROR_MESSAGE)
    context = dict(user_id=user_id, assessment_id=assessment_id)
    context.update({'form': form})
    return render(request, 'core/demographics.html', context)


@incomplete_assessment_required
def question(request, user_id, assessment_id, number):
    last_question = request.session['last_question']
    if number != last_question + 1:
        kwargs = dict(user_id=user_id, assessment_id=assessment_id, number=last_question + 1)
        return HttpResponseRedirect(reverse('core:question', kwargs=kwargs))
    question = Question.objects.get(number=number)
    next_question = Question.objects.filter(number=number + 1)
    is_last_question = False
    if not next_question:
        is_last_question = True
    context = dict(user_id=user_id,
                   assessment_id=assessment_id,
                   question=question,
                   is_last_question=is_last_question,
                   number=number,
                   form=ResponseForm())
    return render(request, 'core/question.html', context)


@require_http_methods(["POST"])
@incomplete_assessment_required
def question_submit(request, user_id, assessment_id, number):
    last_question = request.session['last_question']
    if number != last_question + 1:
        kwargs = dict(user_id=user_id, assessment_id=assessment_id, number=last_question + 1)
        return HttpResponseRedirect(reverse('core:question', kwargs=kwargs))
    try:
        assessment = Assessment.objects.get(pk=assessment_id)
    except Assessment.DoesNotExist:
        if 'access_type' in request.session:
            del request.session['access_type']
        if 'assessment_id' in request.session:
            del request.session['assessment_id']
        if 'last_question' in request.session:
            del request.session['last_question']
        return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=dict(user_id=user_id)))
    question = Question.objects.get(number=number)
    form = ResponseForm(request.POST)
    if form.is_valid():
        response = Response(response=form.cleaned_data['response'],
                            question_number=question.number,
                            sociocultural_location=question.sociocultural_location,
                            assessment=assessment,
                            power_perspective=question.primary_power_perspective
                            )
        if question.secondary_power_perspective is not None and question.secondary_power_perspective != '':
            '''
            Response power perspective depends on demographic choice. (See models.py for explanation)
            '''
            assessment_demographic_choice = assessment.demographic.__dict__.get(question.secondary_demographic_type)
            if question.secondary_demographic_choice == assessment_demographic_choice:
                response.power_perspective = question.secondary_power_perspective
        response.save()
        request.session['last_question'] = number

        # determining the redirect whether to next question or score page
        # number = int(request.POST.get("question_number","").strip())
        next_question = Question.objects.filter(number=number + 1)
        if next_question:
            kwargs = dict(user_id=user_id, assessment_id=assessment_id, number=number + 1)
            return HttpResponseRedirect(reverse('core:question', kwargs=kwargs))
        kwargs = dict(user_id=user_id, assessment_id=assessment_id)
        return HttpResponseRedirect(reverse("core:score", kwargs=kwargs))

    messages.error(request, INCORRECT_RESPONSE_MESSAGE)
    kwargs = dict(user_id=user_id, assessment_id=assessment_id, number=number)
    return HttpResponseRedirect(reverse('core:question', kwargs=kwargs))


@incomplete_assessment_required
def instructions(request, user_id, assessment_id):
    last_question = request.session['last_question']
    if last_question == 0:
        kwargs = dict(user_id=user_id, assessment_id=assessment_id)
        return render(request, 'core/instructions.html', kwargs)
    kwargs = dict(user_id=user_id, assessment_id=assessment_id, number=last_question + 1)
    return HttpResponseRedirect(reverse("core:question", kwargs=kwargs))


@assessment_completion_required
def finished(request, user_id, assessment_id):
    request.session['is_finished'] = True
    context = {'user_id': user_id, 'assessment_id': assessment_id,
               'access_type': request.session.get('access_type', ACCESS_TYPE_FREE),
               'scheduling_url': settings.SCHEDULING_URL}

    if 'accesscode_id' in request.session:
        return render(request, 'core/finished_group.html', context)

    return render(request, 'core/finished.html', context)


# works to make the PDF and email in user (does not send email in admin site)
# called_from_admin_site is True when in admin site, False when being done through taking the assessment
def generate_pdf(item, called_from_admin_site):
    from reportlab.graphics import renderPDF
    from reportlab.graphics.charts.barcharts import HorizontalBarChart
    from reportlab.graphics.charts.legends import Legend
    from reportlab.graphics.charts.spider import SpiderChart
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas  # for pdf report generation
    from reportlab.platypus import Table, TableStyle, Paragraph


    #get the assessment
    assessment = Assessment.objects.get(pk = item)

    if (called_from_admin_site == False):
        # get score and subscores from assessment
        score = assessment.score
        religion_score = score.Religion_Score
        disability_score = score.Disability_Score
        culture_score = score.Culture_Score
        gender_score = score.Gender_Score
        race_score = score.Race_Score
        class_score = score.Class_Score
        sexual_orientation_score = score.Sexual_Orientation_Score
    else:
        try: 
            score = assessment.score
            religion_score = score.Religion_Score
            disability_score = score.Disability_Score
            culture_score = score.Culture_Score
            gender_score = score.Gender_Score
            race_score = score.Race_Score
            class_score = score.Class_Score
            sexual_orientation_score = score.Sexual_Orientation_Score
        except:
            # this lets us know some data was deleted so we cannot remake the PDF in admin site
            return True

    # buffer is basically a bytestream treated like a file
    buffer = io.BytesIO()
    # canvas is what reportlab draws on
    p = canvas.Canvas(buffer)

    # PDF generation starts here:

    # page 1
    # switch to landscape
    p.setPageSize(landscape(letter))
    # Image: logo on top left corner
    p.drawInlineImage(pdf_static_path("core/img/pda_pdf_header.jpg"), .25 * inch, 6 * inch, 2.25 * inch, 2.25 * inch)
    p.setFont("Helvetica-Bold", 28)
    p.drawString(3.5 * inch, 8 * inch, "The Power of Difference Model (PDM)")
    p.setFont("Helvetica", 12)
    p.drawString(4 * inch, 7.75 * inch, "J Elliott Cisneros MEd, Carla Sherrell, EdD ~ 2016 ALL RIGHTS RESERVED (c)")
    p.setFont("Helvetica", 14)
    pstyle=ParagraphStyle('default')

    # sets styles for the leading paragraph on this page
    header_par = ParagraphStyle(
        'header_par',
        parent=pstyle,
        fontSize=16,
        alignment=TA_CENTER,
        leading=17
    )

    par = Paragraph("""<i>The PDM describes three primary perspectives or patterns of thought, behavior, and feeling--related to race, religion, dis/ability, 
        sexual orientation, gender, socio-economic class, and culture.  These patterns can be thought of, in part, as strategies for managing fear and creating safety... 
        often learned in childhood.</i>""", header_par)
    par.wrapOn(p, 7.5 * inch, 3 * inch)
    par.drawOn(p, 3 * inch, 6.5 * inch)

    par = Paragraph("<b><u><i>PERSPECTIVES/PATTERNS</i></u></b>", header_par)
    par.wrapOn(p, 3 * inch, .5 * inch)
    par.drawOn(p, 2.75 * inch, 6 * inch)

    # sets styles for perspective paragraphs
    perspective_par = ParagraphStyle(
        'perspective_par',
        parent=header_par,
        fontSize=14,
        alignment=TA_LEFT
    )

    par = Paragraph("""<b>Sensitivity:</b> I value intelligence, open mindedness, understanding, and 
        difference.  I don't wan't to offend so I can get stuck or confused around
        differences.  I can be patronizing as I try to "get others to get it".<br />
        <i><u>Archetype: Magician</u></i> &nbsp;&nbsp;&nbsp; <i><u>Politics: Tend Liberal</u></i> &nbsp;&nbsp;&nbsp; <i><u>Learning Edge: Strength</u></i>""",
                    perspective_par)
    par.wrapOn(p, 6.75 * inch, 2 * inch)
    par.drawOn(p, .25 * inch, 5 * inch)

    par = Paragraph("""<b>Oneness:</b> I value compassion and connection.  I devalue difference and 
        can over-value sameness.  I can fail to impact others as I intend and I 
        tend to avoid conflict.  "Why can't we all just get along."<br />
        <i><u>Archetype: Lover</u></i> &nbsp;&nbsp;&nbsp;&nbsp; <i><u>Politics: Moderate</u></i> &nbsp;&nbsp;&nbsp;&nbsp <i><u>Learning Edge: Sensitivity</u></i>""",
                    perspective_par)
    par.wrapOn(p, 6.75 * inch, 2 * inch)
    par.drawOn(p, .25 * inch, 3.875 * inch)

    par = Paragraph("""<b>Strength:</b> I value loyalty, bravery, protection, self-sacrifice, and winning. 
        I evaluate differences, seek dominance, and can create an "enemy."<br />
        <i><u>Archetype: Warrior</u></i> &nbsp;&nbsp; <i><u>Politics: Tend Conservative</u></i> &nbsp;&nbsp; <i><u>Learning Edge: Oneness</u></i>""",
                    perspective_par)
    par.wrapOn(p, 6.75 * inch, 2 * inch)
    par.drawOn(p, .25 * inch, 3 * inch)

    # leveraging section
    header_par.alignment = TA_LEFT
    par = Paragraph("<b><u><i>LEVERAGING</i></u></b>", header_par)
    par.wrapOn(p, 1.75 * inch, .5 * inch)
    par.drawOn(p, .25 * inch, 2.5 * inch)

    par = Paragraph("""<i>(leveraging is less of a perspective by itself and more something we do or don't do)</i><br /><br />
        We integrate and leverage assets from ALL of the perspectives as we feel called.<br />
        We impact others (generally) in alignment with our intentions across difference.<br />
        We call others to increased internal integration without blame and shame.<br />
        We live from solidarity across our differences... refusing silence and violence.<br />
        We experience greater effectiveness across difference, mission clarity, empowerment, and fulfillment.<br />
        We experience less rising and falling on external conditions--greater internal stability/immovable sense of peace.<br />
        <i>* A fourth less significant pattern we call "appreciation" which involves an appreciation of, and typically an over-romanticising or appropriation of a particular group to which a person does not belong.</i>""",
                    perspective_par)
    par.wrapOn(p, 10.5 * inch, 3 * inch)
    par.drawOn(p, .25 * inch, .125 * inch)

    # Image: scarecrow/tin man/lion on right of page 2 and arrows
    p.drawInlineImage(pdf_static_path("core/img/STL.jpg"), 8 * inch, 1.5 * inch, 3 * inch, 5 * inch)
    p.drawImage(pdf_static_path("core/img/arrow_1.jpg"), 6.5 * inch, 5.5 * inch, 1.5 * inch, .75 * inch)
    p.drawImage(pdf_static_path("core/img/arrow_2.jpg"), 7.15 * inch, 4 * inch, 1.5 * inch, .75 * inch)
    p.drawImage(pdf_static_path("core/img/arrow_3.jpg"), 7 * inch, 3 * inch, 1.5 * inch, .75 * inch)

    p.showPage()

    # page 2 - statements and answers
    p.translate(.5 * inch, .5 * inch)

    # title
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(4.5 * inch, 7.5 * inch, "The Power of Difference Assessment")
    p.setFont("Helvetica", 14)
    p.drawCentredString(4.5 * inch, 7.25 * inch,
                        "J Elliott Cisneros MEd, Carla Sherrell, EdD ~ 2016 ALL RIGHTS RESERVED (c)")

    # point breakdown and name
    p.setFont("Helvetica-Bold", 14)
    if assessment.user is None:
        p.drawString(0, 6.85 * inch, "Survey Results For: " + assessment.email)
    else:
        p.drawString(0, 6.85 * inch, "Survey Results For: " + assessment.user.last_name + ", " + assessment.user.first_name)
    p.setFont("Helvetica-Oblique", 14)
    p.drawString(0, 6.5 * inch, "POINTS:")
    p.setFont("Helvetica", 12)
    p.drawString(0, 6.25 * inch, 'For every "a" response: 4 pts')
    p.drawString(0, 6 * inch, 'For every "b" response: 3 pts')
    p.drawString(0, 5.75 * inch, 'For every "c" response, 2 pts')
    p.drawString(0, 5.5 * inch, 'For every "d" response, 1 pt')
    p.drawString(0, 5.25 * inch, 'For every "e" response, 0 pts')

    # Response options
    p.setFont("Helvetica-Oblique", 14)
    p.drawString(2.5 * inch, 6.5 * inch, "RESPONSE OPTIONS")
    p.setFont("Helvetica", 12)
    p.drawString(3 * inch, 6.25 * inch, "a. strongly agree")
    p.drawString(3 * inch, 6 * inch, "b. agree more than disagree")
    p.drawString(3 * inch, 5.75 * inch, "c. agree and disagree about the same")
    p.drawString(3 * inch, 5.5 * inch, "d. disagree more than agree; dislike")
    p.drawString(3 * inch, 5.25 * inch, "e. strongly disagree")

    # Image: text box to the right of response options
    p.drawInlineImage(pdf_static_path("core/img/page3_1.jpg"), 6 * inch, 5.5 * inch, 2.75 * inch, 1.25 * inch)

    key_data = [[""], [""], [""], [""], [""]]  # empty, to be filled with colors
    # TableStyle object holds modifiers for table
    key_style = TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.yellow),
        ('BACKGROUND', (0, 1), (0, 1), colors.green),
        ('BACKGROUND', (0, 2), (0, 2), colors.purple),
        ('BACKGROUND', (0, 3), (0, 3), colors.HexColor("#EC491E")),
        ('BACKGROUND', (0, 4), (0, 4), colors.HexColor("#4E89D9"))
    ])
    # create the table object
    key_table = Table(data=key_data, colWidths=.426 * inch)
    # apply the styles from above
    key_table.setStyle(key_style)
    # set canvas, width, and height
    key_table.wrapOn(p, .426 * inch, 1.25 * inch)
    # draw it onto the canvas at (x, y)
    key_table.drawOn(p, 2.5 * inch, 5.15 * inch)

    # Image: logo on right corner of pdf
    p.drawInlineImage(pdf_static_path("core/img/pda_pdf_header.jpg"), 9 * inch, 6.5 * inch, 1.5 * inch, 1.5 * inch)

    # key
    p.setFont("Helvetica-Oblique", 14)
    p.drawString(0, 4.75 * inch, "KEY:")
    p.setFont("Helvetica", 12)
    p.drawString(0, 4.5 * inch, "s#: statement #")
    p.drawString(0, 4.25 * inch, "r: response")
    p.drawString(0, 4 * inch, "p: power")

    # power perspectives
    p.setFont("Helvetica-Oblique", 12)
    p.drawString(1.25 * inch, 4.9 * inch, "POWER PERSPECTIVES:")
    p.setFont("Helvetica", 12)
    p.drawString(1.25 * inch, 4.65 * inch, "se=sensitivity")
    p.drawString(1.25 * inch, 4.4 * inch, "a=appreciation")
    p.drawString(1.25 * inch, 4.15 * inch, "s=strength")
    p.drawString(1.25 * inch, 3.9 * inch, "o=oneness")
    p.drawString(1.25 * inch, 3.65 * inch, "l=leveraged")

    # example images
    p.setFont("Helvetica-Oblique", 12)
    p.drawString(3.5 * inch, 4.9 * inch, 'SAMPLE "LEVERAGING" RESULTS:')
    # if os.environ.get('TRAVIS') != 'true':
    p.drawInlineImage(pdf_static_path("core/img/page3_2.jpg"), 3.5 * inch, 2.65 * inch, 1 * inch, 2 * inch)
    p.drawInlineImage(pdf_static_path("core/img/page3_3.jpg"), 4.5 * inch, 2.65 * inch, 2.75 * inch, 2 * inch)
    p.drawInlineImage(pdf_static_path("core/img/page3_4.jpg"), 7.25 * inch, 3.40 * inch, 2.75 * inch, 1.25 * inch)
    p.drawInlineImage(pdf_static_path("core/img/page3_5.jpg"), 7.25 * inch, 2.65 * inch, 2.5 * inch, .75 * inch)

    # table headers
    pstyle = ParagraphStyle('default')
    religion_head = Paragraph("<b><u>Religion</u></b>", pstyle)
    disability_head = Paragraph("<b><u>Disability</u></b>", pstyle)
    culture_head = Paragraph("<b><u>Culture</u></b>", pstyle)
    gender_head = Paragraph("<b><u>Gender</u></b>", pstyle)
    race_head = Paragraph("<b><u>Race</u></b>", pstyle)
    class_head = Paragraph("<b><u>Class</u></b>", pstyle)
    sexual_orientation_head = Paragraph("<b><u>LGBTQ+</u></b>", pstyle)

    # religion table
    # first two rows
    religion_data = [[religion_head],
                     ["s#", "r", "p"]]

    # styles for religion table
    # merges header cells, draws gridlines, makes second header row grey
    religion_style = TableStyle([
        ('SPAN', (0, 0), (2, 0)),  # merges cells in first row
        ('INNERGRID', (0, 0), (-1, -1), .25, colors.black),  # adds gridlines
        ('BOX', (0, 0), (-1, -1), 2, colors.black),  # adds outer gridlines
        ('BACKGROUND', (0, 1), (2, 1), colors.lightgrey),  # sets background for second row
    ])

    # fetches relevant responses from the database.  Be careful if editing!
    religion_responses = Response.objects.filter(assessment=assessment, sociocultural_location="Religion").order_by(
        'question_number')

    # adds data to table
    for response in religion_responses:
        r = get_response_letter(response.response)
        pers = get_perspective_letter(response.power_perspective)
        religion_data.append([response.question_number, r, pers])
        row = len(religion_data) - 1  # current row is last data entered
        # adds background color depending on which response was chosen
        if r == 'a':
            religion_style.add('BACKGROUND', (1, row), (1, row), colors.yellow)
        elif r == 'b':
            religion_style.add('BACKGROUND', (1, row), (1, row), colors.green)
        elif r == 'c':
            religion_style.add('BACKGROUND', (1, row), (1, row), colors.purple)
        elif r == 'd':
            religion_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#EC491E"))
        elif r == 'e':
            religion_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#4E89D9"))

    religion_table = Table(religion_data, colWidths=.426 * inch, rowHeights=.2 * inch)
    religion_table.setStyle(religion_style)

    # disability table
    disability_data = [[disability_head],
                       ["s#", "r", "p"]]
    disability_style = TableStyle([
        ('SPAN', (0, 0), (2, 0)),
        ('INNERGRID', (0, 0), (-1, -1), .25, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('BACKGROUND', (0, 1), (2, 1), colors.lightgrey),
    ])
    disability_responses = Response.objects.filter(assessment=assessment, sociocultural_location="Disability").order_by(
        'question_number')
    for response in disability_responses:
        r = get_response_letter(response.response)
        pers = get_perspective_letter(response.power_perspective)
        disability_data.append([response.question_number, r, pers])
        row = len(disability_data) - 1
        if r == 'a':
            disability_style.add('BACKGROUND', (1, row), (1, row), colors.yellow)
        elif r == 'b':
            disability_style.add('BACKGROUND', (1, row), (1, row), colors.green)
        elif r == 'c':
            disability_style.add('BACKGROUND', (1, row), (1, row), colors.purple)
        elif r == 'd':
            disability_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#EC491E"))
        elif r == 'e':
            disability_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#4E89D9"))

    disability_table = Table(disability_data, colWidths=.426 * inch, rowHeights=.2 * inch)
    disability_table.setStyle(disability_style)

    # culture table
    culture_data = [[culture_head],
                    ["s#", "r", "p"]]
    culture_style = TableStyle([
        ('SPAN', (0, 0), (2, 0)),
        ('INNERGRID', (0, 0), (-1, -1), .25, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('BACKGROUND', (0, 1), (2, 1), colors.lightgrey),
    ])
    culture_responses = Response.objects.filter(assessment=assessment, sociocultural_location="Culture").order_by(
        'question_number')
    for response in culture_responses:
        r = get_response_letter(response.response)
        pers = get_perspective_letter(response.power_perspective)
        culture_data.append([response.question_number, r, pers])
        row = len(culture_data) - 1
        if r == 'a':
            culture_style.add('BACKGROUND', (1, row), (1, row), colors.yellow)
        elif r == 'b':
            culture_style.add('BACKGROUND', (1, row), (1, row), colors.green)
        elif r == 'c':
            culture_style.add('BACKGROUND', (1, row), (1, row), colors.purple)
        elif r == 'd':
            culture_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#EC491E"))
        elif r == 'e':
            culture_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#4E89D9"))

    culture_table = Table(culture_data, colWidths=.426 * inch, rowHeights=.2 * inch)
    culture_table.setStyle(culture_style)

    # gender table
    gender_data = [[gender_head],
                   ["s#", "r", "p"]]
    gender_style = TableStyle([
        ('SPAN', (0, 0), (2, 0)),
        ('INNERGRID', (0, 0), (-1, -1), .25, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('BACKGROUND', (0, 1), (2, 1), colors.lightgrey),
    ])
    gender_responses = Response.objects.filter(assessment=assessment, sociocultural_location="Gender").order_by(
        'question_number')
    for response in gender_responses:
        r = get_response_letter(response.response)
        pers = get_perspective_letter(response.power_perspective)
        gender_data.append([response.question_number, r, pers])
        row = len(gender_data) - 1
        if r == 'a':
            gender_style.add('BACKGROUND', (1, row), (1, row), colors.yellow)
        elif r == 'b':
            gender_style.add('BACKGROUND', (1, row), (1, row), colors.green)
        elif r == 'c':
            gender_style.add('BACKGROUND', (1, row), (1, row), colors.purple)
        elif r == 'd':
            gender_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#EC491E"))
        elif r == 'e':
            gender_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#4E89D9"))

    gender_table = Table(gender_data, colWidths=.426 * inch, rowHeights=.2 * inch)
    gender_table.setStyle(gender_style)

    # race table
    race_data = [[race_head],
                 ["s#", "r", "p"]]
    race_style = TableStyle([
        ('SPAN', (0, 0), (2, 0)),
        ('INNERGRID', (0, 0), (-1, -1), .25, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('BACKGROUND', (0, 1), (2, 1), colors.lightgrey),
    ])
    race_responses = Response.objects.filter(assessment=assessment, sociocultural_location="Race").order_by(
        'question_number')
    for response in race_responses:
        r = get_response_letter(response.response)
        pers = get_perspective_letter(response.power_perspective)
        race_data.append([response.question_number, r, pers])
        row = len(race_data) - 1
        if r == 'a':
            race_style.add('BACKGROUND', (1, row), (1, row), colors.yellow)
        elif r == 'b':
            race_style.add('BACKGROUND', (1, row), (1, row), colors.green)
        elif r == 'c':
            race_style.add('BACKGROUND', (1, row), (1, row), colors.purple)
        elif r == 'd':
            race_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#EC491E"))
        elif r == 'e':
            race_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#4E89D9"))

    race_table = Table(race_data, colWidths=.426 * inch, rowHeights=.2 * inch)
    race_table.setStyle(race_style)

    # class table
    class_data = [[class_head],
                  ["s#", "r", "p"]]
    class_style = TableStyle([
        ('SPAN', (0, 0), (2, 0)),
        ('INNERGRID', (0, 0), (-1, -1), .25, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('BACKGROUND', (0, 1), (2, 1), colors.lightgrey),
    ])
    class_responses = Response.objects.filter(assessment=assessment, sociocultural_location="Class").order_by(
        'question_number')
    for response in class_responses:
        r = get_response_letter(response.response)
        pers = get_perspective_letter(response.power_perspective)
        class_data.append([response.question_number, r, pers])
        row = len(class_data) - 1
        if r == 'a':
            class_style.add('BACKGROUND', (1, row), (1, row), colors.yellow)
        elif r == 'b':
            class_style.add('BACKGROUND', (1, row), (1, row), colors.green)
        elif r == 'c':
            class_style.add('BACKGROUND', (1, row), (1, row), colors.purple)
        elif r == 'd':
            class_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#EC491E"))
        elif r == 'e':
            class_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#4E89D9"))

    class_table = Table(class_data, colWidths=.426 * inch, rowHeights=.2 * inch)
    class_table.setStyle(class_style)

    # sexual orientation table
    sexual_orientation_data = [[sexual_orientation_head],
                               ["s#", "r", "p"]]
    sexual_orientation_style = TableStyle([
        ('SPAN', (0, 0), (2, 0)),
        ('INNERGRID', (0, 0), (-1, -1), .25, colors.black),
        ('BOX', (0, 0), (-1, -1), 2, colors.black),
        ('BACKGROUND', (0, 1), (2, 1), colors.lightgrey),
    ])
    sexual_orientation_responses = Response.objects.filter(assessment=assessment,
                                                           sociocultural_location="LGBQ+").order_by(
        'question_number')
    for response in sexual_orientation_responses:
        r = get_response_letter(response.response)
        pers = get_perspective_letter(response.power_perspective)
        sexual_orientation_data.append([response.question_number, r, pers])
        row = len(sexual_orientation_data) - 1
        if r == 'a':
            sexual_orientation_style.add('BACKGROUND', (1, row), (1, row), colors.yellow)
        elif r == 'b':
            sexual_orientation_style.add('BACKGROUND', (1, row), (1, row), colors.green)
        elif r == 'c':
            sexual_orientation_style.add('BACKGROUND', (1, row), (1, row), colors.purple)
        elif r == 'd':
            sexual_orientation_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#EC491E"))
        elif r == 'e':
            sexual_orientation_style.add('BACKGROUND', (1, row), (1, row), colors.HexColor("#4E89D9"))

    sexual_orientation_table = Table(sexual_orientation_data, colWidths=.426 * inch, rowHeights=.2 * inch)
    sexual_orientation_table.setStyle(sexual_orientation_style)

    # spacing of tables
    width = 1.28 * inch
    height = 3 * inch
    religion_table.wrapOn(p, width, height)
    religion_table.drawOn(p, .5 * inch, 0 * inch)

    disability_table.wrapOn(p, width, height)
    disability_table.drawOn(p, 1.78 * inch, 0 * inch)

    culture_table.wrapOn(p, width, height)
    culture_table.drawOn(p, 3.06 * inch, 0 * inch)

    gender_table.wrapOn(p, width, height)
    gender_table.drawOn(p, 4.34 * inch, 0 * inch)

    race_table.wrapOn(p, width, height)
    race_table.drawOn(p, 5.62 * inch, 0 * inch)

    class_table.wrapOn(p, width, height)
    class_table.drawOn(p, 6.90 * inch, 0 * inch)

    sexual_orientation_table.wrapOn(p, width, height)
    sexual_orientation_table.drawOn(p, 8.18 * inch, 0 * inch)

    # finishes page
    p.showPage()

    

    # page 3 - graphs
    p.translate(.75*inch, inch)

    # religion graph
    religion_drawing = Drawing(2.8 * inch, 1.8 * inch)
    religion_data = [
        (religion_score.sensitivity, religion_score.oneness, religion_score.strength, religion_score.appreciation,
         religion_score.leveraged)
    ]
    religion = generate_graph()
    religion.data = religion_data

    religion_title = String(1.4 * inch, 1.7 * inch, "Religion", textAnchor='middle')
    religion_title.fontName = 'Times-Bold'
    religion_title.fontSize = 13
    religion_drawing.add(religion_title)
    religion_drawing.add(religion)

    renderPDF.draw(religion_drawing, p, 0, 5 * inch, showBoundary=False)

    # disability graph
    disability_drawing = Drawing(3 * inch, 2 * inch)
    disability_data = [
        (disability_score.sensitivity, disability_score.oneness, disability_score.strength,
         disability_score.appreciation, disability_score.leveraged)
    ]
    disability = generate_graph()
    disability.data = disability_data
    disability_title = String(1.4 * inch, 1.7 * inch, "Disability", textAnchor='middle')
    disability_title.fontName = 'Times-Bold'
    disability_title.fontSize = 13
    disability_drawing.add(disability_title)
    disability_drawing.add(disability)
    renderPDF.draw(disability_drawing, p, 3.25 * inch, 5 * inch, showBoundary=False)

    # culture graph
    culture_drawing = Drawing(3 * inch, 2 * inch)
    culture_data = [
        (culture_score.sensitivity, culture_score.oneness, culture_score.strength, culture_score.appreciation,
         culture_score.leveraged)
    ]
    culture = generate_graph()
    culture.data = culture_data
    culture_title = String(1.4 * inch, 1.7 * inch, "Culture", textAnchor='middle')
    culture_title.fontName = 'Times-Bold'
    culture_title.fontSize = 13
    culture_drawing.add(culture_title)
    culture_drawing.add(culture)
    renderPDF.draw(culture_drawing, p, 6.5 * inch, 5 * inch, showBoundary=False)

    # gender graph
    gender_drawing = Drawing(3 * inch, 2 * inch)
    gender_data = [
        (gender_score.sensitivity, gender_score.oneness, gender_score.strength, gender_score.appreciation,
         gender_score.leveraged)
    ]
    gender = generate_graph()
    gender.data = gender_data
    gender_title = String(1.4 * inch, 1.7 * inch, "Gender", textAnchor='middle')
    gender_title.fontName = 'Times-Bold'
    gender_title.fontSize = 13
    gender_drawing.add(gender_title)
    gender_drawing.add(gender)
    renderPDF.draw(gender_drawing, p, 0 * inch, 2.5 * inch, showBoundary=False)

    # race graph
    race_drawing = Drawing(3 * inch, 2 * inch)
    race_data = [
        (race_score.sensitivity, race_score.oneness, race_score.strength, race_score.appreciation,
         race_score.leveraged)
    ]
    race = generate_graph()
    race.data = race_data
    race_title = String(1.4 * inch, 1.7 * inch, "Race", textAnchor='middle')
    race_title.fontName = 'Times-Bold'
    race_title.fontSize = 13
    race_drawing.add(race_title)
    race_drawing.add(race)
    renderPDF.draw(race_drawing, p, 3.25 * inch, 2.5 * inch, showBoundary=False)

    # class graph
    class_drawing = Drawing(3 * inch, 2 * inch)
    class_data = [
        (class_score.sensitivity, class_score.oneness, class_score.strength, class_score.appreciation,
         class_score.leveraged)
    ]
    class_graph = generate_graph()
    class_graph.data = class_data
    class_title = String(1.4 * inch, 1.7 * inch, "Class", textAnchor='middle')
    class_title.fontName = 'Times-Bold'
    class_title.fontSize = 13
    class_drawing.add(class_title)
    class_drawing.add(class_graph)
    renderPDF.draw(class_drawing, p, 6.5 * inch, 2.5 * inch, showBoundary=False)

    # sexual orientation graph
    sexual_orientation_drawing = Drawing(3 * inch, 2 * inch)
    sexual_orientation_data = [
        (sexual_orientation_score.sensitivity, sexual_orientation_score.oneness, sexual_orientation_score.strength,
         sexual_orientation_score.appreciation, sexual_orientation_score.leveraged)
    ]
    sexual_orientation_graph = generate_graph()
    sexual_orientation_graph.data = sexual_orientation_data
    sexual_orientation_title = String(1.4 * inch, 1.7 * inch, "Sexual Orientation", textAnchor='middle')
    sexual_orientation_title.fontName = 'Times-Bold'
    sexual_orientation_title.fontSize = 13
    sexual_orientation_drawing.add(sexual_orientation_title)
    sexual_orientation_drawing.add(sexual_orientation_graph)
    renderPDF.draw(sexual_orientation_drawing, p, 0 * inch, 0 * inch, showBoundary=False)

    # Image: logo on bottom of page
    p.drawInlineImage(pdf_static_path("core/img/pda_pdf_logo.jpg"), 3.6 * inch, -.25 * inch, 2 * inch, 2 * inch)

    # total across all graph
    total_drawing = Drawing(3 * inch, 2 * inch)
    total_data = [
        (score.sensitivity_total, score.oneness_total, score.strength_total, score.appreciation_total,
         score.leveraged_total)
    ]
    total_graph = generate_total_graph()
    total_graph.data = total_data
    total_title = String(1.4 * inch, 1.6 * inch, "Total across all", textAnchor='middle')
    total_title.fontName = 'Times-Bold'
    total_title.fontSize = 13
    total_drawing.add(total_title)
    total_drawing.add(total_graph)
    renderPDF.draw(total_drawing, p, 6.5 * inch, 0 * inch, showBoundary=False)

    p.showPage()

    # page 4 - more graphs
    p.translate(.25 * inch, -.25 * inch)

    # locations and responses to loop through
    locations = ["Religion", "Disability", "Culture", "Gender", "Race", "Class", "LGBQ+"]
    responses = ["strongly agree",
                 "agree more than disagree",
                 "agree and disagree about the same",
                 "disagree more than agree",
                 "strongly disagree"]

    se_totals = [0, 0, 0, 0, 0]
    o_totals = [0, 0, 0, 0, 0]
    s_totals = [0, 0, 0, 0, 0]
    a_totals = [0, 0, 0, 0, 0]
    l_totals = [0, 0, 0, 0, 0]

    # create a table for each social_location, left to right
    for location in locations:
        se_loc_total = 0
        o_loc_total = 0
        s_loc_total = 0
        a_loc_total = 0
        l_loc_total = 0
        # utility to multiply number of responses by point value
        # decremented at end of loop
        multiplier = 4
        # utility to see what index to add to in totals lists
        # incremented at end of loop
        response_num = 0  # 0 = a, 1 = b, ...
        for response in responses:
            # count the number of responses for each perspective matching the current response
            se = Response.objects.filter(assessment=assessment, power_perspective="Sensitivity", response=response,
                                         sociocultural_location=location).count()
            o = Response.objects.filter(assessment=assessment, power_perspective="Oneness", response=response,
                                        sociocultural_location=location).count()
            s = Response.objects.filter(assessment=assessment, power_perspective="Strength", response=response,
                                        sociocultural_location=location).count()
            a = Response.objects.filter(assessment=assessment, power_perspective="Appreciation", response=response,
                                        sociocultural_location=location).count()
            l = Response.objects.filter(assessment=assessment, power_perspective="Leveraged", response=response,
                                        sociocultural_location=location).count()
            # multiply by number of points for this response
            # append totals to data, i.e. add a row
            total = multiplier * (se + o + s + a + l)
            se_totals[response_num] += se * multiplier
            o_totals[response_num] += o * multiplier
            s_totals[response_num] += s * multiplier
            a_totals[response_num] += a * multiplier
            l_totals[response_num] += l * multiplier

            # decrement multiplier and increment response_num
            multiplier -= 1
            response_num += 1

    p.drawString(0, 8.5 * inch, "Totals for each Power Perspective by response option/point value")
    p.drawString(0, 8.27 * inch, "a. strongly agree; love")  # multiplier = 4
    data = [
        [int(se_totals[0] / 4), "se", se_totals[0]],
        [int(o_totals[0] / 4), "o", o_totals[0]],
        [int(s_totals[0] / 4), "s", s_totals[0]],
        [int(a_totals[0] / 4), "a", a_totals[0]],
        [int(l_totals[0] / 4), "l", l_totals[0]]]
    table = Table(data, colWidths=.4 * inch, rowHeights=.23 * inch)
    table.wrapOn(p, 1.28 * inch, 1.15 * inch)
    table.drawOn(p, 0, 7.12 * inch)
    p.drawString(0, 6.89 * inch, "b. agree more than disagree; like")  # multiplier = 3
    data = [
        [int(se_totals[1] / 3), "se", se_totals[1]],
        [int(o_totals[1] / 3), "o", o_totals[1]],
        [int(s_totals[1] / 3), "s", s_totals[1]],
        [int(a_totals[1] / 3), "a", a_totals[1]],
        [int(l_totals[1] / 3), "l", l_totals[1]]]
    table = Table(data, colWidths=.4 * inch, rowHeights=.23 * inch)
    table.wrapOn(p, 1.28 * inch, 1.15 * inch)
    table.drawOn(p, 0, 5.74 * inch)
    p.drawString(0, 5.51 * inch, "c. agree and disagree about the same; neutral emotional reaction")  # multiplier = 2
    data = [
        [int(se_totals[2] / 2), "se", se_totals[2]],
        [int(o_totals[2] / 2), "o", o_totals[2]],
        [int(s_totals[2] / 2), "s", s_totals[2]],
        [int(a_totals[2] / 2), "a", a_totals[2]],
        [int(l_totals[2] / 2), "l", l_totals[2]]]
    table = Table(data, colWidths=.4 * inch, rowHeights=.23 * inch)
    table.wrapOn(p, 1.28 * inch, 1.15 * inch)
    table.drawOn(p, 0, 4.36 * inch)
    p.drawString(0, 4.13 * inch, "d. disagree more than agree; dislike")  # multiplier = 1
    data = [
        [int(se_totals[3]), "se", se_totals[3]],
        [int(o_totals[3]), "o", o_totals[3]],
        [int(s_totals[3]), "s", s_totals[3]],
        [int(a_totals[3]), "a", a_totals[3]],
        [int(l_totals[3]), "l", l_totals[3]]]
    table = Table(data, colWidths=.4 * inch, rowHeights=.23 * inch)
    table.wrapOn(p, 1.28 * inch, 1.15 * inch)
    table.drawOn(p, 0, 2.98 * inch)
    p.drawString(0, 2.75 * inch, "e. strongly disagree; hate")  # multiplier = 0
    # need to recalculate totals because they can't be derived due to multiplier of 0
    se = Response.objects.filter(assessment=assessment, power_perspective="Sensitivity",
                                 response="strongly disagree").count()
    o = Response.objects.filter(assessment=assessment, power_perspective="Oneness",
                                response="strongly disagree").count()
    s = Response.objects.filter(assessment=assessment, power_perspective="Strength",
                                response="strongly disagree").count()
    a = Response.objects.filter(assessment=assessment, power_perspective="Appreciation",
                                response="strongly disagree").count()
    l = Response.objects.filter(assessment=assessment, power_perspective="Leveraged",
                                response="strongly disagree").count()
    data = [
        [se, "se", 0],
        [o, "o", 0],
        [s, "s", 0],
        [a, "a", 0],
        [l, "l", 0]]
    table = Table(data, colWidths=.4 * inch, rowHeights=.23 * inch)
    table.wrapOn(p, 1.28 * inch, 1.15 * inch)
    table.drawOn(p, 0, 1.6 * inch)

    # totals
    data = [
        ["sensitivity", score.sensitivity_total],
        ["oneness", score.oneness_total],
        ["strength", score.strength_total],
        ["appreciation", score.appreciation_total],
        ["leveraged", str(score.leveraged_total) + "    " + str(
            56 - score.leveraged_total) + '  (difference between "leveraged" possible and "leveraged" chosen)']
    ]
    table = Table(data, colWidths=1.2 * inch, rowHeights=.16 * inch)
    table.wrapOn(p, 1.28 * inch, .8 * inch)
    table.drawOn(p, 0, .8 * inch)
    leveraged_difference = 56 - score.leveraged_total
    total = score.sensitivity_total + score.oneness_total + score.strength_total + score.appreciation_total + leveraged_difference
    percentage = int(round((float(total) / float(280)), 2) * 100)
    round(percentage, 2)
    data = [
        ["Total", total, "out of 280", "or", str(percentage) + r"%",
         "conflicts with leveraged perspective", str(100 - percentage) + r"% aligned with a leveraged perspective."]]
    table = Table(data, rowHeights=.16 * inch)
    table.wrapOn(p, 9 * inch, .16 * inch)
    table.drawOn(p, 0, .56 * inch)

    # right half of page 6
    p.drawString(5.25 * inch, 8.5 * inch, "Intersectional Data: Total Points Across All Sociocultural Locations")
    data = [
        ["", "religion", "disability", "ethnicity", "gender", "race", "class", "lgbtq+"],
        ["sensitivity", score.Religion_Score.sensitivity, score.Disability_Score.sensitivity,
         score.Culture_Score.sensitivity, score.Gender_Score.sensitivity,
         score.Race_Score.sensitivity, score.Class_Score.sensitivity, score.Sexual_Orientation_Score.sensitivity],
        ["oneness", score.Religion_Score.oneness, score.Disability_Score.oneness, score.Culture_Score.oneness,
         score.Gender_Score.oneness,
         score.Race_Score.oneness, score.Class_Score.oneness, score.Sexual_Orientation_Score.oneness],
        ["strength", score.Religion_Score.strength, score.Disability_Score.strength, score.Culture_Score.strength,
         score.Gender_Score.strength,
         score.Race_Score.strength, score.Class_Score.strength, score.Sexual_Orientation_Score.strength],
        ["appreciation", score.Religion_Score.appreciation, score.Disability_Score.appreciation,
         score.Culture_Score.appreciation, score.Gender_Score.appreciation,
         score.Race_Score.appreciation, score.Class_Score.appreciation, score.Sexual_Orientation_Score.appreciation],
        ["leveraged", score.Religion_Score.leveraged, score.Disability_Score.leveraged, score.Culture_Score.leveraged,
         score.Gender_Score.leveraged,
         score.Race_Score.leveraged, score.Class_Score.leveraged, score.Sexual_Orientation_Score.leveraged]
    ]
    table = Table(data, rowHeights=.16 * inch)
    table.wrapOn(p, 5.25 * inch, 1.44 * inch)
    table.drawOn(p, 5.25 * inch, 7.24 * inch)

    # radar chart
    d = Drawing(5.25 * inch, 2.8 * inch)
    spider = SpiderChart()
    spider.width = 3.5 * inch
    spider.height = 2.5 * inch

    spider.labels = ["leveraged", "sensitivity", "oneness", "appreciation", "strength"]
    spider.data = [
        (score.Religion_Score.leveraged, score.Religion_Score.sensitivity, score.Religion_Score.oneness,
         score.Religion_Score.appreciation, score.Religion_Score.strength),
        (score.Disability_Score.leveraged, score.Disability_Score.sensitivity, score.Disability_Score.oneness,
         score.Disability_Score.appreciation, score.Disability_Score.strength),
        (score.Culture_Score.leveraged, score.Culture_Score.sensitivity, score.Culture_Score.oneness,
         score.Culture_Score.appreciation, score.Culture_Score.strength),
        (score.Gender_Score.leveraged, score.Gender_Score.sensitivity, score.Gender_Score.oneness,
         score.Gender_Score.appreciation, score.Gender_Score.strength),
        (score.Race_Score.leveraged, score.Race_Score.sensitivity, score.Race_Score.oneness,
         score.Race_Score.appreciation, score.Race_Score.strength),
        (score.Class_Score.leveraged, score.Class_Score.sensitivity, score.Class_Score.oneness,
         score.Class_Score.appreciation, score.Class_Score.strength),
        (score.Sexual_Orientation_Score.leveraged, score.Sexual_Orientation_Score.sensitivity,
         score.Sexual_Orientation_Score.oneness, score.Sexual_Orientation_Score.appreciation,
         score.Sexual_Orientation_Score.strength)
    ]
    spider.direction = 'clockwise'

    # sets colors for radar graph lines
    spider.strands[0].strokeColor = colors.blue
    spider.strands[1].strokeColor = colors.red
    spider.strands[2].strokeColor = colors.green
    spider.strands[3].strokeColor = colors.purple
    spider.strands[4].strokeColor = colors.turquoise
    spider.strands[5].strokeColor = colors.orange
    spider.strands[6].strokeColor = colors.blueviolet

    # sets width of radar graph lines
    spider.strands.strokeWidth = 2

    d.add(spider)

    # legend for radar graph
    legend = Legend()
    legend.x = -1.2 * inch
    legend.y = 2.2 * inch
    legend.columnMaximum = 7
    legend.boxAnchor = 'nw'
    cols = [colors.blue, colors.red, colors.green, colors.purple, colors.turquoise, colors.orange, colors.blueviolet]
    categories = ("Religion", "Disability", "Culture", "Gender", "Race", "Class", "Sexual Orientation")
    legend.colorNamePairs = list(zip(cols, categories))
    d.add(legend)

    renderPDF.draw(d, p, 6.75 * inch, 4.5 * inch, showBoundary=False)

    # bar graph of unacknowledged power quotient
    d = Drawing(5.25 * inch, 2.8 * inch)
    data = [
        [percentage],
        [100 - percentage]
    ]
    bc = HorizontalBarChart()
    bc.data = data
    bc.fillColor = colors.white
    bc.strokeColor = colors.black
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 100
    bc.valueAxis.valueStep = 10
    bc.barWidth = .1 * inch
    bc.width = 4.5 * inch
    bc.height = 1.5 * inch
    bc.barLabelArray = [
        str(percentage) + r"%",
        str(100 - percentage) + r"%"
    ]
    bc.barLabelFormat = "%s"
    bc.barLabels.fontName = 'Helvetica-Bold'
    bc.barLabels.fontSize = 18
    # centers labels within respective bars
    bc.barLabels[0].dx = -4.5 * float(percentage / 200) * inch
    bc.barLabels[1].dx = -4.5 * float((100 - percentage) / 200) * inch
    bc.bars[0].fillColor = colors.lightgrey
    bc.bars[1].fillColor = colors.darkgrey
    bc.categoryAxis.style = 'stacked'
    d.add(bc)
    renderPDF.draw(d, p, 5.1 * inch, 1.5 * inch, showBoundary=False)
    # title for unacknowledged power quotient chart
    p.setFont("Helvetica-Bold", 14)
    p.drawString(5.5 * inch, 3.75 * inch, "* Unknown/Unacknowledged Power Quotient")

    p.showPage()

    # page 5 - point calculation table
    p.translate(inch, inch)
    
    # utility to track which column is currently being edited
    column_num = 0

    # totals for far right column

    # create a table for each social_location, left to right
    for location in locations:
        # table data, to be appended to.  Starts with header
        data = [[location],
                ["", "mr", "mrp"]]
        # merge first row columns
        style = TableStyle([
            ('SPAN', (0, 0), (2, 0)),
        ])
        se_loc_total = 0
        o_loc_total = 0
        s_loc_total = 0
        a_loc_total = 0
        l_loc_total = 0
        # utility to multiply number of responses by point value
        # decremented at end of loop
        multiplier = 4
        # utility to see what index to add to in totals lists
        # incremented at end of loop
        response_num = 0  # 0 = a, 1 = b, ...
        for response in responses:
            data.append([str(multiplier) + " points"])
            # count the number of responses for each perspective matching the current response
            se = Response.objects.filter(assessment=assessment, power_perspective="Sensitivity", response=response,
                                         sociocultural_location=location).count()
            o = Response.objects.filter(assessment=assessment, power_perspective="Oneness", response=response,
                                        sociocultural_location=location).count()
            s = Response.objects.filter(assessment=assessment, power_perspective="Strength", response=response,
                                        sociocultural_location=location).count()
            a = Response.objects.filter(assessment=assessment, power_perspective="Appreciation", response=response,
                                        sociocultural_location=location).count()
            l = Response.objects.filter(assessment=assessment, power_perspective="Leveraged", response=response,
                                        sociocultural_location=location).count()
            # multiply by number of points for this response
            # append totals to data, i.e. add a row
            total = multiplier * (se + o + s + a + l)
            data.append(['se', se, se * multiplier])
            data.append(['o', o, o * multiplier])
            data.append(['s', s, s * multiplier])
            data.append(['a', a, a * multiplier])
            data.append(['l', l, l * multiplier])
            data.append(['', 'total', total])

            # add to totals for this location
            se_loc_total += se * multiplier
            o_loc_total += o * multiplier
            s_loc_total += s * multiplier
            a_loc_total += a * multiplier
            l_loc_total += l * multiplier

            # decrement multiplier and increment response_num
            multiplier -= 1
            response_num += 1

        # totals at bottom of table
        data.append([location, "", "pts"])

        data.append(["sensitivity", "", se_loc_total])
        data.append(["oneness", "", o_loc_total])
        data.append(["strength", "", s_loc_total])
        data.append(["appreciation", "", a_loc_total])
        data.append(["leveraged", "", l_loc_total])

        # merge cells in totals rows
        style.add('SPAN', (0, -6), (1, -6))
        style.add('SPAN', (0, -5), (1, -5))
        style.add('SPAN', (0, -4), (1, -4))
        style.add('SPAN', (0, -3), (1, -3))
        style.add('SPAN', (0, -2), (1, -2))
        style.add('SPAN', (0, -1), (1, -1))

        # add outline to table
        style.add('BOX', (0, 0), (-1, -1), 2, colors.black),
        # add colors for point header rows
        style.add('BACKGROUND', (0, 2), (-1, 2), colors.yellow)
        style.add('BACKGROUND', (0, 9), (-1, 9), colors.green)
        style.add('BACKGROUND', (0, 16), (-1, 16), colors.purple)
        style.add('BACKGROUND', (0, 23), (-1, 23), colors.HexColor("#EC491E"))
        style.add('BACKGROUND', (0, 30), (-1, 30), colors.HexColor("#4E89D9"))
        # add lines to divide headers
        style.add('LINEABOVE', (0, 37), (-1, 37), 1, colors.black)
        style.add('LINEABOVE', (0, 2), (-1, 2), 1, colors.black)

        # make a table - one table for each social location, pushed together to look like columns
        table = Table(data, colWidths=.4266 * inch, rowHeights=.18 * inch)
        table.setStyle(style)
        table.wrapOn(p, 1.28 * inch, 8.5 * inch)
        table.drawOn(p, 1.28 * column_num * inch, -.5 * inch)
        column_num += 1

    # totals column on far right
    data = [[""],
            ["pttl"]]
    for i in range(0, 5):
        data.append([""])  # response line
        data.append([se_totals[i]])
        data.append([o_totals[i]])
        data.append([s_totals[i]])
        data.append([a_totals[i]])
        data.append([l_totals[i]])
        data.append([""])  # total line
    data.append(["total"])
    # sums all totals from every location
    data.append([sum(se_totals)])
    data.append([sum(o_totals)])
    data.append([sum(s_totals)])
    data.append([sum(a_totals)])
    data.append([sum(l_totals)])
    table = Table(data, colWidths=.4266 * inch, rowHeights=.18 * inch)
    style = TableStyle([
        ('BOX', (0, 0), (-1, -1), 2, colors.black)
    ])
    table.setStyle(style)
    table.wrapOn(p, .4266 * inch, 8.5 * inch)
    table.drawOn(p, 8.96 * inch, -.5 * inch)
    p.showPage()

    # finalizes PDF
    p.save()
    buffer.seek(0)
    # string to represent our filename
    naming = assessment.email + "_" + str(assessment.pk) + "_results.pdf"
    pdf = buffer.getvalue()
    # save the PDF to the S3 bucket!
    assessment.PDF.save(naming, buffer)
    assessment.save()
    # PDF generation ends here

    # only actually send email when someone takes the assessment (called_from_admin_site should be False)
    if (called_from_admin_site == False):
        group_users = CoreGroupuser.objects.filter(
            user=assessment.user,
            assessment=assessment
        )

        if len(group_users) > 0:
            # group participants contribute to the anonymous cohort report
            # and do not continue through the normal individual-results email path
            group_result(item)
            return False

        # environment variable for email toggle... always sends emails unless SEND_PDF_EMAIL env var is set to OFF
        if (settings.SEND_PDF_EMAIL != "OFF"):
            user = assessment.user
            # the below code should email the pdf results to the user and admin
            # setup what templates to use
            email_template = 'core/pdf_email_plain.html'
            html_email_template = 'core/pdf_email.html'

            template_context = {
                'abstract_user': user,
            }

            # fill the email with content
            mail_subject = "PDA Results"
            text_content = render_to_string(email_template, template_context)
            html_content = render_to_string(html_email_template, template_context)
            # bcc it to the admin email
            email = EmailMultiAlternatives(mail_subject, text_content, settings.FROM_EMAIL, to=[user.email],
                                        bcc=[settings.BCC_EMAIL])
            email.attach_alternative(html_content, "text/html")
            # attach PDF to email
            email.attach(naming, pdf, 'application/pdf')
            # send it
            email.send()

    # return False (no issues) to admin if we get here in admin site
    if (called_from_admin_site == True):
        return False


# sets base values for bar graph
def generate_total_graph():
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.lib import colors
    from reportlab.lib.units import inch

    bc = VerticalBarChart()
    bc.x = 0
    bc.y = 0
    bc.height = 1.8 * inch      # graph height
    bc.width = 2.8 * inch       # graph width
    bc.fillColor = colors.white
    bc.barLabelFormat = '%s'   
    bc.barLabels.nudge = 10     # moves bar labels up a bit
    bc.strokeColor = colors.black   
    bc.valueAxis.valueMin = 0   
    bc.valueAxis.valueMax = 60
    bc.valueAxis.valueStep = 10 # distance between gridlines
    bc.valueAxis.visibleGrid = 1  # makes grid visible.  Set to 0 to turn off  
    bc.categoryAxis.labels.boxAnchor = 'nw' 
    bc.categoryAxis.labels.dx = -30 # moves the x axis labels left a bit
    bc.categoryAxis.labels.dy = -35 # moves the x axis lables down a bit
    bc.categoryAxis.labels.angle = 45   # angle of text in labels
    bc.categoryAxis.categoryNames = ['Sensitivity', 'Oneness', 'Strength', 'Appreciation', 'Leveraged'] # names of x axis categories

    return bc


def generate_graph():
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.lib import colors
    from reportlab.lib.colors import Color
    from reportlab.lib.units import inch

    bc = VerticalBarChart()
    bc.x = 0
    bc.y = 0
    bc.height = 1.8 * inch
    bc.width = 2.8 * inch
    bc.fillColor = colors.white
    bc.strokeColor = colors.black
    bc.bars[0].fillColor = Color(100, 0, 0, alpha=.3)
    bc.barLabelFormat = '%s'
    bc.barLabels.nudge = 10
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 8
    bc.valueAxis.valueStep = 1
    bc.valueAxis.visibleGrid = 1
    bc.categoryAxis.labels.boxAnchor = 'nw'
    bc.categoryAxis.labels.dx = -30
    bc.categoryAxis.labels.dy = -35
    bc.categoryAxis.labels.angle = 45
    bc.categoryAxis.categoryNames = ['Sensitivity', 'Oneness', 'Strength', 'Appreciation', 'Leveraged']
    return bc


# utility function to turn response into letter
def get_response_letter(s):
    if s == "strongly agree":
        return "a"
    elif s == "agree more than disagree":
        return "b"
    elif s == "agree and disagree about the same":
        return "c"
    elif s == "disagree more than agree":
        return "d"
    else:
        return "e"


# utility function to turn power perspective into letter
def get_perspective_letter(s):
    if s == "Sensitivity":
        return "se"
    elif s == "Appreciation":
        return "a"
    elif s == "Strength":
        return "s"
    elif s == "Oneness":
        return "o"
    elif s == "Leveraged":
        return "l"


@assessment_completion_required
def score(request, user_id, assessment_id):
    # make sure that everything that should exist does
    # get the user
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return HttpResponseRedirect(reverse('core:register'))
    try:
        assessment = Assessment.objects.get(pk=assessment_id)
    except Assessment.DoesNotExist:
        if 'access_type' in request.session:
            del request.session['access_type']
        if 'assessment_id' in request.session:
            del request.session['assessment_id']
        if 'last_question' in request.session:
            del request.session['last_question']
        return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=dict(
            user_id=user_id)))
    try:
        score = Score.objects.get(assessment=assessment)
        kwargs = dict(user_id=user_id, assessment_id=assessment_id)
        return HttpResponseRedirect(reverse('core:finished', kwargs=kwargs))
    except Score.DoesNotExist:
        score = Score(assessment=assessment)

    # here (or wherever else once implemented) we finish an assessment... clear the time session variables
    toDel = ['year', 'month', 'day', 'hour', 'minute', 'second']
    for var in toDel:
        if var in request.session:
            del request.session[var]

    # try:
    #     score = Score.objects.get(assessment=assessment)
    # except Score.DoesNotExist:
    #     score = None

    gender_score = Gender_Score()
    race_score = Race_Score()
    religion_score = Religion_Score()
    sexual_orientation_score = Sexual_Orientation_Score()
    disability_score = Disability_Score()
    culture_score = Culture_Score()
    class_score = Class_Score()

    # get all of the responses for an assessment
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


    #generate pdf function
    generate_pdf(assessment.pk, False)


    kwargs = dict(user_id=user_id, assessment_id=assessment_id)
    return HttpResponseRedirect(reverse('core:finished', kwargs=kwargs))


class CustomSuitAdminContextMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        # required to work with django-suit (see: https://github.com/darklow/django-suit/blob/v2/demo/demo/views.py#L14)
        context = super().get_context_data(**kwargs)
        self.request.current_app = 'admin'
        from core.admin import admin_site
        context.update(admin_site.each_context(self.request))
        return context


def create_custom_suit_admin_view_class(base_class):
    class NewClass(CustomSuitAdminContextMixin, base_class):
        pass

    return NewClass


CustomPasswordResetView = create_custom_suit_admin_view_class(PasswordResetView)
CustomPasswordResetCompleteView = create_custom_suit_admin_view_class(PasswordResetCompleteView)
CustomPasswordResetConfirmView = create_custom_suit_admin_view_class(PasswordResetConfirmView)
CustomPasswordResetDoneView = create_custom_suit_admin_view_class(PasswordResetDoneView)


class CompleteConsultantRegistrationView(View):
    class PseudoConsultantAdmin(ModelAdmin):
        fieldsets = (
            (None, {
                'classes': ('wide',),
                'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name'),
            }),
        )  # fields consultant has to fill in to complete registration
        form = CompleteConsultantRegistrationForm

        def has_perm(self, request, obj):
            if obj is not None and request.user.pk == obj.pk:
                # only consultant can view his/her complete registration page
                return True
            return False

        def has_view_permission(self, request, obj=None):
            return self.has_perm(request, obj)

        def has_change_permission(self, request, obj=None):
            return self.has_perm(request, obj)

    pseudo_consultant_admin = PseudoConsultantAdmin(Consultant,
                                                    AdminSite())  # this allows using ModelAdmin's change_view, thus preventing the need to writing one from scratch

    def dispatch(self, request, *args, **kwargs):
        response = self.pseudo_consultant_admin.change_view(request, '%d' % self.kwargs['consultant_pk'])
        return response


class VerifyConsultantRegistrationCompletionLinkView(View):
    # Based on django.contrib.auth.views.PasswordResetView. (v 3.0.3)
    # Verifies if the link that requested consultant registration is indeed valid
    token_generator = default_token_generator

    def get_consultant(self):
        try:
            uid = urlsafe_base64_decode(self.kwargs['uidb64']).decode()
            return Consultant.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, Consultant.DoesNotExist, ValidationError):
            return None

    def dispatch(self, request, *args, **kwargs):
        assert 'uidb64' in kwargs and 'token' in kwargs
        consultant = self.get_consultant()
        if consultant is not None:
            token = self.kwargs['token']
            if self.token_generator.check_token(consultant, token):
                login(request, consultant, backend=AUTHENTICATION_BACKENDS[0])
                return HttpResponseRedirect(
                    reverse('admin:core_consultant_complete_registration', kwargs=dict(consultant_pk=consultant.pk)))
        return handle_invalid_link_error(request)


class CompleteViewOnlyAdminRegistrationView(View):
    class PseudoViewOnlyAdminAdmin(ModelAdmin):
        fieldsets = (
            (None, {
                'classes': ('wide',),
                'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name'),
            }),
        )
        form = CompleteViewOnlyAdminRegistrationForm

        def has_perm(self, request, obj):
            if obj is not None and request.user.pk == obj.pk:
                return True
            return False

        def has_view_permission(self, request, obj=None):
            return self.has_perm(request, obj)

        def has_change_permission(self, request, obj=None):
            return self.has_perm(request, obj)

    pseudo_view_only_admin_admin = PseudoViewOnlyAdminAdmin(ViewOnlyAdmin,
                                                            AdminSite())  # this allows using ModelAdmin's change_view, thus preventing the need to writing one from scratch

    def dispatch(self, request, *args, **kwargs):
        response = self.pseudo_view_only_admin_admin.change_view(request, '%d' % self.kwargs['view_only_admin_pk'])
        return response


class VerifyViewOnlyAdminRegistrationCompletionLinkView(View):
    # Based on django.contrib.auth.views.PasswordResetView. (v 3.0.3)
    token_generator = default_token_generator

    def get_view_only_admin(self):
        try:
            uid = urlsafe_base64_decode(self.kwargs['uidb64']).decode()
            return ViewOnlyAdmin.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, ViewOnlyAdmin.DoesNotExist, ValidationError):
            return None

    def dispatch(self, request, *args, **kwargs):
        assert 'uidb64' in kwargs and 'token' in kwargs
        view_only_admin = self.get_view_only_admin()
        if view_only_admin is not None:
            token = self.kwargs['token']
            if self.token_generator.check_token(view_only_admin, token):
                login(request, view_only_admin, backend=AUTHENTICATION_BACKENDS[0])
                return HttpResponseRedirect(
                    reverse('admin:core_view_only_admin_complete_registration',
                            kwargs=dict(view_only_admin_pk=view_only_admin.pk)))
        return handle_invalid_link_error(request)


class ClearSessionView(View):
    def get(self, request):
        is_finished = request.session.get('is_finished', False)
        if is_finished:
            request.session.flush()
            return HttpResponseRedirect(reverse('core:index'))
        return HttpResponseRedirect(reverse('core:continue'))


def custom_server_error(request):
    if not settings.DEBUG:
        logger = logging.getLogger(__name__)
        logger.error(INTERNAL_SERVER_ERROR_LOG_MESSAGE)  # This will help with
    # filtering 500 errors when DEBUG is False
    return server_error(request, template_name='core/500.html')


def custom_page_not_found(request, exception):
    return page_not_found(request, exception, template_name='core/404.html')


class AssessmentDetailedView(PermissionRequiredMixin, TemplateView):
    template_name = 'admin/core/assessment/detailed_view.html'
    permission_required = 'core.view_assessment'

    @staticmethod
    def get_user_fields_for_assessment(assessment):
        if assessment.user:
            return get_field_dict(assessment.user, exclude=('id', 'can_retake',))
        return None

    @staticmethod
    def get_demographic_fields_for_assessment(assessment):
        try:
            return get_field_dict(assessment.demographic, exclude=('id', 'assessment',))
        except Demographic.DoesNotExist:
            return None

    @staticmethod
    def sort_responses_by_response_choice(responses):

        def get_score_for_response(response):
            return response_choices_to_score_map[response.response]

        return sorted(responses, key=lambda response: get_score_for_response(response))

    @staticmethod
    def get_responses_for_assessment(assessment):
        responses = Response.objects.filter(assessment=assessment)
        for response in responses:
            question = Question.objects.get(number=response.question_number)
            response.statement = question.title
        return responses

    @staticmethod
    def get_pdf_link_for_assessment(assessment):
        if bool(assessment.PDF):
            return mark_safe("<a href=\"{}\" rel=\"noopener noreferrer\" target=\"_blank\">Click to view</a>".format(
                assessment.PDF.url))
        return "No report available"

    @staticmethod
    def get_consultants_for_assessment(assessment):
        consultants = assessment.consultants.all()
        if len(consultants) == 0:
            return "No consultants assigned"
        consultants_string = str(consultants.first())
        for consultant in consultants[1:]:
            consultants_string += ", " + str(consultant)
        return consultants_string

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assessment = Assessment.objects.get(pk=self.kwargs.get('assessment_pk'))
        responses = self.get_responses_for_assessment(assessment)
        context['assessment'] = assessment
        context['user_fields'] = self.get_user_fields_for_assessment(assessment)
        context['demographic_fields'] = self.get_demographic_fields_for_assessment(assessment)
        context['sociocultural_locations'] = SOCIOCULTURAL_LOCATIONS
        context['power_perspectives'] = POWER_PERSPECTIVES
        context['responses_sorted_by_question_number'] = list(responses)
        context['responses_sorted_by_response_choice'] = self.sort_responses_by_response_choice(responses)
        context['consultants'] = self.get_consultants_for_assessment(assessment)
        context['pdf_link'] = self.get_pdf_link_for_assessment(assessment)
        return context

    def get_permission_object(self):
        try:
            return Assessment.objects.get(pk=self.kwargs.get('assessment_pk'))
        except Assessment.DoesNotExist:
            return None
