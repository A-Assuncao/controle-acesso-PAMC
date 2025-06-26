"""
Views básicas do sistema de controle de acesso.

Responsável por:
- welcome: Página de boas-vindas
- home: Dashboard principal de produção
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
import pytz

from ..models import RegistroDashboard, Servidor
from ..utils import calcular_plantao_atual


@login_required
def welcome(request):
    """View para página de boas-vindas."""
    return render(request, 'core/welcome.html')
    
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