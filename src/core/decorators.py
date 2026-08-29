from functools import wraps

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from .constants import INVALID_LAST_QUESTION_ERROR_MESSAGE, CANNOT_MOVE_BACKWARDS_MESSAGE
from .models import Question


def require_session_key_absence(session_key):
    """Prevents users from accessing urls that they have already passed"""
    def decorator_require_session_key_absence(func):
        @wraps(func)
        def wrapper_require_session_key_absence(request, *args, **kwargs):
            if session_key in request.session:
                messages.error(request, CANNOT_MOVE_BACKWARDS_MESSAGE)
                return HttpResponseRedirect(reverse('core:continue'))
            return func(request=request, *args, **kwargs)
        return wrapper_require_session_key_absence
    return decorator_require_session_key_absence


def valid_last_question_required(func):
    @wraps(func)
    def wrap(request, user_id, assessment_id, *args, **kwargs):
        if 'last_question' not in request.session:
            kwargs = dict(user_id=user_id, assessment_id=assessment_id)
            return HttpResponseRedirect(reverse('core:demographics', kwargs=kwargs))
        last_question = request.session['last_question']
        num_questions = Question.objects.count()
        assert 0 <= last_question <= num_questions, INVALID_LAST_QUESTION_ERROR_MESSAGE % last_question
        return func(request=request, user_id=user_id, assessment_id=assessment_id, *args, **kwargs)

    return wrap


def incomplete_assessment_required(func):
    @wraps(func)
    @valid_last_question_required
    def wrap(request, user_id, assessment_id, *args, **kwargs):
        if request.session['last_question'] == Question.objects.count():
            kwargs = dict(user_id=user_id, assessment_id=assessment_id)
            return HttpResponseRedirect(reverse('core:score', kwargs=kwargs))
        return func(request=request, user_id=user_id, assessment_id=assessment_id, *args, **kwargs)

    return wrap


def assessment_completion_required(func):
    @wraps(func)
    @valid_last_question_required
    def wrap(request, user_id, assessment_id, *args, **kwargs):
        if request.session['last_question'] != Question.objects.count():
            kwargs = dict(user_id=user_id, assessment_id=assessment_id, number=request.session['last_question'] + 1)
            return HttpResponseRedirect(reverse('core:question', kwargs=kwargs))
        return func(request=request, user_id=user_id, assessment_id=assessment_id, *args, **kwargs)

    return wrap
