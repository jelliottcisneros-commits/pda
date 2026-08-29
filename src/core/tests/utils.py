import logging

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpRequest
from django.test import Client
from django.contrib.auth.models import User as AuthUser

from TheSum import settings
from core.constants import ACCESS_TYPE_INST
from core.models import User, Demographic, Assessment, Question, UnverifiedUser, \
    SOCIOCULTURAL_LOCATIONS, POWER_PERSPECTIVES, Consultant, Response, ViewOnlyAdmin

USER_DICT = dict(first_name='Thomas', last_name='Jefferson', email='tj3va@virginia.edu', phone='444-444-4444')
CONSULTANT_DICT = dict(username='test_consultant', first_name='test', last_name='consultant',
                       email='test_consultant@email.com')
VIEW_ONLY_ADMIN_DICT = dict(username='test_view_only_admin', first_name='test', last_name='view_only_admin',
                       email='test_view_only_admin@email.com')
ASSESSMENT_DICT = dict(access_type=ACCESS_TYPE_INST, email='test@email.com')
QUESTION_DICT = dict(number=1, title="question 1", sociocultural_location=SOCIOCULTURAL_LOCATIONS[0][0],
                     primary_power_perspective=POWER_PERSPECTIVES[0][0])
DEMOGRAPHIC_DICT = dict(age="Under-17", religion="Buddhism", area="Urban", disability="Able-bodied",
                        socioeconomic="Other", employment="Other", education="Other", marital="Other", status="Other",
                        race_or_culture="Other", perception="As a White Person", sexual_orientation="LGBTQ+",
                        gender="Male", country_of_birth="Other", country_of_birth_state="Other", clocation="Other",
                        cstate="Other", purpose="Other",
                        safety="when we stop stereotyping, and treat all people with respect--the way we would like "
                               "to be treated.",
                        gender_perception='as a man')
RESPONSE_DICT = dict(power_perspective=POWER_PERSPECTIVES[0][0],
                     sociocultural_location=SOCIOCULTURAL_LOCATIONS[0][0],
                     response=Response.RESPONSE_CHOICES[0][0],
                     question_number=1)


def create_view_only_admin(view_only_admin_dict=None):
    if view_only_admin_dict is None:
        view_only_admin_dict = VIEW_ONLY_ADMIN_DICT
    view_only_admin = ViewOnlyAdmin()
    for attr, attr_val in view_only_admin_dict.items():
        setattr(view_only_admin, attr, attr_val)
    view_only_admin.set_password(BaseUserManager().make_random_password())
    view_only_admin.save()
    return view_only_admin    

def create_consultant(consultant_dict=None):
    if consultant_dict is None:
        consultant_dict = CONSULTANT_DICT
    consultant = Consultant()
    for attr, attr_val in consultant_dict.items():
        setattr(consultant, attr, attr_val)
    consultant.set_password(BaseUserManager().make_random_password())
    consultant.save()
    return consultant


def create_unverified_user(user_dict=None):
    if user_dict is None:
        user_dict = USER_DICT
    unverified_user = UnverifiedUser()
    for attr, attr_val in user_dict.items():
        setattr(unverified_user, attr, attr_val)
    unverified_user.save()
    return unverified_user


def create_user(user_dict=None):
    if user_dict is None:
        user_dict = USER_DICT
    user = User()
    for attr, attr_val in user_dict.items():
        setattr(user, attr, attr_val)
    user.save()
    return user


def create_assessment(user=None, assessment_dict=None):
    if assessment_dict is None:
        assessment_dict = ASSESSMENT_DICT
    assessment = Assessment()
    if user is not None:
        assessment.user = user
        assessment.email = user.email
    for attr, attr_val in assessment_dict.items():
        setattr(assessment, attr, attr_val)
    assessment.save()
    return assessment


def create_demographic(assessment, demographic_dict=None):
    if demographic_dict is None:
        demographic_dict = DEMOGRAPHIC_DICT
    demographic = Demographic()
    for attr, attr_val in demographic_dict.items():
        setattr(demographic, attr, attr_val)
    demographic.assessment = assessment
    demographic.save()
    assessment.demographic = demographic
    assessment.save()
    return demographic


def create_question(question_dict=None):
    if question_dict is None:
        question_dict = QUESTION_DICT
    question = Question()
    for attr, attr_val in question_dict.items():
        setattr(question, attr, attr_val)
    question.save()
    return question


def create_response(assessment, response_dict=None):
    if response_dict is None:
        response_dict = RESPONSE_DICT
    response = Response(assessment=assessment)
    for attr, attr_val in response_dict.items():
        setattr(response, attr, attr_val)
    response.save()
    return response


def set_session_key_for_client(client: Client, key, value):
    session = client.session
    session[key] = value
    session.save()


def delete_session_key_for_client(client: Client, key):
    session = client.session
    del session[key]
    session.save()


class MockHttpRequest(HttpRequest):
    """A subclass of HttpRequest with session and messages support. Useful when test Client is not making requests"""

    def __init__(self):
        super().__init__()
        self.session = SessionStore()
        self._messages = FallbackStorage(self)



def is_function_wrapped_by_decorator(function: callable, decorator_name: str):
    """
    modified from https://schinckel.net/2012/01/20/get-decorators-wrapping-a-function/
    :param function: The function in question
    :param decorator_name: The name of the decorator
    :return: True if the decorator is present, False otherwise
    """

    def get_callable_cells(func):
        callables = []
        if not hasattr(func, '__closure__'):
            if hasattr(func, 'view_func'):
                return get_callable_cells(func.view_func)
            return []
        if not func.__closure__:
            return [func]
        for closure in func.__closure__:
            contents = closure.cell_contents
            if isinstance(contents, list):
                for content in contents:
                    callables.extend(get_callable_cells(content))
            else:
                callables.extend(get_callable_cells(contents))
        return [func] + callables

    callable_cells = get_callable_cells(function)
    for i in range(len(callable_cells)):
        cell = callable_cells[i]
        if decorator_name in str(cell):
            return True
    return False

def disable_console_logging(logger: logging.Logger):
    logger.addHandler(logging.NullHandler(level=logging.INFO))

def login_as_super_user(client: Client):
    superuser = AuthUser.objects.create_superuser(
        username='test',
        password='test',
        email='test@test.com'
    )
    client.force_login(superuser)

