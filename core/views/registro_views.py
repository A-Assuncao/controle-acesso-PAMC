"""
Views de gerenciamento de registros de acesso (produção).

Responsável por:
- Criação de registros de acesso
- Listagem e detalhes dos registros
- Edição e exclusão de registros
- Saída de servidores
- Limpeza do dashboard
- Exportação para Excel
- Relatório de faltas e ISVs
"""

import pytz
import logging
from datetime import datetime
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone

from ..models import RegistroDashboard, RegistroAcesso, Servidor
from ..decorators import (
    pode_registrar_acesso, pode_excluir_registros, 
    pode_saida_definitiva, pode_limpar_dashboard
)
from ..utils import (
    processar_registro_acesso_helper, exportar_excel_helper,
    saida_definitiva_helper, limpar_dashboard_helper
)

logger = logging.getLogger(__name__)


@login_required
@pode_registrar_acesso
def registro_acesso_create(request):
    """Cria um novo registro de acesso."""
    if request.method == 'POST':
        sucesso, mensagem, redirect_url = processar_registro_acesso_helper(request, is_treinamento=False)
        
        if sucesso:
            messages.success(request, mensagem)
        else:
            messages.error(request, mensagem)
        
        return redirect(redirect_url)
    
    return redirect('home')


@login_required
def registro_manual_create(request):
    """Cria um registro manual de entrada/saída."""
    if request.method == 'POST':
        servidor_id = request.POST.get('servidor')
        tipo_acesso = request.POST.get('tipo_acesso')
        data_hora = request.POST.get('data_hora_manual')
        justificativa = request.POST.get('justificativa')
        observacao = request.POST.get('observacao', '')
        isv = request.POST.get('isv') == 'on'
        
        servidor = get_object_or_404(Servidor, id=servidor_id)
        
        # Cria o registro manual
        registro = RegistroAcesso.objects.create(
            servidor=servidor,
            operador=request.user,
            tipo_acesso=tipo_acesso,
            data_hora_manual=data_hora,
            justificativa=justificativa,
            observacao=observacao,
            isv=isv
        )
        
        # Atualiza saída pendente
        if tipo_acesso == 'ENTRADA':
            registro.saida_pendente = True
            registro.save()
        elif tipo_acesso == 'SAIDA':
            ultima_entrada = RegistroAcesso.objects.filter(
                servidor=servidor,
                tipo_acesso='ENTRADA',
                saida_pendente=True
            ).first()
            if ultima_entrada:
                ultima_entrada.saida_pendente = False
                ultima_entrada.save()
        
        messages.success(request, f'{tipo_acesso.title()} manual registrada com sucesso!')
        return redirect('home')
    
    return redirect('home')


@login_required
def registros_plantao(request):
    """API que retorna todos os registros do dashboard em JSON."""
    # Obtém todos os registros do dashboard
    registros = RegistroDashboard.objects.all().select_related('servidor', 'operador', 'operador_saida').order_by('data_hora', 'id')
    
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    
    data = []
    for registro in registros:
        # Converte os horários para UTC-4
        data_hora = timezone.localtime(registro.data_hora, tz)
        data_hora_saida = timezone.localtime(registro.data_hora_saida, tz) if registro.data_hora_saida else None
        
        # Se for uma entrada normal
        if registro.tipo_acesso == 'ENTRADA':
            data.append({
                'id': registro.id,
                'servidor_nome': registro.servidor.nome,
                'servidor_documento': registro.servidor.numero_documento,
                'setor': registro.servidor.setor or '-',
                'veiculo': registro.veiculo or '-',
                'isv': registro.isv,
                'hora_entrada': data_hora.strftime('%d/%m/%Y %H:%M'),
                'hora_saida': data_hora_saida.strftime('%d/%m/%Y %H:%M') if data_hora_saida else None,
                'tipo_acesso': registro.tipo_acesso,
                'saida_pendente': registro.saida_pendente
            })
        # Se for uma saída definitiva
        elif registro.tipo_acesso == 'SAIDA':
            data.append({
                'id': registro.id,
                'servidor_nome': f"Egresso: {registro.servidor.nome}" if not registro.servidor.nome.startswith('Egresso:') else registro.servidor.nome,
                'servidor_documento': registro.servidor.numero_documento,
                'setor': registro.setor or '-',
                'veiculo': registro.veiculo or '-',
                'isv': registro.isv,
                'hora_entrada': '-',
                'hora_saida': data_hora.strftime('%d/%m/%Y %H:%M'),
                'tipo_acesso': registro.tipo_acesso,
                'saida_pendente': False
            })
    
    return JsonResponse(data, safe=False)


@login_required
def registro_detalhe(request, registro_id):
    """Retorna os detalhes de um registro para edição."""
    registro = get_object_or_404(RegistroDashboard, id=registro_id)
    tz = pytz.timezone('America/Manaus')
    
    # Converte os horários para UTC-4
    data_hora = timezone.localtime(registro.data_hora, tz)
    data_hora_saida = timezone.localtime(registro.data_hora_saida, tz) if registro.data_hora_saida else None
    
    # Formata as datas para o formato ISO e BR
    data_iso = data_hora.strftime('%Y-%m-%d') if data_hora else ''
    data_saida_iso = data_hora_saida.strftime('%Y-%m-%d') if data_hora_saida else ''
    
    return JsonResponse({
        'data_hora': data_hora.isoformat(),
        'data': data_iso,  # Data no formato YYYY-MM-DD
        'data_saida': data_saida_iso,  # Data de saída no formato YYYY-MM-DD
        'hora_entrada': data_hora.strftime('%H:%M') if registro.tipo_acesso == 'ENTRADA' else '-',
        'hora_saida': data_hora_saida.strftime('%H:%M') if data_hora_saida else '-',
        'tipo_acesso': registro.tipo_acesso,
        'servidor_nome': registro.servidor.nome,
        'saida_pendente': registro.saida_pendente
    })


