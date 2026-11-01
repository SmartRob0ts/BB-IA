"""WSGI config for SmartRobots BB IA."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartrobots.settings")
application = get_wsgi_application()
