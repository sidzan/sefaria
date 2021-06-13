# An example of settings needed in a local_settings.py file.
# copy this file to sefaria/local_settings.py and provide local info to run.
import os.path
from datetime import timedelta
relative_to_abs_path = lambda *x: os.path.join(os.path.dirname(
                               os.path.realpath(__file__)), *x)

import structlog
import os
import re

# These are things you need to change!

################ YOU ONLY NEED TO CHANGE "NAME" TO THE PATH OF YOUR SQLITE DATA FILE (If the db.sqlite file does not exist, simply create it) ########################################
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'sefaria_auth',
        'USER': 'sefaria',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    }
}

"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'name of db table here',
        'USER': 'name of db user here',
        'PASSWORD': 'password here',
        'HOST': '127.0.0.1',
        'PORT': '',
    }
}"""

# Map domain to an interface language that the domain should be pinned to.
# Leave as {} to prevent language pinning, in which case one domain can serve either Hebrew or English
DOMAIN_LANGUAGES = {
    "http://hebrew.example.org": "hebrew",
    "http://english.example.org": "english",
}


################ These are things you can change! ###########################################################################
#SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']

ALLOWED_HOSTS = ["localhost", "127.0.0.1","0.0.0.0"]

ADMINS = (
     ('Your Name', 'you@example.com'),
)
PINNED_IPCOUNTRY = "IL" #change if you want parashat hashavua to be diaspora.

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
""" These are some other examples of possible caches. more here: https://docs.djangoproject.com/en/1.11/topics/cache/"""
"""CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/home/ephraim/www/sefaria/django_cache/',
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/0", #The URI used to look like this "127.0.0.1:6379:0"
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            #"PASSWORD": "secretpassword", # Optional
        },
        "TIMEOUT": 60 * 60 * 24 * 30,
    }
}"""

SITE_PACKAGE = "sites.sefaria"







################ These are things you DO NOT NEED to touch unless you know what you are doing. ##############################
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']
OFFLINE = False
DOWN_FOR_MAINTENANCE = False
MAINTENANCE_MESSAGE = ""
GLOBAL_WARNING = False
GLOBAL_WARNING_MESSAGE = ""

# GLOBAL_INTERRUPTING_MESSAGE = None
"""
GLOBAL_INTERRUPTING_MESSAGE = {
    "name":       "messageName",
    "repetition": 1,
    "style":      "modal" # "modal" or "banner"
    "condition":  {"returning_only": True}
}
"""


MANAGERS = ADMINS

SECRET_KEY = 'insert your long random secret key here !'


EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Example using anymail, replaces block above
# EMAIL_BACKEND = 'anymail.backends.mandrill.EmailBackend'
# DEFAULT_FROM_EMAIL = "Sefaria <hello@sefaria.org>"
# ANYMAIL = {
#    "MANDRILL_API_KEY": "your api key",
# }

MONGO_HOST = "localhost"
MONGO_PORT = 27017
# Name of the MongoDB database to use.
if os.getenv('MONGO_DB_NAME'):
    SEFARIA_DB = os.getenv('MONGO_DB_NAME')
else:
    SEFARIA_DB = "sefaria-vecino"

# Leave user and password blank if not using Mongo Auth
SEFARIA_DB_USER = ''
SEFARIA_DB_PASSWORD = ''
APSCHEDULER_NAME = "apscheduler"

# ElasticSearch server
SEARCH_ADMIN = "http://localhost:9200"
SEARCH_INDEX_ON_SAVE = False  # Whether to send texts and source sheet to Search Host for indexing after save
SEARCH_INDEX_NAME_TEXT = 'text'  # name of the ElasticSearch index to use
SEARCH_INDEX_NAME_SHEET = 'sheet'

# Node Server
USE_NODE = False
NODE_HOST = "http://localhost:4040"
NODE_TIMEOUT = 10
# NODE_TIMEOUT_MONITOR = relative_to_abs_path("../log/forever/timeouts")

