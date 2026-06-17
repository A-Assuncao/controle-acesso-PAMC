from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
import logging
import traceback

from core.models import PerfilUsuario

logger = logging.getLogger('core')

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'Você não tem permissão para acessar esta página. Entre em contato com um administrador.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def _perfil_or_none(user):
    """Retorna o PerfilUsuario ou None se ainda não foi criado."""
    try:
        return user.perfil
    except PerfilUsuario.DoesNotExist:
        return None

def pode_registrar_acesso(view_func):
    """
    Decorator para verificar se o usuário pode registrar acessos no ambiente de produção.
    Usuários sem perfil são tratados como OPERADOR (acesso total).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        perfil = _perfil_or_none(request.user)
        if perfil is not None and not perfil.pode_registrar_acesso():
            messages.error(request, 'Você não tem permissão para registrar acessos. Apenas visualização é permitida.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def pode_excluir_registros(view_func):
    """
    Decorator para verificar se o usuário pode excluir registros.
    Usuários sem perfil são tratados como OPERADOR (podem excluir).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        perfil = _perfil_or_none(request.user)
        if perfil is not None and not perfil.pode_excluir_registros():
            messages.error(request, 'Você não tem permissão para excluir registros.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def pode_gerenciar_servidores(view_func):
    """
    Decorator para verificar se o usuário pode gerenciar servidores.
    Usuários sem perfil são tratados como OPERADOR (podem gerenciar).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        perfil = _perfil_or_none(request.user)
        if perfil is not None and not perfil.pode_gerenciar_servidores():
            messages.error(request, 'Você não tem permissão para gerenciar servidores.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def pode_limpar_dashboard(view_func):
    """
    Decorator para verificar se o usuário pode limpar o dashboard.
    Usuários sem perfil são tratados como OPERADOR (podem limpar).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        perfil = _perfil_or_none(request.user)
        if perfil is not None and not perfil.pode_limpar_dashboard():
            messages.error(request, 'Você não tem permissão para limpar o dashboard.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def pode_saida_definitiva(view_func):
    """
    Decorator para verificar se o usuário pode registrar saída definitiva.
    Usuários sem perfil são tratados como OPERADOR (podem registrar).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        perfil = _perfil_or_none(request.user)
        if perfil is not None and not perfil.pode_saida_definitiva():
            messages.error(request, 'Você não tem permissão para registrar saída definitiva.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def log_errors(view_func):
    """
    Decorator para capturar e logar erros em views específicas
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            # Captura informações detalhadas do erro
            tb = traceback.format_exc()
            
            # Informações da requisição
            request_info = {
                'view': view_func.__name__,
                'method': request.method,
                'url': request.get_full_path(),
                'user': getattr(request.user, 'username', 'Anônimo') if hasattr(request, 'user') else 'Anônimo',
                'ip': request.META.get('REMOTE_ADDR', 'Desconhecido'),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'Desconhecido'),
                'args': str(args),
                'kwargs': str(kwargs),
            }
            
            # Captura dados POST se existirem (sem senhas)
            post_data = {}
            if request.method == 'POST':
                for key, value in request.POST.items():
                    if 'password' not in key.lower() and 'senha' not in key.lower():
                        post_data[key] = value
                    else:
                        post_data[key] = '[HIDDEN]'
            
            # Log detalhado do erro
            logger.error(
                f"ERRO NA VIEW '{view_func.__name__}':\n"
                f"Tipo: {type(e).__name__}\n"
                f"Mensagem: {str(e)}\n"
                f"URL: {request_info['url']}\n"
                f"Método: {request_info['method']}\n"
                f"Usuário: {request_info['user']}\n"
                f"IP: {request_info['ip']}\n"
                f"Args: {request_info['args']}\n"
                f"Kwargs: {request_info['kwargs']}\n"
                f"POST Data: {post_data}\n"
                f"Traceback:\n{tb}"
            )
            
            # Re-levanta a exceção para que seja processada normalmente
            raise
    
    return _wrapped_view 