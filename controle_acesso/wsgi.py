# -*- coding: utf-8 -*-
"""
WSGI config for controle_acesso project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'controle_acesso.settings')

# Get the Django WSGI application
application = get_wsgi_application()

# Wrap the WSGI application for Vercel
app = application