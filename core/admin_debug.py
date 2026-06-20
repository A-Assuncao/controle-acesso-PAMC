"""Ferramentas de debug para o admin Django.

Views customizadas (acessiveis apenas a superuser) que ajudam a
investigar problemas em producao:

- debug_sql_queries: mostra as queries SQL executadas em uma pagina admin
- debug_sessao: dump da sessao Django (chaves, valores serializaveis)
- debug_smtp: testa o envio de email com a configuracao atual
- debug_status: status geral do sistema (versao Django, Python, conexao DB, etc)

Todas exigem is_superuser. Nao use em producao sem HTTPS.
"""

import json
import platform
import sys

from django import get_version
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.db import connection
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils import timezone


def _superuser_required(view_func):
    """Decorator que exige is_superuser - mesmo padrao do admin."""
    decorated = user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser,
        login_url='/admin/login/',
    )(view_func)
    return decorated


@_superuser_required
def debug_index(request):
    """Pagina de entrada do debug - lista as ferramentas."""
    return render(request, 'admin/debug/index.html', {
        'title': 'Debug',
        'tools': [
            {'name': 'SQL Queries', 'url': 'debug_sql_queries', 'icon': 'bi-database', 'descricao': 'Ver queries SQL executadas em uma pagina admin'},
            {'name': 'Sessao Django', 'url': 'debug_sessao', 'icon': 'bi-key', 'descricao': 'Inspecionar todos os dados armazenados na sessao'},
            {'name': 'Testar SMTP', 'url': 'debug_smtp', 'icon': 'bi-envelope', 'descricao': 'Enviar email de teste com a configuracao atual'},
            {'name': 'Status do sistema', 'url': 'debug_status', 'icon': 'bi-info-circle', 'descricao': 'Versao Django/Python, conexao DB, etc'},
        ],
    })


@_superuser_required
def debug_sql_queries(request):
    """Mostra as queries SQL executadas no request atual.

    Acessivel via /admin/debug/sql/ - executa um GET e captura
    todas as queries disparadas pelo Django ORM.
    """
    queries = []

    # Habilita debug de SQL
    from django.db import reset_queries
    from django.conf import settings
    if not settings.DEBUG:
        return HttpResponse(
            '<h1>SQL debug desabilitado</h1>'
            '<p>Para usar, habilite DEBUG=True em settings.py.</p>',
            content_type='text/html',
        )

    reset_queries()

    # Executa queries de exemplo (3 contagens simples)
    from core.models import Servidor, RegistroAcesso, LogAuditoria, VideoTutorial
    from django.contrib.auth.models import User
    Servidor.objects.count()
    RegistroAcesso.objects.count()
    LogAuditoria.objects.count()
    VideoTutorial.objects.count()
    User.objects.count()

    # Pega as queries capturadas
    queries = connection.queries

    total_time = sum(float(q.get('time', 0)) for q in queries)
    return render(request, 'admin/debug/sql_queries.html', {
        'title': 'SQL Queries executadas',
        'queries': queries,
        'total_time': total_time,
        'total_count': len(queries),
    })


@_superuser_required
def debug_sessao(request):
    """Inspeciona a sessao Django do usuario atual.

    Mostra todas as chaves, valores serializados (JSON quando possivel),
    tamanho aproximado em bytes.
    """
    sess = request.session
    items = []
    total_size = 0
    for key, value in sess.items():
        try:
            # Tenta serializar como JSON para exibicao legivel
            value_repr = json.dumps(value, ensure_ascii=False, default=str)
            value_display = value_repr
        except (TypeError, ValueError):
            value_display = repr(value)
        size = len(str(value_display).encode('utf-8'))
        total_size += size
        items.append({
            'key': key,
            'value': value_display,
            'size': size,
        })

    return render(request, 'admin/debug/sessao.html', {
        'title': 'Sessao Django',
        'items': items,
        'total_size': total_size,
    })


@_superuser_required
def debug_smtp(request):
    """Tenta enviar email de teste com a configuracao SMTP atual.

    GET: mostra form com email de destino
    POST: envia email de teste e mostra resultado
    """
    if request.method == 'POST':
        destino = request.POST.get('destino', '').strip()
        if not destino:
            messages.error(request, 'Informe um email de destino.')
            return HttpResponseRedirect(reverse('admin:debug_smtp'))

        try:
            send_mail(
                subject='[PAMC] Teste de SMTP via admin',
                message=(
                    f'Este email foi enviado pelo painel admin em {timezone.now()}.\n\n'
                    f'Usuario: {request.user.username}\n'
                    f'Destino: {destino}\n\n'
                    'Se voce recebeu isto, o SMTP esta funcionando.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com',
                recipient_list=[destino],
                fail_silently=False,
            )
            messages.success(request, f'Email enviado para {destino}. Verifique a caixa de entrada.')
        except Exception as e:
            messages.error(request, f'Erro ao enviar: {e}')

        return HttpResponseRedirect(reverse('admin:debug_smtp'))

    return render(request, 'admin/debug/smtp.html', {
        'title': 'Testar SMTP',
        'default_from': getattr(settings, 'DEFAULT_FROM_EMAIL', 'N/A'),
        'email_host': getattr(settings, 'EMAIL_HOST', 'N/A'),
        'email_port': getattr(settings, 'EMAIL_PORT', 'N/A'),
        'email_user': getattr(settings, 'EMAIL_HOST_USER', 'N/A'),
        'email_use_tls': getattr(settings, 'EMAIL_USE_TLS', 'N/A'),
    })


@_superuser_required
def debug_status(request):
    """Status geral do sistema: versao Django, Python, conexao DB."""
    from core.models import Servidor, RegistroAcesso, LogAuditoria, VideoTutorial
    from django.contrib.auth.models import User

    # Testa conexao com DB
    db_ok = False
    db_error = None
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        db_ok = True
    except Exception as e:
        db_error = str(e)

    return render(request, 'admin/debug/status.html', {
        'title': 'Status do sistema',
        'django_version': get_version(),
        'python_version': f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}',
        'platform': platform.platform(),
        'debug_mode': settings.DEBUG,
        'database_engine': settings.DATABASES['default']['ENGINE'],
        'database_name': settings.DATABASES['default']['NAME'],
        'db_ok': db_ok,
        'db_error': db_error,
        'time_zone': settings.TIME_ZONE,
        'language': settings.LANGUAGE_CODE,
        'contagens': {
            'servidores': Servidor.objects.count(),
            'registros': RegistroAcesso.objects.count(),
            'logs': LogAuditoria.objects.count(),
            'tutoriais': VideoTutorial.objects.count(),
            'usuarios': User.objects.count(),
        },
    })


def get_debug_urls():
    """Retorna as URLs para registrar no admin.site.get_urls()."""
    return [
        path('debug/', debug_index, name='debug_index'),
        path('debug/sql/', debug_sql_queries, name='debug_sql_queries'),
        path('debug/sessao/', debug_sessao, name='debug_sessao'),
        path('debug/smtp/', debug_smtp, name='debug_smtp'),
        path('debug/status/', debug_status, name='debug_status'),
    ]