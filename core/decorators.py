from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
import logging

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