"""
Views para autenticação Canaimé.

Implementa login alternativo via Canaimé para testes.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.models import User
from core.authentication import CanaimeAuthBackend
import requests
from django.urls import reverse
import json

logger = logging.getLogger(__name__)


@csrf_protect
@never_cache
def canaime_login(request):
    """
    View de login experimental usando autenticação Canaimé
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not username or not password:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Por favor, preencha todos os campos.'})
            messages.error(request, 'Por favor, preencha todos os campos.')
            return render(request, 'core/canaime_login.html')
        
        try:
            # Tenta autenticar no Canaimé (mas não cria usuário ainda)
            backend = CanaimeAuthBackend()
            canaime_data = backend._authenticate_canaime(username, password)
            
            if canaime_data:
                # Salva dados na sessão para usar na confirmação
                request.session['canaime_pending'] = {
                    'username': username,
                    'nome_completo': canaime_data['nome_completo'],
                    'first_name': canaime_data['first_name'],
                    'last_name': canaime_data['last_name'],
                    'foto_url': canaime_data.get('foto_url', ''),
                }
                
                # Força salvar a sessão
                request.session.save()
                
                logger.info(f"Dados Canaimé obtidos para {username}, enviando para modal")
                
                # Se for AJAX, retorna dados para o modal
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'show_modal': True,
                        'data': {
                            'username': username,
                            'first_name': canaime_data['first_name'],
                            'last_name': canaime_data['last_name'],
                            'foto_url': canaime_data.get('foto_url', ''),
                        }
                    })
                else:
                    # Fallback para não-AJAX
                    return redirect('canaime_user_info')
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'Falha na autenticação. Verifique suas credenciais.'})
                messages.error(request, 'Falha na autenticação. Verifique suas credenciais.')
                logger.warning(f"Falha na autenticação Canaimé para: {username}")
                
        except Exception as e:
            error_msg = f'Erro interno: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
            logger.error(f"Erro na autenticação Canaimé: {str(e)}")
    
    return render(request, 'core/canaime_login.html')


@csrf_protect
@never_cache
def canaime_user_info(request):
    """
    Processa confirmação de dados via AJAX ou formulário normal
    """
    logger.info(f"=== canaime_user_info chamada ===")
    logger.info(f"Método: {request.method}")
    logger.info(f"AJAX: {request.headers.get('X-Requested-With') == 'XMLHttpRequest'}")
    logger.info(f"Dados POST: {dict(request.POST)}")
    logger.info(f"Sessão: {dict(request.session)}")
    
    # Verifica se há dados pendentes na sessão (compatível com login unificado)
    canaime_data = request.session.get('canaime_user_data') or request.session.get('canaime_pending')
    if not canaime_data:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Sessão expirada. Faça login novamente.'})
        messages.error(request, 'Sessão expirada. Faça login novamente.')
        return redirect('login')
    
    if request.method == 'POST':
        # Usuário confirmou/editou os dados
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        
        if not first_name or not last_name:
            error_msg = 'Por favor, preencha o nome e sobrenome.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
            return render(request, 'core/canaime_user_info.html', {
                'username': canaime_data['username'],
                'first_name': first_name,
                'last_name': last_name,
                'foto_url': canaime_data.get('foto_url', ''),
            })
        
        try:
            # Atualiza os dados com as correções do usuário
            canaime_data['first_name'] = first_name
            canaime_data['last_name'] = last_name
            canaime_data['nome_completo'] = f"{first_name} {last_name}"
            
            # Recupera a senha da sessão
            canaime_credentials = request.session.get('canaime_credentials', {})
            password = canaime_credentials.get('password')
            
            # Agora cria/atualiza o usuário com os dados confirmados
            backend = CanaimeAuthBackend()
            user = backend._create_or_update_user(canaime_data['username'], canaime_data, password)
            
            if user:
                # Faz login do usuário automaticamente
                login(request, user)
                
                # Limpa dados da sessão (compatível com login unificado)
                if 'canaime_user_data' in request.session:
                    del request.session['canaime_user_data']
                if 'canaime_credentials' in request.session:
                    del request.session['canaime_credentials']
                if 'canaime_pending' in request.session:
                    del request.session['canaime_pending']
                
                success_msg = f'Login realizado com sucesso! Bem-vindo, {user.get_full_name()}!'
                logger.info(f"Login Canaimé confirmado e bem-sucedido: {user.username}")
                
                # Se for AJAX, retorna sucesso para redirecionar
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'redirect': True,
                        'redirect_url': reverse('home'),
                        'message': success_msg
                    })
                else:
                    messages.success(request, success_msg)
                    return redirect('home')
            else:
                error_msg = 'Erro ao criar usuário. Tente novamente.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': error_msg})
                messages.error(request, error_msg)
                
        except Exception as e:
            error_msg = f'Erro interno: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': error_msg})
            messages.error(request, error_msg)
            logger.error(f"Erro ao criar usuário Canaimé: {str(e)}")
    
    # Se não for AJAX, mostra tela normal (fallback)
    return render(request, 'core/canaime_user_info.html', {
        'username': canaime_data['username'],
        'first_name': canaime_data['first_name'],
        'last_name': canaime_data['last_name'],
        'foto_url': canaime_data.get('foto_url', ''),
    })


def test_canaime_connection(request):
    """
    Testa conectividade com o Canaimé
    """
    try:
        response = requests.get(
            "https://canaime.com.br/sgp2rr/login/login_principal.php",
            timeout=10,
            verify=False
        )
        
        if response.status_code == 200:
            return JsonResponse({
                'status': 'success',
                'message': 'Conexão com Canaimé OK',
                'response_size': len(response.text)
            })
        else:
            return JsonResponse({
                'status': 'error', 
                'message': f'Canaimé retornou status {response.status_code}'
            })
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro de conexão: {str(e)}'
        })


def logout_canaime(request):
    """
    Logout específico para usuários Canaimé
    """
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'Logout realizado com sucesso!')
    return redirect('canaime_login') 