@login_required
def registro_acesso_update(request, registro_id):
    """
    Atualiza um registro de acesso existente.
    
    Esta view é complexa pois permite edição completa de data/hora de entrada e saída.
    Por ser muito extensa (~200 linhas), mantém a implementação original.
    """
    # Importa a view original para manter funcionalidade completa
    from ..views_original import registro_acesso_update as original_update
    return original_update(request, registro_id)


@login_required
@pode_excluir_registros
def excluir_registro(request, registro_id):
    """Exclui um registro do dashboard mantendo histórico."""
    if request.method == 'POST':
        try:
            # Obtém o registro do dashboard
            registro_dashboard = get_object_or_404(RegistroDashboard, id=registro_id)
            registro_historico = registro_dashboard.registro_historico
            justificativa = request.POST.get('justificativa')
            
            if not justificativa:
                return JsonResponse({
                    'status': 'error',
                    'message': 'É necessário informar uma justificativa para excluir o registro.'
                }, status=400)
            
            # Cria uma cópia do registro com status EXCLUIDO para o histórico
            registro_excluido = RegistroAcesso.objects.create(
                servidor=registro_historico.servidor,
                operador=registro_historico.operador,
                tipo_acesso=registro_historico.tipo_acesso,
                observacao=registro_historico.observacao,
                observacao_saida=registro_historico.observacao_saida,
                isv=registro_historico.isv,
                veiculo=registro_historico.veiculo,
                setor=registro_historico.setor,
                data_hora=registro_historico.data_hora,
                data_hora_saida=registro_historico.data_hora_saida,
                operador_saida=registro_historico.operador_saida,
                registro_original=registro_historico,
                status_alteracao='EXCLUIDO',
                data_hora_alteracao=timezone.now(),
                justificativa=justificativa,
                saida_pendente=registro_historico.saida_pendente
            )
            
            # Remove o registro do dashboard
            registro_dashboard.delete()
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)


@login_required
def exportar_excel(request):
    """Exporta os registros do dashboard para Excel."""
    registros = RegistroDashboard.objects.all().select_related(
        'servidor', 'operador', 'operador_saida'
    ).order_by('data_hora', 'id')
    
    return exportar_excel_helper(registros, 'dashboard_controle_acesso', is_treinamento=False)


@login_required
@pode_saida_definitiva
def saida_definitiva(request):
    """Registra saída definitiva (egresso)."""
    if request.method == 'POST':
        resultado = saida_definitiva_helper(request, is_treinamento=False)
        return JsonResponse(resultado)
            
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido'
    })


@login_required
@pode_limpar_dashboard
def limpar_dashboard(request):
    """Limpa todos os registros do dashboard exceto os que têm saída pendente."""
    if request.method == 'POST':
        resultado = limpar_dashboard_helper(request, is_treinamento=False)
        
        # Adiciona código de status HTTP baseado no resultado
        if resultado['status'] == 'error':
            if 'Senha não fornecida' in resultado['message']:
                status_code = 400
            elif 'Senha incorreta' in resultado['message']:
                status_code = 401
            else:
                status_code = 500
            return JsonResponse(resultado, status=status_code)
        
        return JsonResponse(resultado)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido. Use POST para esta operação.'
    }, status=405)


@login_required
def registrar_saida(request, registro_id):
    """Registra a saída diretamente para um registro pendente."""
    if request.method == 'POST':
        try:
            # Obtém o registro do dashboard
            registro_dashboard = get_object_or_404(RegistroDashboard, id=registro_id)
            
            # Verifica se o registro está pendente
            if not registro_dashboard.saida_pendente:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Este registro não está pendente de saída.'
                }, status=400)
            
            # Define o timezone UTC-4
            tz = pytz.timezone('America/Manaus')
            agora = timezone.now()
            
            # Atualiza o registro histórico
            registro_historico = registro_dashboard.registro_historico
            registro_historico.data_hora_saida = agora
            registro_historico.operador_saida = request.user
            registro_historico.saida_pendente = False
            registro_historico.save()
            
            # Atualiza o registro no dashboard
            registro_dashboard.data_hora_saida = agora
            registro_dashboard.operador_saida = request.user
            registro_dashboard.saida_pendente = False
            registro_dashboard.save()
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)


@login_required
def retirar_faltas(request):
    """
    View para listar e exportar as faltas do plantão atual.
    
    Esta view é extremamente complexa (~250 linhas) pois processa:
    - Servidores faltosos do plantão atual
    - ISVs presentes 
    - Permutas/Reposição de hora
    - Exportação em PDF
    
    Por ser muito extensa, mantém a implementação original.
    """
    # Importa a view original para manter funcionalidade completa
    from ..views_original import retirar_faltas as original_retirar_faltas
    return original_retirar_faltas(request) 