SEFARIA_DATA_PATH = '/path/to/your/Sefaria-Data' # used for Data
SEFARIA_EXPORT_PATH = '/path/to/your/Sefaria-Data/export' # used for exporting texts


# DafRoulette server
RTC_SERVER = '' # Root URL/IP of the server

GOOGLE_TAG_MANAGER_CODE = 'you tag manager code here'
GOOGLE_ANALYTICS_CODE = 'your google analytics code'
GOOGLE_MAPS_API_KEY = None  # currently used for shavuot map
MIXPANEL_CODE = 'you mixpanel code here'

AWS_ACCESS_KEY = None
AWS_SECRET_KEY = None
S3_BUCKET = "bucket-name"

# Integration with a NationBuilder list
NATIONBUILDER = False
NATIONBUILDER_SLUG = ""
NATIONBUILDER_TOKEN = ""
NATIONBUILDER_CLIENT_ID = ""
NATIONBUILDER_CLIENT_SECRET = ""

# Issue bans to Varnish on update.
USE_VARNISH = False
FRONT_END_URL = "http://localhost:8000"  # This one wants the http://
VARNISH_ADM_ADDR = "localhost:6082" # And this one doesn't
VARNISH_HOST = "localhost"
VARNISH_FRNT_PORT = 8040
VARNISH_SECRET = "/etc/varnish/secret"
# Use ESI for user box in header.
USE_VARNISH_ESI = False

# Prevent modification of Index records
DISABLE_INDEX_SAVE = False

# Caching with Cloudflare
CLOUDFLARE_ZONE = ""
CLOUDFLARE_EMAIL = ""
CLOUDFLARE_TOKEN = ""

# Multiserver
MULTISERVER_ENABLED = False
MULTISERVER_REDIS_SERVER = "127.0.0.1"
MULTISERVER_REDIS_PORT = 6379
MULTISERVER_REDIS_DB = 0
MULTISERVER_REDIS_EVENT_CHANNEL = "msync"   # Message queue on Redis
MULTISERVER_REDIS_CONFIRM_CHANNEL = "mconfirm"   # Message queue on Redis

# OAUTH these fields dont need to be filled in. they are only required for oauth2client to __init__ successfully
GOOGLE_OAUTH2_CLIENT_ID = ""
GOOGLE_OAUTH2_CLIENT_SECRET = ""
# This is the field that is actually used
GOOGLE_OAUTH2_CLIENT_SECRET_FILEPATH = ""

GOOGLE_APPLICATION_CREDENTIALS_FILEPATH = ""

GEOIP_DATABASE = 'data/geoip/GeoLiteCity.dat'
GEOIPV6_DATABASE = 'data/geoip/GeoLiteCityv6.dat'

PARTNER_GROUP_EMAIL_PATTERN_LOOKUP_FILE = None

# Simple JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=90),
    'ROTATE_REFRESH_TOKENS': True,
    'SIGNING_KEY': 'a signing key: at least 256 bits',
}

# Key which identifies the Sefaria app as opposed to a user
# using our API outside of the app. Mainly for registration
MOBILE_APP_KEY = "MOBILE_APP_KEY"

""" to use logging, in any module:
# import the logging library
import structlog

# Get an instance of a logger
logger = structlog.get_logger(__name__)

#log stuff
logger.critical()
logger.error()
logger.warning()
logger.info()
logger.debug()

if you are logging to a file, make sure the directory exists and is writeable by the server.
"""


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        "json_formatter": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
    },
    'handlers': {
        'default': {
            "class": "logging.StreamHandler",
            "formatter": "json_formatter",
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'propagate': False,
        },
        'django': {
            'handlers': ['default'],
            'propagate': False,
        },
        'django.request': {
            'handlers': ['default'],
            'propagate': False,
        },
    }
}

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.ExceptionPrettyPrinter(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=structlog.threadlocal.wrap_dict(dict),
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
