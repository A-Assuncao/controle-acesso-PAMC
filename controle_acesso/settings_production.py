"""
Configurações de produção para deploy na Vercel com Supabase.
"""
import os
import dj_database_url
from .settings import *

# Sobrescrever configurações para produção
DEBUG = os.getenv('DJANGO_DEBUG', 'False') == 'True'

# Hosts permitidos
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',')
if os.getenv('VERCEL_URL'):
    ALLOWED_HOSTS.append(os.getenv('VERCEL_URL'))
if os.getenv('VERCEL_BRANCH_URL'):
    ALLOWED_HOSTS.append(os.getenv('VERCEL_BRANCH_URL'))

# Adicionar domínio da Vercel
ALLOWED_HOSTS.extend([
    '.vercel.app',
    '.vercel.com',
])

# Configuração do banco de dados Supabase (PostgreSQL)
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

# Segurança
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = []
if os.getenv('VERCEL_URL'):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.getenv('VERCEL_URL')}")
if os.getenv('VERCEL_BRANCH_URL'):
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.getenv('VERCEL_BRANCH_URL')}")

# Adicionar domínios personalizados
custom_domains = os.getenv('CUSTOM_DOMAINS', '')
if custom_domains:
    for domain in custom_domains.split(','):
        domain = domain.strip()
        if domain:
            CSRF_TRUSTED_ORIGINS.append(f"https://{domain}")
            ALLOWED_HOSTS.append(domain)

# Arquivos estáticos
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging para produção: o filesystem da Vercel é somente leitura.
# Os logs devem ser enviados para stdout/stderr e consultados no painel da Vercel.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Não tente gravar logs no diretório da aplicação serverless.
LOG_DIR = None
DEBUG_LOG_FILE = None
ERROR_LOG_FILE = None
