"""
Views básicas do sistema de controle de acesso.

Responsável por:
- login_view: Login unificado (local + Canaimé)
- logout_view: Logout do sistema
- welcome: Página de boas-vindas
- home: Dashboard principal de produção
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone
import pytz

from core.authentication import CanaimeAuthBackend
from core.models import PerfilUsuario, RegistroDashboard, Servidor
from core.utils import calcular_plantao_atual


def login_view(request):
    """
    View de login unificada que tenta:
    1. Login local primeiro
    2. Se não encontrar usuário, tenta Canaimé
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not username or not password:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Por favor, preencha todos os campos.'
                })
            messages.error(request, 'Por favor, preencha todos os campos.')
            return render(request, 'core/login.html')
        
        # 1. PRIMEIRO: Tenta login local
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Login local bem-sucedido
            login(request, user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'redirect': True,
                    'redirect_url': reverse('home'),
                    'message': f'Bem-vindo de volta, {user.first_name or user.username}!'
                })
            
            messages.success(request, f'Bem-vindo de volta, {user.first_name or user.username}!')
            return redirect('home')
        
        # 2. SEGUNDO: Se login local falhou, verifica se usuário existe
        if User.objects.filter(username=username).exists():
            # Usuário existe mas senha está errada
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Senha incorreta.'
                })
            messages.error(request, 'Senha incorreta.')
            return render(request, 'core/login.html')
        
        # 3. TERCEIRO: Usuário não existe, tenta Canaimé
        try:
            canaime_backend = CanaimeAuthBackend()
            user_data = canaime_backend._authenticate_canaime(username, password)
            
            if user_data:
                # Sucesso no Canaimé, salva dados na sessão e mostra modal
                request.session['canaime_user_data'] = user_data
                request.session['canaime_credentials'] = {
                    'username': username,
                    'password': password
                }
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'show_modal': True,
                        'data': user_data
                    })
                
                # Fallback para não-AJAX (não deveria acontecer)
                return redirect('canaime_user_info')
            else:
                # Falha no Canaimé também
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Usuário ou senha incorretos. Verifique suas credenciais.'
                    })
                messages.error(request, 'Usuário ou senha incorretos. Verifique suas credenciais.')
                return render(request, 'core/login.html')
                
        except Exception as e:
            # Erro na conexão com Canaimé
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Erro de conexão. Tente novamente em alguns instantes.'
                })
            messages.error(request, 'Erro de conexão. Tente novamente em alguns instantes.')
            return render(request, 'core/login.html')
    
    # GET request
    return render(request, 'core/login.html')


def logout_view(request):
    """View de logout"""
    if request.user.is_authenticated:
        user_name = request.user.first_name or request.user.username
        logout(request)
        messages.success(request, f'Até logo, {user_name}! Você foi desconectado com sucesso.')
    return redirect('login')


@login_required
def welcome(request):
    """View para página de boas-vindas."""
    # Se o usuário precisa trocar a senha, redireciona direto para a página de troca
    try:
        if request.user.perfil.precisa_trocar_senha:
            return redirect('trocar_senha')
    except:
        pass
    
    # Verifica se o usuário já viu a página de boas-vindas nesta sessão
    if request.session.get('welcome_shown'):
        return redirect('home')
    
    # Marca que o usuário já viu a página de boas-vindas
    request.session['welcome_shown'] = True
    return render(request, 'core/welcome.html')


@login_required
def home(request):
    """
    View principal do dashboard de produção.
    
    Exibe:
    - Resumo do plantão atual
    - Estatísticas de entradas, saídas e pendentes
    - Lista de servidores ativos
    - Controles de acordo com permissões do usuário
    """
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    agora = timezone.localtime(timezone.now(), tz)
    
    # Atualiza a última visita do usuário (mantido para outras funcionalidades)
    request.session['ultima_visita_dashboard'] = agora.isoformat()
    
    # Obtém hora atual para uso em outros lugares
    hora_atual = agora.hour
    minuto_atual = agora.minute
    
    # Define mostrar_aviso como False para desativar o aviso de troca de plantão
    mostrar_aviso = False
    
    plantao_atual = calcular_plantao_atual()
    
    # Filtra registros do plantão atual
    registros = RegistroDashboard.objects.all().select_related('servidor', 'operador')
    
    # Calcula totais para os cards
    total_entradas = registros.filter(tipo_acesso='ENTRADA').count()  # Total de entradas
    total_saidas = registros.filter(data_hora_saida__isnull=False).count()  # Total de saídas normais
    total_pendentes = registros.filter(tipo_acesso='ENTRADA', saida_pendente=True).count()  # Entradas sem saída
    
    # Lista de servidores para os modais
    servidores = Servidor.objects.filter(ativo=True).order_by('nome')
    
    # Verifica permissões do usuário
    try:
        perfil = request.user.perfil
        pode_registrar = perfil.pode_registrar_acesso()
        pode_excluir = perfil.pode_excluir_registros()
        pode_limpar = perfil.pode_limpar_dashboard()
        pode_saida_def = perfil.pode_saida_definitiva()
        tipo_usuario = perfil.get_tipo_usuario_display()
    except:
        # Se não tem perfil, assume operador completo
        pode_registrar = True
        pode_excluir = True
        pode_limpar = True
        pode_saida_def = True
        tipo_usuario = 'Operador'

    context = {
        'plantao_atual': plantao_atual,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_pendentes': total_pendentes,
        'servidores': servidores,
        'mostrar_aviso_plantao': mostrar_aviso,
        'hora_atual': f"{hora_atual:02d}:{minuto_atual:02d}",
        'is_superuser': request.user.is_superuser,
        'pode_registrar_acesso': pode_registrar,
        'pode_excluir_registros': pode_excluir,
        'pode_limpar_dashboard': pode_limpar,
        'pode_saida_definitiva': pode_saida_def,
        'tipo_usuario': tipo_usuario,
    }
    
    return render(request, 'core/home.html', context)


def trocar_senha_view(request):
    """View para trocar senha"""
    return render(request, 'core/trocar_senha.html')


def tutoriais_view(request):
    """View de tutoriais"""
    return render(request, 'core/tutoriais.html') 