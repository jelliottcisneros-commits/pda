from datetime import datetime

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from core.helpers import is_request_from_core_app
from core.models import Question
from .constants import NOT_REGISTERED_MESSAGE, CHOOSE_ACCESS_TYPE_MESSAGE, MISSING_PERMISSION_ERROR_MESSAGE, \
    QUESTIONS_MISSING_FROM_DB_ERROR_MESSAGE
from .views import score, finished

ASSESSMENT_COMPLETE_REQUIRED_VIEW_FUNCS = {score, finished}


class RequiredDataMiddleware:
    """A middleware to check if the database has the required data, such as the questions"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if is_request_from_core_app(request):  # don't want to throw errors if the request is for a non core app page
            # such as an admin page.
            assert Question.objects.count() > 0, QUESTIONS_MISSING_FROM_DB_ERROR_MESSAGE
        return response


class PermissionMiddleware(MiddlewareMixin):
    # this checks if the URL params matches with the session variables.
    @staticmethod
    def process_view(request, view_func, view_args, view_kwargs):

        # handling user urls
        user_id = view_kwargs.get('user_id', None)
        if user_id is None:
            return None
        if 'user_id' not in request.session:
            messages.error(request, NOT_REGISTERED_MESSAGE)
            return HttpResponseRedirect(reverse('core:register'))
        if request.session['user_id'] != user_id:
            messages.error(request, MISSING_PERMISSION_ERROR_MESSAGE)
            return HttpResponseRedirect(reverse('core:continue'))  # let continue handle redirection
        kwargs = dict(user_id=user_id)

        # handling assessment urls
        assessment_id = view_kwargs.get('assessment_id', None)
        if assessment_id is None:
            return None
        if 'access_type' not in request.session:
            messages.error(request, CHOOSE_ACCESS_TYPE_MESSAGE)
            return HttpResponseRedirect(reverse('core:choose_access_type', kwargs=kwargs))
        if 'assessment_id' not in request.session:
            return HttpResponseRedirect(reverse('core:create_assessment', kwargs=kwargs))
        if request.session['assessment_id'] != assessment_id:
            messages.error(request, MISSING_PERMISSION_ERROR_MESSAGE)
            return HttpResponseRedirect(reverse('core:continue'))  # let continue handle redirection
        return None


# z = datetime(year,month,day,hour,minute,second)
# middleware to detect if a session should expire
# amount of time will be in seconds... currently set to 3600 (one hour) can change as desired
class SessionExpirationMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # if one of the time items is there, all of them should be there
        if 'year' in request.session:
            dt = datetime(request.session['year'], request.session['month'], request.session['day'],
                          request.session['hour'], request.session['minute'], request.session['second'])
            # rebuild the time of start and compare to datetime.now()
            # if too old, kill the session and go to our expiration page
            if (datetime.now() - dt).total_seconds() > 3600:
                request.session.flush()
                return HttpResponseRedirect(reverse('core:expired'))
        return self.get_response(request)
