from django.urls import path

from .constants import VERIFY_EMAIL_INSTRUCTIONS
from .views import *

app_name = 'core'
urlpatterns = [
    path('continue', ContinueView.as_view(), name='continue'),
    path('register', RegisterView.as_view(), name='register'),
    path('retake', RetakeView.as_view(), name='retake'),
    path('verify_email_instructions',
         require_session_key_absence('user_id')(TemplateView.as_view(template_name='core/plain_message.html',
                                                                     extra_context=dict(
                                                                         message=VERIFY_EMAIL_INSTRUCTIONS))),
         name='verify_email_instructions'),
    path('verify_email/<uidb64>/<token>/', EmailVerificationView.as_view(), name='verify_email'),
    path('re_verify_email/<uidb64>/<token>/', EmailReVerificationView.as_view(), name='re_verify_email'),

    path('users/<int:user_id>/choose_access_type', choose_access_type, name='choose_access_type'),
    path('users/<int:user_id>/payment', payment, name='payment'),
    path('users/<int:user_id>/payment_cancelled', payment_cancelled, name='payment_cancelled'),
    path('users/<int:user_id>/verify_access_code', verify_access_code, name='verify_access_code'),
    #path('users/<int:user_id>/take_free_version', take_free_version, name='take_free_version'),
    path('users/<int:user_id>/assessments/create', create_assessment, name='create_assessment'),

    path('users/<int:user_id>/assessments/<int:assessment_id>/demographics_submit', demographics_submit,
         name='demographics_submit'),
    path('users/<int:user_id>/assessments/<int:assessment_id>/demographics', demographics, name='demographics'),
    path('users/<int:user_id>/assessments/<int:assessment_id>/statement/<int:number>', question, name='question'),
    path('users/<int:user_id>/assessments/<int:assessment_id>/statement/<int:number>/statement_submit',
         question_submit, name='question_submit'),
    path('users/<int:user_id>/assessments/<int:assessment_id>/instructions',
         instructions, name='instructions'),
    path('users/<int:user_id>/assessments/<int:assessment_id>/finished', finished, name='finished'),
    path('users/<int:user_id>/assessments/<int:assessment_id>/score', score, name='score'),
    path('clear_session', ClearSessionView.as_view(), name='clear_session'),
    path('expired', TemplateView.as_view(template_name='core/expired.html'), name='expired'),
    # Will be called from the middleware that checks if the assessment has gone on for too long
    path('', IndexView.as_view(), name='index'),
]

if settings.DEBUG:
    urlpatterns += [
        path('500', custom_server_error, name='server_error'),
        path('404', custom_page_not_found, name='page_not_found', kwargs=dict(exception=None)),
    ]
