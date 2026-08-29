from .settings import *  # IMPORTANT: Even if your IDE says this is unused, do not delete: this is setting up the
# default constants that don't need to be overridden for the tests

# overriding middleware to exclude RequiredDataMiddleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.SessionExpirationMiddleware',
    'core.middleware.PermissionMiddleware',
]
