from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

from core.admin import admin_site
from core.views import custom_server_error, custom_page_not_found, CustomPasswordResetView, CustomPasswordResetDoneView, \
    CustomPasswordResetConfirmView, CustomPasswordResetCompleteView

handler500 = custom_server_error
handler404 = custom_page_not_found

password_reset_urls = [
    # These urls rightful place is in core/admin.py.
    # However, the way default admin password reset templates work is that
    # they require the views to be named without an app_name prefix.
    # For example, 'password_reset' instead of 'core:password_reset', or 'admin:password_reset'
    # And the only way to achieve that was to put it here where there is no app name.
    path('admin/password_reset', CustomPasswordResetView.as_view(), name='admin_password_reset'),
    path('admin/password_reset/done', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('admin/reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('admin/reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]

urlpatterns = [
                  path('admin/', admin_site.urls),
                  path('paypal/', include('paypal.standard.ipn.urls')),
                  path('visualization/', include('visualization.urls')),
                  path('', include('core.urls')),
              ] + password_reset_urls + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
