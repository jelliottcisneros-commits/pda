from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm
from django.forms.utils import pretty_name
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from TheSum import settings
from core.models import AbstractUser, Demographic
from core.tokens import token_generator_for_abstract_user
from .constants import INVALID_LINK_MESSAGE

send_email = PasswordResetForm().send_mail

response_choices_to_score_map = {
    "strongly disagree": 0,
    "disagree more than agree": 1,
    "agree and disagree about the same": 2,
    "agree more than disagree": 3,
    "strongly agree": 4
}


def email_verification_token_to_abstract_user(domain: str,
                                              abstract_user: AbstractUser,
                                              email_subject: str,
                                              email_template_name: str,
                                              html_email_template_name: str):
    context = {
        'abstract_user': abstract_user,
        'domain': domain,
        'uid': urlsafe_base64_encode(force_bytes(abstract_user.pk)),
        'token': token_generator_for_abstract_user.make_token(abstract_user),
        'protocol': settings.PROTOCOL,
        'email_subject': email_subject
    }
    send_email(subject_template_name='core/email_subject.html',
               email_template_name=email_template_name,
               context=context,
               from_email=settings.FROM_EMAIL,
               to_email=abstract_user.email,
               html_email_template_name=html_email_template_name)


def redirect_with_error_message(request, error_message, redirect_url):
    messages.error(request, error_message)
    return HttpResponseRedirect(reverse(redirect_url))


def handle_invalid_link_error(request):
    return render(request, 'core/plain_message.html', {'message': INVALID_LINK_MESSAGE})


def setup_session_for_user(request, user):
    request.session.flush()
    request.session['user_id'] = user.pk


def is_request_from_core_app(request):
    resolver_match = request.resolver_match
    if resolver_match is not None:
        return resolver_match.app_name == 'core'
    return False


def is_auth_user_consultant(auth_user):
    try:
        _ = auth_user.consultant
        return True
    except:
        return False


def get_demographic_fields_as_choices():
    """Return a list of choice where each choice is a (demographic field name, demographic field verbose name) """
    demographic_fields = Demographic._meta.fields
    ret = []
    for (i, field) in enumerate(demographic_fields):
        if field.choices:
            ret.append((field.name, field.verbose_name))
    return ret


def get_demographic_field_to_choices_map():
    demographic_field_to_choices_map = {}
    demographic_fields = Demographic._meta.fields
    for field in demographic_fields:
        if field.choices:
            demographic_field_to_choices_map[field.name] = field.choices
    return demographic_field_to_choices_map


def get_field_dict(obj, exclude=()):
    """Returns a dict where the keys are the names of the fields, and the values are the fields' values"""
    ret = {}
    for field in obj._meta.fields:
        if field.name in exclude:
            continue
        ret[pretty_name(field.verbose_name)] = obj.__dict__.get(field.name)
    return ret
