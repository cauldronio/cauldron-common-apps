"""
Django settings for project.

Generated by 'django-admin startproject' using Django 3.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '!6_w+t5mzefpl2f0+kb#o3p5e^kn81oko@uzy+(q4crqi@z_e6'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

GIT_REPOS = os.environ.get('GIT_REPOS')
JOB_LOGS = os.environ.get('JOB_LOGS')
SPDX_FILES = os.environ.get('SPDX_FILES')

ES_IN_HOST = os.environ.get('ELASTIC_HOST')
ES_IN_PORT = os.environ.get('ELASTIC_PORT')
ES_ADMIN_PASSWORD = os.environ.get('ELASTIC_PASS')

KIB_IN_HOST = os.environ.get('KIBANA_HOST')
KIB_IN_PORT = os.environ.get('KIBANA_PORT')
KIB_PATH = os.environ.get('KIBANA_PATH')

SORTINGHAT = os.environ.get('SORTINGHAT', False) in (True, 'True', 'true')
SORTINGHAT_HOST = os.environ.get('SORTINGHAT_HOST')
SORTINGHAT_DATABASE = os.environ.get('SORTINGHAT_DATABASE')
SORTINGHAT_USER = os.environ.get('SORTINGHAT_USER')
SORTINGHAT_PASSWORD = os.environ.get('SORTINGHAT_PASSWORD')

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'poolsched',
    'cauldron_apps.poolsched_git',
    'cauldron_apps.poolsched_github',
    'cauldron_apps.poolsched_gitlab',
    'cauldron_apps.poolsched_meetup',
    'cauldron_apps.poolsched_stackexchange',
    'cauldron_apps.poolsched_twitter',
    'cauldron_apps.poolsched_autorefresh',
    'cauldron_apps.poolsched_merge_identities',
    'cauldron_apps.cauldron',
    'cauldron_apps.poolsched_export',
    'cauldron_apps.cauldron_actions',
    'cauldron_apps.poolsched_sbom',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'
