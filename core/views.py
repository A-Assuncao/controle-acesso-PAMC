from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, DateTimeField, Subquery, OuterRef, Count
from django.utils import timezone
from datetime import datetime, timedelta, date
import pandas as pd
from .models import RegistroAcesso, LogAuditoria, Servidor, RegistroDashboard, RegistroAcessoTreinamento, VideoTutorial, ServidorTreinamento, PerfilUsuario
from .forms import RegistroAcessoForm, ServidorForm
from .utils import calcular_plantao_atual, determinar_tipo_acesso, verificar_plantao_servidor, verificar_saida_pendente
from .decorators import admin_required
from django.contrib.auth.models import User
import json
import csv
import pytz
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from openpyxl.utils import get_column_letter
import random
import logging
import re
import io
import string

# Configuração do logger
logger = logging.getLogger(__name__)

def is_staff(user):
    return user.is_staff

@login_required
def welcome(request):
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
    
    context = {
        'plantao_atual': plantao_atual,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_pendentes': total_pendentes,
        'servidores': servidores,
        'mostrar_aviso_plantao': mostrar_aviso,
        'hora_atual': f"{hora_atual:02d}:{minuto_atual:02d}"
    }
    return render(request, 'core/home.html', context)

@login_required
def servidor_list(request):
    query = request.GET.get('q')
    servidores = Servidor.objects.all().order_by('nome')
    
    if query:
        print(f"Busca realizada com o termo: '{query}'")
        servidores = servidores.filter(
            Q(nome__icontains=query) |
            Q(numero_documento__icontains=query) |
            Q(setor__icontains=query)
        )
        print(f"Resultados encontrados: {servidores.count()}")
    
    return render(request, 'core/servidor_list.html', {'servidores': servidores})

@login_required
def servidor_create(request):
    if request.method == 'POST':
        form = ServidorForm(request.POST)
        if form.is_valid():
            servidor = form.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='CRIACAO',
                modelo='Servidor',
                objeto_id=servidor.id,
                detalhes=f'Criação do servidor {servidor.nome}'
            )
            messages.success(request, 'Servidor cadastrado com sucesso!')
            return redirect('servidor_list')
    else:
        form = ServidorForm()
    return render(request, 'core/servidor_form.html', {'form': form})

@login_required
def servidor_update(request, pk):
    servidor = get_object_or_404(Servidor, pk=pk)
    
    if request.method == 'POST':
        form = ServidorForm(request.POST, instance=servidor)
        if form.is_valid():
            servidor = form.save()
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EDICAO',
                modelo='Servidor',
                objeto_id=servidor.id,
                detalhes=f'Edição de servidor: {servidor.nome}'
            )
            messages.success(request, 'Servidor atualizado com sucesso!')
            return redirect('servidor_list')
    else:
        form = ServidorForm(instance=servidor)
    
    return render(request, 'core/servidor_form.html', {'form': form})

@login_required
def buscar_servidor(request):
    query = request.GET.get('q', '')
    if len(query) >= 2:  # Alterado de 3 para 2
        servidores = Servidor.objects.filter(
            Q(nome__icontains=query) |
            Q(numero_documento__icontains=query),
            ativo=True
        ).values('id', 'nome', 'numero_documento', 'setor')
        
        # Formata os resultados para o autocomplete
        resultados = []
        for servidor in servidores:
            resultados.append({
                'id': servidor['id'],
                'nome': servidor['nome'],
                'numero_documento': servidor['numero_documento'],
                'setor': servidor['setor'] or '-'
            })
        return JsonResponse(resultados, safe=False)
    return JsonResponse([], safe=False)

@login_required
def registro_acesso_create(request):
    if request.method == 'POST':
        servidor_id = request.POST.get('servidor')
        tipo_acesso = request.POST.get('tipo_acesso')
        observacao = request.POST.get('observacao', '')
        isv = request.POST.get('isv') == 'on'
        
        servidor = get_object_or_404(Servidor, id=servidor_id)
        plantao_atual = calcular_plantao_atual()
        
        # Verifica se já existe uma entrada sem saída
        entrada_pendente = RegistroDashboard.objects.filter(
            servidor=servidor,
            saida_pendente=True
        ).exists()
        
        if tipo_acesso == 'ENTRADA':
            if entrada_pendente:
                messages.error(request, 'Este servidor já possui uma entrada sem saída registrada. Registre a saída antes de fazer uma nova entrada.')
                return redirect('home')
            
            # Cria um novo registro no histórico
            registro_historico = RegistroAcesso.objects.create(
                servidor=servidor,
                operador=request.user,
                tipo_acesso='ENTRADA',
                observacao=observacao,
                isv=isv,
                veiculo=servidor.veiculo,
                setor=servidor.setor,
                saida_pendente=True,
                status_alteracao='ORIGINAL',
                data_hora=timezone.now()
            )
            
            # Cria um novo registro no dashboard
            RegistroDashboard.objects.create(
                servidor=servidor,
                operador=request.user,
                tipo_acesso='ENTRADA',
                isv=isv,
                veiculo=servidor.veiculo,
                setor=servidor.setor,
                data_hora=registro_historico.data_hora,
                saida_pendente=True,
                registro_historico=registro_historico
            )
            
            messages.success(request, 'Entrada registrada com sucesso!')
            return redirect('home')
            
        elif tipo_acesso == 'SAIDA':
            if not entrada_pendente:
                messages.error(request, 'Não foi encontrada uma entrada sem saída para este servidor. Registre uma entrada primeiro.')
                return redirect('home')
            
            # Procura a última entrada sem saída no dashboard
            ultima_entrada_dashboard = RegistroDashboard.objects.filter(
                servidor=servidor,
                saida_pendente=True
            ).first()
            
            # Atualiza o registro histórico existente
            registro_historico = ultima_entrada_dashboard.registro_historico
            registro_historico.data_hora_saida = timezone.now()
            registro_historico.operador_saida = request.user
            registro_historico.observacao_saida = observacao
            registro_historico.saida_pendente = False
            registro_historico.save()
            
            # Atualiza o registro no dashboard
            ultima_entrada_dashboard.data_hora_saida = registro_historico.data_hora_saida
            ultima_entrada_dashboard.operador_saida = request.user
            ultima_entrada_dashboard.saida_pendente = False
            ultima_entrada_dashboard.save()
            
            messages.success(request, 'Saída registrada com sucesso!')
            return redirect('home')
    
    return redirect('home')

@login_required
def registro_manual_create(request):
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
    Permite a edição de data e hora de entrada e saída por qualquer usuário.
    """
    logger.info(f"Iniciando atualização do registro ID={registro_id}")
    
    try:
        # Tenta localizar o registro no banco de dados
        registro = RegistroAcesso.objects.get(id=registro_id)
        logger.info(f"Registro encontrado: {registro}")
        
        # Para GET, retorna os detalhes do registro em JSON para AJAX
        if request.method == 'GET':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Prepara as datas em formato legível
                data_hora = None
                data_hora_saida = None
                
                if registro.entrada:
                    data_hora = registro.entrada.strftime('%Y-%m-%dT%H:%M')
                    
                if registro.saida:
                    data_hora_saida = registro.saida.strftime('%Y-%m-%dT%H:%M')
                    
                data = {
                    'id': registro.id,
                    'servidor_id': registro.servidor.id,
                    'servidor_nome': registro.servidor.nome,
                    'servidor_documento': registro.servidor.numero_documento,
                    'data_hora': data_hora,
                    'data': registro.entrada.strftime('%Y-%m-%d') if registro.entrada else None,
                    'hora_entrada': registro.entrada.strftime('%H:%M') if registro.entrada else None,
                    'data_hora_saida': data_hora_saida,
                    'data_saida': registro.saida.strftime('%Y-%m-%d') if registro.saida else None,
                    'hora_saida': registro.saida.strftime('%H:%M') if registro.saida else None,
                    'isv': registro.isv,
                    'saida_pendente': registro.saida_pendente,
                    'observacao': registro.observacao,
                    'setor': registro.setor
                }
                logger.info(f"Enviando dados do registro: {data}")
                return JsonResponse(data)
            else:
                # Para acesso direto, redireciona para a home
                return redirect('home')
        
        elif request.method == 'POST':
            logger.info(f"Recebido POST para atualizar registro {registro_id}. Dados: {request.POST}")
            
            # Extrai os dados do formulário
            data_entrada = request.POST.get('data_entrada')
            hora_entrada = request.POST.get('hora_entrada')
            data_saida = request.POST.get('data_saida')
            hora_saida = request.POST.get('hora_saida')
            justificativa = request.POST.get('justificativa')
            isv = request.POST.get('isv') == 'on'
            
            # Log para depuração
            logger.info(f"Dados extraídos: data_entrada={data_entrada}, hora_entrada={hora_entrada}")
            logger.info(f"data_saida={data_saida}, hora_saida={hora_saida}, isv={isv}")
            logger.info(f"justificativa={justificativa}")
            
            # Compatibilidade com código anterior que usava 'data' em vez de 'data_entrada'
            if not data_entrada and request.POST.get('data'):
                data_entrada = request.POST.get('data')
                logger.info(f"Usando campo 'data' alternativo: {data_entrada}")
            
            # Validação básica
            if not justificativa:
                logger.warning("Justificativa não fornecida")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'A justificativa é obrigatória'
                    }, status=400)
                messages.error(request, 'A justificativa é obrigatória')
                return redirect('home')
            
            try:
                # Processa a data e hora de entrada
                entrada_datetime = None
                if data_entrada and hora_entrada:
                    try:
                        logger.info(f"Processando entrada: {data_entrada} {hora_entrada}")
                        entrada_datetime = datetime.strptime(f"{data_entrada} {hora_entrada}", "%Y-%m-%d %H:%M")
                        entrada_datetime = pytz.timezone('America/Sao_Paulo').localize(entrada_datetime)
                        registro.entrada = entrada_datetime
                        logger.info(f"Entrada processada: {entrada_datetime}")
                    except ValueError as e:
                        logger.error(f"Erro ao processar data/hora de entrada: {e}")
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Formato de data/hora de entrada inválido: {e}'
                        }, status=400)
                
                # Processa a data e hora de saída, se fornecidas
                saida_datetime = None
                if data_saida and hora_saida:
                    try:
                        logger.info(f"Processando saída: {data_saida} {hora_saida}")
                        saida_datetime = datetime.strptime(f"{data_saida} {hora_saida}", "%Y-%m-%d %H:%M")
                        saida_datetime = pytz.timezone('America/Sao_Paulo').localize(saida_datetime)
                        registro.saida = saida_datetime
                        registro.saida_pendente = False
                        logger.info(f"Saída processada: {saida_datetime}")
                    except ValueError as e:
                        logger.error(f"Erro ao processar data/hora de saída: {e}")
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Formato de data/hora de saída inválido: {e}'
                        }, status=400)
                
                # Se não tiver saída, marca como pendente
                if not saida_datetime:
                    registro.saida_pendente = True
                    logger.info("Marcando registro como saída pendente")
                
                # Atualiza o campo de ISV
                registro.isv = isv
                logger.info(f"ISV atualizado: {isv}")
                
                # Registra a justificativa para a edição
                registro.justificativa_edicao = justificativa
                registro.editado_por = request.user
                registro.data_edicao = timezone.now()
                registro.status_alteracao = 'EDITADO'
                
                # Salva o registro atualizado
                registro.save()
                logger.info(f"Registro {registro_id} atualizado com sucesso")
                
                # Log para debug
                log_data = {
                    'registro_id': registro_id,
                    'data_entrada': data_entrada,
                    'hora_entrada': hora_entrada,
                    'data_saida': data_saida,
                    'hora_saida': hora_saida,
                    'entrada_datetime': str(entrada_datetime) if entrada_datetime else None,
                    'saida_datetime': str(saida_datetime) if saida_datetime else None,
                    'saida_pendente': registro.saida_pendente,
                    'isv': isv
                }
                logger.info(f"Detalhes da atualização: {log_data}")
                
                # Atualiza também o registro no dashboard, se existir
                try:
                    dashboard_registro = RegistroDashboard.objects.get(registro_historico=registro)
                    logger.info(f"Atualizando registro no dashboard: {dashboard_registro.id}")
                    
                    dashboard_registro.data_hora = registro.entrada
                    dashboard_registro.data_hora_saida = registro.saida
                    dashboard_registro.saida_pendente = registro.saida_pendente
                    dashboard_registro.isv = registro.isv
                    
                    if registro.saida and not dashboard_registro.operador_saida:
                        dashboard_registro.operador_saida = request.user
                        
                    dashboard_registro.save()
                    logger.info("Registro do dashboard atualizado com sucesso")
                except RegistroDashboard.DoesNotExist:
                    logger.info("Não foi encontrado registro correspondente no dashboard")
                except Exception as e:
                    logger.error(f"Erro ao atualizar registro do dashboard: {e}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success'})
                else:
                    messages.success(request, 'Registro atualizado com sucesso')
                    return redirect('home')
                
            except Exception as e:
                logger.error(f"Erro ao atualizar registro: {str(e)}", exc_info=True)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Erro ao processar datas: {str(e)}'
                    }, status=500)
                else:
                    messages.error(request, f'Erro ao processar datas: {str(e)}')
                    return redirect('home')
    
    except RegistroAcesso.DoesNotExist:
        logger.error(f"Registro {registro_id} não encontrado")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Registro não encontrado'
            }, status=404)
        else:
            messages.error(request, 'Registro não encontrado')
            return redirect('home')
    except Exception as e:
        logger.error(f"Erro geral ao acessar/editar registro {registro_id}: {str(e)}", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao processar a requisição: {str(e)}'
            }, status=500)
        else:
            messages.error(request, f'Erro ao processar a requisição: {str(e)}')
            return redirect('home')

@login_required
def excluir_registro(request, registro_id):
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
    # Obtém todos os registros do dashboard, sem filtrar por plantão
    registros = RegistroDashboard.objects.all().select_related(
        'servidor', 'operador', 'operador_saida'
    ).order_by('data_hora', 'id')
    
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    agora = timezone.localtime(timezone.now(), tz)
    
    # Cria um DataFrame com os registros
    data = []
    for registro in registros:
        # Converte os horários para UTC-4
        data_hora = timezone.localtime(registro.data_hora, tz)
        data_hora_saida = timezone.localtime(registro.data_hora_saida, tz) if registro.data_hora_saida else None
        
        # Identifica o plantão do registro
        plantao_registro = calcular_plantao_atual(data_hora)['nome']
        
        # Se for uma entrada normal
        if registro.tipo_acesso == 'ENTRADA':
            data.append({
                'ORD': len(data) + 1,
                'Plantão': plantao_registro,
                'Data': data_hora.strftime('%d/%m/%Y'),
                'Operador': registro.operador.get_full_name() or registro.operador.username,
                'Servidor': registro.servidor.nome,
                'Documento': registro.servidor.numero_documento,
                'Setor': registro.servidor.setor or '-',
                'Veículo': registro.veiculo if registro.veiculo and registro.veiculo.strip() else registro.servidor.veiculo if registro.servidor.veiculo and registro.servidor.veiculo.strip() else '-',
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': data_hora.strftime('%d/%m/%Y %H:%M'),
                'Saída': data_hora_saida.strftime('%d/%m/%Y %H:%M') if data_hora_saida else 'Pendente'
            })
        # Se for uma saída definitiva
        elif registro.tipo_acesso == 'SAIDA':
            data.append({
                'ORD': len(data) + 1,
                'Plantão': plantao_registro,
                'Data': data_hora.strftime('%d/%m/%Y'),
                'Operador': registro.operador.get_full_name() or registro.operador.username,
                'Servidor': f"Egresso: {registro.servidor.nome}" if not registro.servidor.nome.startswith('Egresso:') else registro.servidor.nome,
                'Documento': registro.servidor.numero_documento,
                'Setor': registro.setor or '-',  # Aqui estará a justificativa
                'Veículo': registro.veiculo if registro.veiculo and registro.veiculo.strip() else registro.servidor.veiculo if registro.servidor.veiculo and registro.servidor.veiculo.strip() else '-',
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': '-',
                'Saída': data_hora.strftime('%d/%m/%Y %H:%M')
            })
    
    # Cria o DataFrame com as colunas na ordem especificada
    df = pd.DataFrame(data, columns=[
        'ORD', 'Plantão', 'Data', 'Operador', 'Servidor', 'Documento', 
        'Setor', 'Veículo', 'ISV', 'Entrada', 'Saída'
    ])
    
    # Cria o arquivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=dashboard_controle_acesso_{agora.strftime("%Y%m%d_%H%M")}.xlsx'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Registros')
        
        # Ajusta a largura das colunas
        worksheet = writer.sheets['Registros']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            )
            worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
    
    return response

@login_required
@user_passes_test(is_staff)
def user_list(request):
    # Verifica se o usuário tem permissão de staff
    if not request.user.is_staff:
        messages.error(request, 'Você não tem permissão para acessar a lista de usuários.')
        return redirect('home')  # Redireciona para a página inicial em vez da página de login
    
    # Obtém todos os usuários ordenados por tipo (superuser, staff, operador) e depois por nome
    from django.db.models import Case, When, IntegerField
    
    users = User.objects.annotate(
        ordem_tipo=Case(
            When(is_superuser=True, then=1),
            When(is_staff=True, then=2),
            default=3,
            output_field=IntegerField()
        )
    ).order_by('ordem_tipo', 'username')
    
    # Prepara os dados para o template, incluindo informações do perfil
    users_data = []
    for user in users:
        # Obtém ou cria o perfil do usuário
        try:
            perfil = user.perfil
        except:
            from core.models import PerfilUsuario
            perfil = PerfilUsuario.objects.create(
                usuario=user,
                precisa_trocar_senha=False
            )
        
        # Se o perfil tem uma senha temporária, usa essa informação
        # Se não, apenas mostra None (traço na interface)
        senha_temporaria = perfil.senha_temporaria
            
        # Adiciona à lista de dados
        users_data.append({
            'user': user,
            'perfil': perfil,
            'senha_temporaria': senha_temporaria
        })
    
    return render(request, 'core/user_list.html', {'users_data': users_data, 'is_superuser': request.user.is_superuser})

@login_required
@user_passes_test(is_staff)
def user_create(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        is_staff = request.POST.get('is_staff') == 'on'
        
        if not username or not password:
            messages.error(request, 'Usuário e senha são obrigatórios.')
            return redirect('user_create')
        
        # Verifica se o usuário já existe
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Este nome de usuário já está em uso.')
            return redirect('user_create')
        
        # Cria o usuário
        user = User.objects.create_user(
            username=username,
            password=password,
            is_staff=is_staff
        )
        
        # Cria o perfil do usuário com senha temporária
        from core.models import PerfilUsuario
        PerfilUsuario.objects.create(
            usuario=user,
            precisa_trocar_senha=True,  # Força a troca de senha no primeiro login
            senha_temporaria=password  # Salva a senha temporária
        )
        
        # Registra a criação no log de auditoria
        LogAuditoria.objects.create(
            usuario=request.user,
            tipo_acao='CRIACAO',
            modelo='User',
            objeto_id=user.id,
            detalhes=f'Criação do usuário {username}'
        )
        
        messages.success(request, f'Usuário {username} criado com sucesso! A senha temporária é: {password}')
        return redirect('user_list')
    
    return render(request, 'core/user_create.html')

@login_required
def user_update(request, pk):
    # Verifica se o usuário tem permissão de staff
    if not request.user.is_staff:
        messages.error(request, 'Você não tem permissão para editar usuários.')
        return redirect('home')
        
    usuario = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        usuario.email = request.POST.get('email')
        usuario.first_name = request.POST.get('first_name')
        usuario.last_name = request.POST.get('last_name')
        usuario.is_staff = request.POST.get('is_staff') == 'on'
        
        if request.POST.get('password'):
            usuario.set_password(request.POST.get('password'))
        
        usuario.save()
        messages.success(request, 'Usuário atualizado com sucesso!')
        return redirect('user_list')
    
    return render(request, 'core/user_form.html', {'usuario': usuario})

@login_required
def user_delete(request, pk):
    # Verifica se o usuário tem permissão de staff
    if not request.user.is_staff:
        messages.error(request, 'Você não tem permissão para excluir usuários.')
        return redirect('home')
        
    if request.method == 'POST':
        user = get_object_or_404(User, pk=pk)
        user.delete()
        messages.success(request, 'Usuário excluído com sucesso!')
        return redirect('user_list')
    return redirect('user_list')

@login_required
def verificar_entrada(request, servidor_id):
    """Verifica se existe uma entrada sem saída para o servidor."""
    plantao_atual = calcular_plantao_atual()
    tem_entrada = RegistroAcesso.objects.filter(
        servidor_id=servidor_id,
        data_hora__gte=plantao_atual['inicio'],
        data_hora__lte=plantao_atual['fim'],
        tipo_acesso='ENTRADA',
        saida_pendente=True
    ).exists()
    
    return JsonResponse({'tem_entrada': tem_entrada})

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def limpar_historico(request):
    # Verifica se o usuário tem permissão de superuser
    if not request.user.is_superuser:
        messages.error(request, 'Apenas superusuários podem limpar o histórico.')
        return redirect('home')
        
    if request.method == 'POST':
        try:
            senha = request.POST.get('senha')
            data_inicio = request.POST.get('data_inicio')
            data_fim = request.POST.get('data_fim')
            
            # Verifica se a senha está correta
            if not request.user.check_password(senha):
                messages.error(request, 'Senha incorreta!')
                return redirect('historico')
            
            # Verifica se as datas foram fornecidas
            if not data_inicio or not data_fim:
                messages.error(request, 'É necessário informar o período para limpeza do histórico!')
                return redirect('historico')
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='RegistroAcesso',
                objeto_id=None,
                detalhes=f'Limpeza do histórico de registros entre {data_inicio} e {data_fim}'
            )
            
            # Exclui os registros do período selecionado
            RegistroAcesso.objects.filter(
                data_hora__date__gte=data_inicio,
                data_hora__date__lte=data_fim
            ).delete()
            
            messages.success(request, 'Histórico limpo com sucesso!')
            return redirect('historico')
            
        except Exception as e:
            messages.error(request, f'Erro ao limpar histórico: {str(e)}')
            return redirect('historico')
    
    return redirect('historico')

@login_required
@admin_required
def importar_servidores(request):
    if request.method == 'POST':
        try:
            arquivo = request.FILES['arquivo']
            
            # Tentativa de leitura com diferentes codificações
            encodings = ['utf-8', 'latin1', 'iso-8859-1', 'windows-1252']
            decoded_file = None
            successful_encoding = None
            
            for encoding in encodings:
                try:
                    # Tenta decodificar com a codificação atual
                    arquivo.seek(0)  # Reseta o ponteiro do arquivo
                    decoded_file = arquivo.read().decode(encoding).splitlines()
                    successful_encoding = encoding
                    break
                except UnicodeDecodeError:
                    # Se falhar, continua para a próxima codificação
                    continue
            
            if decoded_file is None:
                raise Exception(f"Não foi possível ler o arquivo com nenhuma das codificações suportadas ({', '.join(encodings)}). Certifique-se de salvar o arquivo como CSV com codificação UTF-8.")
                
            print(f"Arquivo CSV lido com sucesso usando codificação: {successful_encoding}")
            
            # Tenta identificar o delimitador (vírgula ou ponto-e-vírgula)
            primeira_linha = decoded_file[0] if decoded_file else ""
            delimiter = ';' if ';' in primeira_linha else ','
            print(f"Delimitador identificado: {delimiter}")
            
            # Usa o delimitador detectado
            reader = csv.DictReader(decoded_file, delimiter=delimiter)
            
            # Verificação e normalização dos nomes das colunas
            colunas_esperadas = ['Nome', 'Número do Documento', 'Setor', 'Veículo']
            colunas_reader = reader.fieldnames
            
            # Verificar se há colunas necessárias no CSV
            if not colunas_reader:
                raise Exception("Arquivo CSV não contém cabeçalhos de colunas")
                
            # Criar mapeamento para normalizar nomes de colunas
            mapeamento_colunas = {}
            for coluna_esperada in colunas_esperadas:
                # Verifica coluna exata
                if coluna_esperada in colunas_reader:
                    mapeamento_colunas[coluna_esperada] = coluna_esperada
                    continue
                
                # Verifica variação sem acentos e case insensitive
                coluna_normalizada = coluna_esperada.lower().replace('ú', 'u').replace('í', 'i')
                for coluna in colunas_reader:
                    if coluna and coluna.lower().replace('ú', 'u').replace('í', 'i') == coluna_normalizada:
                        mapeamento_colunas[coluna_esperada] = coluna
                        break
            
            # Verifica se todas as colunas necessárias foram encontradas
            colunas_faltantes = [col for col in colunas_esperadas if col not in mapeamento_colunas]
            if colunas_faltantes:
                colunas_encontradas = ", ".join([f"'{c}'" for c in colunas_reader if c])
                colunas_necessarias = ", ".join([f"'{c}'" for c in colunas_faltantes])
                raise Exception(f"Colunas não encontradas: {colunas_necessarias}. Colunas disponíveis: {colunas_encontradas}")
            
            servidores_criados = 0
            servidores_atualizados = 0
            
            for row in reader:
                try:
                    # Verifica se a linha tem dados válidos
                    if not row[mapeamento_colunas['Nome']] or not row[mapeamento_colunas['Número do Documento']]:
                        continue  # Pula linhas vazias ou sem dados essenciais
                        
                    servidor, created = Servidor.objects.update_or_create(
                        numero_documento=row[mapeamento_colunas['Número do Documento']],
                        defaults={
                            'nome': row[mapeamento_colunas['Nome']],
                            'setor': row[mapeamento_colunas['Setor']],
                            'veiculo': row[mapeamento_colunas['Veículo']],
                            'ativo': True
                        }
                    )
                    
                    if created:
                        servidores_criados += 1
                    else:
                        servidores_atualizados += 1
                    
                    LogAuditoria.objects.create(
                        usuario=request.user,
                        tipo_acao='CRIACAO' if created else 'EDICAO',
                        modelo='Servidor',
                        objeto_id=servidor.id,
                        detalhes=f"{'Criação' if created else 'Atualização'} de servidor via importação: {servidor.nome}"
                    )
                except Exception as row_error:
                    # Adiciona informações sobre a linha que falhou
                    raise Exception(f"Erro na linha {reader.line_num}: {str(row_error)}. Dados: {row}")
            
            messages.success(request, f'{servidores_criados} servidores criados e {servidores_atualizados} atualizados com sucesso!')
            return redirect('servidor_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao importar servidores: {str(e)}')
            return redirect('importar_servidores')
    
    return render(request, 'core/importar_servidores.html')

@login_required
@admin_required
def download_modelo_importacao(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=modelo_importacao.csv'
    
    # Configura encoding UTF-8 com BOM para compatibilidade com Excel
    response.write('\ufeff')
    
    # Estas colunas DEVEM corresponder exatamente às esperadas na função importar_servidores
    colunas = ['Nome', 'Número do Documento', 'Setor', 'Veículo']
    
    # Configura o CSV para usar ponto-e-vírgula como delimitador (melhor compatibilidade com Excel brasileiro)
    writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(colunas)
    writer.writerow(['João da Silva', '12.345.678-9', 'Administrativo', 'ABC1234'])
    writer.writerow(['Maria Oliveira', '98.765.432-1', 'RH', ''])
    
    return response

@login_required
@admin_required
def limpar_banco_servidores(request):
    if request.method == 'POST':
        try:
            senha = request.POST.get('senha')
            # O campo username é ignorado, pois é apenas para acessibilidade
            # username = request.POST.get('username')
            
            # Verifica se a senha está correta
            if not request.user.check_password(senha):
                messages.error(request, 'Senha incorreta!')
                return redirect('servidor_list')
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='Servidor',
                objeto_id=0,
                detalhes='Limpeza do banco de servidores'
            )
            
            # Exclui todos os registros do dashboard primeiro
            RegistroDashboard.objects.all().delete()
            
            # Exclui todos os servidores
            Servidor.objects.all().delete()
            
            messages.success(request, 'Banco de servidores limpo com sucesso!')
            return redirect('servidor_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao limpar banco de servidores: {str(e)}')
            return redirect('servidor_list')
    
    return redirect('servidor_list')

@login_required
@admin_required
def servidor_delete(request, pk):
    if request.method == 'POST':
        try:
            servidor = get_object_or_404(Servidor, pk=pk)
            nome_servidor = servidor.nome
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='Servidor',
                objeto_id=servidor.id,
                detalhes=f'Exclusão do servidor {nome_servidor}'
            )
            
            # Exclui o servidor
            servidor.delete()
            
            messages.success(request, f'Servidor {nome_servidor} excluído com sucesso!')
            return redirect('servidor_list')
            
        except Exception as e:
            messages.error(request, f'Erro ao excluir servidor: {str(e)}')
            return redirect('servidor_list')
    
    return redirect('servidor_list')

@login_required
def historico(request):
    # Configuração do timezone
    tz = pytz.timezone('America/Manaus')  # UTC-4
    
    # Obtém os parâmetros do filtro
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    servidor = request.GET.get('servidor', '')
    plantao = request.GET.get('plantao', '')
    filtro_rapido = request.GET.get('filtro_rapido', '')
    
    # Define datas padrão se não fornecidas
    if not data_inicio:
        data_inicio = (datetime.now(tz) - timedelta(days=1)).strftime('%Y-%m-%d')
    if not data_fim:
        data_fim = datetime.now(tz).strftime('%Y-%m-%d')
        
    # Converte as strings de data para objetos datetime
    data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d').replace(tzinfo=tz)
    data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=tz)
    
    # Aplica filtro rápido se solicitado
    if filtro_rapido:
        agora = datetime.now(tz)
        hora_atual = agora.hour
        
        # Determina o início do plantão atual
        if 7 <= hora_atual < 19:  # Plantão diurno
            inicio_plantao = agora.replace(hour=7, minute=30, second=0, microsecond=0)
        else:  # Plantão noturno
            if hora_atual < 7:  # Se for antes das 7h, o plantão começou no dia anterior
                inicio_plantao = (agora - timedelta(days=1)).replace(hour=19, minute=30, second=0, microsecond=0)
            else:  # Se for depois das 19h, o plantão começou no mesmo dia
                inicio_plantao = agora.replace(hour=19, minute=30, second=0, microsecond=0)
        
        if filtro_rapido == 'atual':
            data_inicio_dt = inicio_plantao
            data_fim_dt = agora
        elif filtro_rapido == 'anterior':
            if 7 <= hora_atual < 19:  # Se estamos no plantão diurno
                data_fim_dt = inicio_plantao - timedelta(minutes=1)  # 07:29 do dia atual
                data_inicio_dt = data_fim_dt - timedelta(hours=12)  # 19:30 do dia anterior
            else:  # Se estamos no plantão noturno
                data_fim_dt = inicio_plantao - timedelta(minutes=1)  # 19:29 do dia atual
                data_inicio_dt = data_fim_dt.replace(hour=7, minute=30)  # 07:30 do mesmo dia
    
    # Filtra os registros
    registros = RegistroAcesso.objects.filter(
        data_hora__range=(data_inicio_dt, data_fim_dt)
    ).select_related('servidor', 'operador', 'operador_saida').order_by('data_hora', 'data_hora_alteracao')
    
    # Aplica filtro por servidor
    if servidor:
        registros = registros.filter(
            Q(servidor__nome__icontains=servidor) |
            Q(servidor__numero_documento__icontains=servidor)
        )
    
    # Aplica filtro por plantão
    if plantao:
        registros = registros.filter(servidor__plantao=plantao)
    
    # Formata os registros para exibição
    registros_formatados = []
    for registro in registros:
        try:
            # Converte os horários para UTC-4
            data_hora = registro.data_hora.astimezone(tz) if registro.data_hora else None
            data_hora_saida = registro.data_hora_saida.astimezone(tz) if registro.data_hora_saida else None
            data_hora_alteracao = registro.data_hora_alteracao.astimezone(tz) if registro.data_hora_alteracao else None
            
            # Determina o plantão usando a função calcular_plantao_atual
            plantao_registro = calcular_plantao_atual(data_hora)['nome'] if data_hora else "N/A"
            
            registros_formatados.append({
                'id': registro.id,
                'plantao': plantao_registro,
                'data_hora': data_hora,
                'operador': registro.operador.get_full_name() or registro.operador.username if registro.operador else "N/A",
                'servidor': registro.servidor.nome if registro.servidor else "N/A",
                'numero_documento': registro.servidor.numero_documento if registro.servidor else "N/A",
                'setor': registro.servidor.setor or '-' if registro.servidor else "N/A",
                'veiculo': registro.veiculo if registro.veiculo and registro.veiculo.strip() else registro.servidor.veiculo if registro.servidor and registro.servidor.veiculo and registro.servidor.veiculo.strip() else '-',
                'isv': 'Sim' if registro.isv else 'Não',
                'entrada': data_hora.strftime('%H:%M') if data_hora and registro.tipo_acesso == 'ENTRADA' else '-',
                'observacao': registro.observacao or '-',
                'saida': data_hora_saida.strftime('%H:%M') if data_hora_saida else '-',
                'observacao_saida': registro.observacao_saida or '-',
                'status_alteracao': registro.status_alteracao or 'Original',
                'data_hora_alteracao': data_hora_alteracao.strftime('%d/%m/%Y %H:%M') if data_hora_alteracao else '-',
                'justificativa': registro.justificativa or '-'
            })
        except Exception as e:
            # Log do erro para depuração
            print(f"[ERRO] Falha ao processar registro {registro.id}: {str(e)}")
            continue  # Pula este registro e continua com o próximo
    
    # Se for solicitado exportar para Excel
    if request.GET.get('export') == 'excel':
        try:
            # Cria um DataFrame com os registros já formatados
            df = pd.DataFrame(registros_formatados)
            
            # Remove a coluna ID que é usada apenas internamente
            if 'id' in df.columns:
                df = df.drop('id', axis=1)
            
            # Renomeia as colunas para português
            colunas = {
                'plantao': 'Plantão',
                'data_hora': 'Data',
                'operador': 'Operador',
                'servidor': 'Servidor',
                'numero_documento': 'Documento',
                'setor': 'Setor',
                'veiculo': 'Veículo',
                'isv': 'ISV',
                'entrada': 'Entrada',
                'observacao': 'OBS Entrada',
                'saida': 'Saída',
                'observacao_saida': 'OBS Saída',
                'status_alteracao': 'Alteração',
                'data_hora_alteracao': 'Data/Hora Alteração',
                'justificativa': 'Justificativa'
            }
            df = df.rename(columns=colunas)
            
            # Converte a coluna de data para string no formato desejado
            # Trate registros com data_hora nulos
            df['Data'] = df['Data'].apply(lambda x: x.strftime('%d/%m/%Y') if hasattr(x, 'strftime') else 'N/A')
            
            # Cria o arquivo Excel na memória
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Histórico')
            
            # Prepara a resposta com o arquivo Excel
            output.seek(0)
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=historico_{data_inicio}_{data_fim}.xlsx'
            return response
        except Exception as e:
            # Log do erro para depuração
            import traceback
            print(f"[ERRO EXPORTAÇÃO EXCEL] {str(e)}")
            traceback.print_exc()
            
            # Retorna uma mensagem de erro amigável ao usuário
            messages.error(request, f"Erro ao exportar Excel: {str(e)}")
            # Continue com a renderização normal da página
    
    context = {
        'registros': registros_formatados,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'servidor': servidor,
        'plantao': plantao
    }
    
    return render(request, 'core/historico.html', context)

def saida_definitiva(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        numero_documento = request.POST.get('numero_documento')
        observacao = request.POST.get('observacao', '')
        
        try:
            # Validação dos campos obrigatórios
            if not nome or not numero_documento:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Nome e número do documento são obrigatórios.'
                })
            
            # Adiciona o prefixo "Egresso: " ao nome
            nome_completo = f"Egresso: {nome}"
            
            # Busca ou cria o servidor
            servidor, created = Servidor.objects.get_or_create(
                numero_documento=numero_documento,
                defaults={
                    'nome': nome_completo,
                    'setor': observacao,
                    'ativo': True,
                    'veiculo': None
                }
            )
            
            if not created:
                servidor.nome = nome_completo
                servidor.setor = observacao
                servidor.save()
            
            # Pega o horário atual
            data_hora = timezone.now()
            
            # Cria o registro no histórico
            registro_historico = RegistroAcesso.objects.create(
                servidor=servidor,
                tipo_acesso='SAIDA',
                operador=request.user,
                observacao=observacao,
                data_hora=data_hora,
                data_hora_saida=data_hora,  # Adiciona o horário de saída
                veiculo=servidor.veiculo,
                setor=servidor.setor,
                status_alteracao='ORIGINAL',
                saida_pendente=False  # Marca como não pendente
            )
            
            # Cria o registro no dashboard
            RegistroDashboard.objects.create(
                servidor=servidor,
                tipo_acesso='SAIDA',
                operador=request.user,
                data_hora=data_hora,
                data_hora_saida=data_hora,  # Adiciona o horário de saída
                veiculo=servidor.veiculo,
                setor=servidor.setor,
                registro_historico=registro_historico,
                saida_pendente=False  # Marca como não pendente
            )
            
            return JsonResponse({
                'status': 'success',
                'message': f'Saída definitiva registrada com sucesso para {servidor.nome}'
            })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
            
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido'
    })

@login_required
def limpar_dashboard(request):
    """
    View para limpar todos os registros do dashboard exceto os que têm saída pendente.
    """
    if request.method == 'POST':
        try:
            senha = request.POST.get('senha')
            print(f"[DEBUG] Recebida requisição para limpar dashboard do usuário: {request.user.username}")
            
            # Verifica se a senha foi fornecida
            if not senha:
                print(f"[ERRO] Senha não fornecida para limpar dashboard")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Senha não fornecida. Por favor, tente novamente.'
                }, status=400)
            
            # Verifica se a senha está correta
            if not request.user.check_password(senha):
                print(f"[ERRO] Senha incorreta fornecida pelo usuário: {request.user.username}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Senha incorreta! Por favor, tente novamente.'
                }, status=401)
            
            print(f"[INFO] Senha validada com sucesso para o usuário: {request.user.username}")
            
            # Registra a ação no log de auditoria
            try:
                LogAuditoria.objects.create(
                    usuario=request.user,
                    tipo_acao='EXCLUSAO',
                    modelo='RegistroDashboard',
                    objeto_id=0,
                    detalhes='Limpeza do dashboard (mantendo registros pendentes)'
                )
                print(f"[INFO] Log de auditoria criado com sucesso")
            except Exception as e:
                print(f"[ERRO] Falha ao criar log de auditoria: {str(e)}")
                # Continua mesmo se falhar o log de auditoria
            
            # Exclui todos os registros do dashboard EXCETO os que têm saída pendente
            # Isso inclui registros com saída já registrada E saídas definitivas
            try:
                registros_excluidos = RegistroDashboard.objects.filter(
                    Q(saida_pendente=False) | Q(tipo_acesso='SAIDA')
                ).delete()
                excluidos_count = registros_excluidos[0] if registros_excluidos else 0
                print(f"[INFO] Registros excluídos com sucesso: {excluidos_count}")
                
                # Retorna uma resposta JSON de sucesso
                return JsonResponse({
                    'status': 'success',
                    'message': 'Dashboard limpo com sucesso! (Registros com saída pendente foram mantidos)',
                    'detalhes': {
                        'registros_excluidos': excluidos_count
                    }
                })
            except Exception as e:
                print(f"[ERRO] Falha ao excluir registros: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Erro ao excluir registros: {str(e)}'
                }, status=500)
                
        except Exception as e:
            import traceback
            print(f"[ERRO] Falha ao limpar dashboard: {str(e)}")
            traceback.print_exc()
            return JsonResponse({
                'status': 'error',
                'message': f'Erro inesperado: {str(e)}'
            }, status=500)
    
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

    Esta view permite:
    1. Listar os servidores faltosos do plantão atual
    2. Listar os ISVs presentes
    3. Exportar ambas as listas em formato PDF

    Args:
        request: HttpRequest contendo os parâmetros da requisição
            - nome (opcional): Filtro por nome ou documento do servidor
            - format (opcional): Se 'pdf', gera relatório em PDF

    Returns:
        HttpResponse: Renderiza template com listas ou retorna arquivo PDF/JSON
    """
    # Constantes para configuração do PDF
    PDF_TITLE_FONT_SIZE = 16
    PDF_SUBTITLE_FONT_SIZE = 14
    PDF_NORMAL_FONT_SIZE = 12
    PDF_TABLE_FONT_SIZE = 10
    TABLE_PADDING = 6
    
    # Obtém o plantão atual
    plantao_atual = calcular_plantao_atual()
    nome_plantao = plantao_atual['nome']
    
    # Obtém o filtro de nome da query string e sanitiza
    filtro_nome = request.GET.get('nome', '').strip()
    
    try:
        # Busca servidores do plantão atual
        servidores_plantao = Servidor.objects.filter(
            setor__icontains=nome_plantao,
            ativo=True
        ).order_by('nome')
        
        # Aplica filtro por nome se fornecido
        if filtro_nome:
            servidores_plantao = servidores_plantao.filter(
                Q(nome__icontains=filtro_nome) |
                Q(numero_documento__icontains=filtro_nome)
            )
        
        # Busca registros de entrada do dia
        hoje = timezone.now().date()
        registros_hoje = RegistroDashboard.objects.filter(
            data_hora__date=hoje,
            tipo_acesso='ENTRADA',
            saida_pendente=True  # Adiciona filtro para considerar apenas registros ativos
        ).select_related('servidor')
        
        servidores_presentes = set(registro.servidor_id for registro in registros_hoje)
        
        # Processa ISVs presentes
        isvs_presentes = []
        for registro in registros_hoje:
            if registro.isv:
                hora_entrada = timezone.localtime(registro.data_hora).strftime('%H:%M')
                isvs_presentes.append({
                    'ord': len(isvs_presentes) + 1,
                    'nome': registro.servidor.nome,
                    'documento': registro.servidor.numero_documento,
                    'setor': registro.servidor.setor,
                    'hora_entrada': hora_entrada
                })
        
        # Processa faltosos
        faltosos = []
        for servidor in servidores_plantao:
            if servidor.id not in servidores_presentes:
                faltosos.append({
                    'ord': len(faltosos) + 1,
                    'nome': servidor.nome,
                    'documento': servidor.numero_documento,
                    'setor': servidor.setor
                })
        
        # Ordena as listas por nome
        faltosos.sort(key=lambda x: x['nome'])
        isvs_presentes.sort(key=lambda x: x['nome'])
        
        # Atualiza números de ordem após ordenação
        for i, faltoso in enumerate(faltosos, 1):
            faltoso['ord'] = i
        for i, isv in enumerate(isvs_presentes, 1):
            isv['ord'] = i
        
        # Gera PDF se solicitado
        if request.GET.get('format') == 'pdf':
            try:
                # Cria buffer e documento
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                elements = []
                
                # Define estilos
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=PDF_TITLE_FONT_SIZE,
                    spaceAfter=30,
                    alignment=1
                )
                subtitle_style = ParagraphStyle(
                    'CustomSubtitle',
                    parent=styles['Heading2'],
                    fontSize=PDF_SUBTITLE_FONT_SIZE,
                    spaceAfter=20,
                    spaceBefore=30,
                    alignment=1
                )
                date_style = ParagraphStyle(
                    'DateStyle',
                    parent=styles['Normal'],
                    fontSize=PDF_NORMAL_FONT_SIZE,
                    spaceAfter=20,
                    alignment=1
                )
                
                # Adiciona título
                title = Paragraph(f"Relatório do Plantão {nome_plantao}", title_style)
                elements.append(title)
                
                # Adiciona data/hora
                current_datetime = timezone.localtime().strftime("%d/%m/%Y %H:%M:%S")
                date_paragraph = Paragraph(f"Gerado em: {current_datetime}", date_style)
                elements.append(date_paragraph)
                
                # Seção de Faltas
                if faltosos:
                    elements.append(Paragraph("Lista de Faltas", subtitle_style))
                    
                    # Dados da tabela
                    table_data = [['ORD', 'Nome', 'Documento']]
                    for faltoso in faltosos:
                        table_data.append([
                            str(faltoso['ord']),
                            faltoso['nome'],
                            faltoso['documento']
                        ])
                    
                    # Cria e estiliza tabela
                    table = Table(table_data, colWidths=[50, 350, 150])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), PDF_NORMAL_FONT_SIZE),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), TABLE_PADDING * 2),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), PDF_TABLE_FONT_SIZE),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                        ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
                        ('TOPPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                        ('LEFTPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                        ('RIGHTPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                    ]))
                    elements.append(table)
                else:
                    # Mensagem quando não há faltosos
                    no_data_style = ParagraphStyle(
                        'NoData',
                        parent=styles['Normal'],
                        fontSize=PDF_NORMAL_FONT_SIZE,
                        spaceAfter=20,
                        alignment=1
                    )
                    no_data = Paragraph("Não há faltas registradas para o plantão atual!", no_data_style)
                    elements.append(no_data)
                
                # Seção de ISVs
                if isvs_presentes:
                    elements.append(Paragraph("Lista de ISVs Presentes", subtitle_style))
                    
                    # Dados da tabela
                    table_data = [['ORD', 'Nome', 'Documento', 'Hora']]
                    for isv in isvs_presentes:
                        table_data.append([
                            str(isv['ord']),
                            isv['nome'],
                            isv['documento'],
                            isv['hora_entrada']
                        ])
                    
                    # Cria e estiliza tabela
                    table = Table(table_data, colWidths=[50, 300, 150, 50])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#006400')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), PDF_NORMAL_FONT_SIZE),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), TABLE_PADDING * 2),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), PDF_TABLE_FONT_SIZE),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                        ('ALIGN', (1, 0), (-1, -1), 'LEFT'),
                        ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
                        ('TOPPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                        ('LEFTPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                        ('RIGHTPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                    ]))
                    elements.append(table)
                
                # Gera PDF
                doc.build(elements)
                
                # Prepara resposta
                buffer.seek(0)
                response = HttpResponse(buffer.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="relatorio_faltas_{hoje}.pdf"'
                
                return response
                
            except Exception as e:
                messages.error(request, f'Erro ao gerar PDF: {str(e)}')
                return redirect('retirar_faltas')
        
        # Verifica se é uma requisição AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Retorna JSON para requisições AJAX
            return JsonResponse({
                'plantao_atual': nome_plantao,
                'faltosos': faltosos,
                'isvs_presentes': isvs_presentes,
                'total_faltas': len(faltosos),
                'total_isvs': len(isvs_presentes)
            })
        
        # Renderiza template para requisições normais
        context = {
            'faltosos': faltosos,
            'isvs_presentes': isvs_presentes,
            'filtro_nome': filtro_nome,
            'plantao_atual': nome_plantao
        }
        
        return render(request, 'core/retirar_faltas.html', context)
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        messages.error(request, f'Erro ao processar dados: {str(e)}')
        return redirect('home')

@login_required
def ambiente_treinamento(request):
    """View principal do ambiente de treinamento."""
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    agora = timezone.localtime(timezone.now(), tz)
    
    # Obtém o plantão atual
    plantao_atual = calcular_plantao_atual()
    
    # Filtra registros do plantão atual (todos os registros para treinamento)
    registros = RegistroAcessoTreinamento.objects.all().select_related('servidor', 'operador')
    
    # Calcula totais para os cards (similar ao dashboard principal)
    total_entradas = registros.filter(tipo_acesso='ENTRADA').count()  # Total de entradas
    total_saidas = registros.filter(data_hora_saida__isnull=False).count()  # Total de saídas normais
    total_pendentes = registros.filter(tipo_acesso='ENTRADA', saida_pendente=True).count()  # Entradas sem saída
    
    # Lista de servidores para os modais (do banco principal)
    servidores = Servidor.objects.filter(ativo=True).order_by('nome')
    
    # Define mostrar_aviso como False para desativar o aviso de troca de plantão
    mostrar_aviso = False
    
    # Obtém hora atual para uso em outros lugares
    hora_atual = agora.hour
    minuto_atual = agora.minute
    
    context = {
        'plantao_atual': plantao_atual,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_pendentes': total_pendentes,
        'servidores': servidores,
        'mostrar_aviso_plantao': mostrar_aviso,
        'hora_atual': f"{hora_atual:02d}:{minuto_atual:02d}",
        'agora': agora
    }
    
    return render(request, 'core/treinamento.html', context)

@login_required
def registros_plantao_treinamento(request):
    """View para obter os registros do plantão atual no ambiente de treinamento."""
    try:
        print(f"\n\n[DEBUG TREINAMENTO] ======= INÍCIO CARREGAMENTO DE REGISTROS =======")
        print(f"[DEBUG TREINAMENTO] Requisição recebida de: {request.user}")
        print(f"[DEBUG TREINAMENTO] Método HTTP: {request.method}")
        print(f"[DEBUG TREINAMENTO] Path: {request.path}")
        print(f"[DEBUG TREINAMENTO] GET params: {dict(request.GET)}")
        
        # Define o timezone UTC-4
        tz = pytz.timezone('America/Manaus')
        agora = timezone.now()
        print(f"[DEBUG TREINAMENTO] Data/hora atual (UTC): {agora}")
        print(f"[DEBUG TREINAMENTO] Data/hora atual (local): {timezone.localtime(agora, tz)}")
        
        # Obtém TODOS os registros (sem filtrar por data atual)
        registros = RegistroAcessoTreinamento.objects.all().select_related(
            'servidor', 'operador', 'operador_saida'
        ).order_by('-data_hora')
        
        print(f"[DEBUG TREINAMENTO] Total de registros encontrados: {registros.count()}")
        
        # Formata os registros
        registros_formatados = []
        
        for registro in registros:
            print(f"[DEBUG TREINAMENTO] ------ Processando registro ID: {registro.id} ------")
            print(f"[DEBUG TREINAMENTO] Tipo: {registro.tipo_acesso}")
            print(f"[DEBUG TREINAMENTO] Servidor: {registro.servidor.nome if registro.servidor else 'N/A'}")
            print(f"[DEBUG TREINAMENTO] Data/hora entrada (DB): {registro.data_hora}")
            print(f"[DEBUG TREINAMENTO] Data/hora saída (DB): {registro.data_hora_saida}")
            print(f"[DEBUG TREINAMENTO] Saída pendente: {registro.saida_pendente}")
            
            # Converte os horários para UTC-4
            data_hora_entrada = timezone.localtime(registro.data_hora, tz)
            print(f"[DEBUG TREINAMENTO] Data/hora entrada (local): {data_hora_entrada}")
            
            # Processa data e hora de entrada
            data_entrada = data_hora_entrada.strftime('%d/%m/%Y')
            hora_entrada = data_hora_entrada.strftime('%H:%M')
            print(f"[DEBUG TREINAMENTO] Data entrada formatada: {data_entrada}")
            print(f"[DEBUG TREINAMENTO] Hora entrada formatada: {hora_entrada}")
            
            # Processa data e hora de saída (se existir)
            data_saida = ''
            hora_saida = ''
            if registro.data_hora_saida:
                data_hora_saida = timezone.localtime(registro.data_hora_saida, tz)
                data_saida = data_hora_saida.strftime('%d/%m/%Y')
                hora_saida = data_hora_saida.strftime('%H:%M')
                print(f"[DEBUG TREINAMENTO] Data/hora saída (local): {data_hora_saida}")
                print(f"[DEBUG TREINAMENTO] Data saída formatada: {data_saida}")
                print(f"[DEBUG TREINAMENTO] Hora saída formatada: {hora_saida}")
            else:
                print(f"[DEBUG TREINAMENTO] Sem data/hora de saída")
            
            # Cria o dicionário com os dados formatados
            registro_formatado = {
                'id': registro.id,
                'servidor_id': registro.servidor.id if registro.servidor else None,
                'servidor_nome': registro.servidor.nome if registro.servidor else 'N/A',
                'servidor_documento': registro.servidor.numero_documento if registro.servidor else 'N/A',
                'tipo_acesso': registro.tipo_acesso,
                'data_entrada': data_entrada,
                'hora_entrada': hora_entrada,
                'data_saida': data_saida,
                'hora_saida': hora_saida,
                'setor': registro.setor or 'N/A',
                'veiculo': registro.veiculo or 'N/A',
                'isv': registro.isv,
                'saida_pendente': registro.saida_pendente,
                'operador': registro.operador.get_full_name() or registro.operador.username
            }
            print(f"[DEBUG TREINAMENTO] Registro formatado: {registro_formatado}")
            
            registros_formatados.append(registro_formatado)
        
        # Calcula os totais
        total_entradas = registros.filter(tipo_acesso='ENTRADA').count()
        total_saidas = registros.filter(tipo_acesso='SAIDA').count()
        total_pendentes = registros.filter(saida_pendente=True).count()
        
        print(f"[DEBUG TREINAMENTO] Total de entradas: {total_entradas}")
        print(f"[DEBUG TREINAMENTO] Total de saídas: {total_saidas}")
        print(f"[DEBUG TREINAMENTO] Total de pendentes: {total_pendentes}")
        print(f"[DEBUG TREINAMENTO] Total de registros formatados: {len(registros_formatados)}")
        
        # Prepara a resposta
        resposta = {
            'status': 'success',
            'registros': registros_formatados,
            'total_entradas': total_entradas,
            'total_saidas': total_saidas,
            'total_pendentes': total_pendentes
        }
        
        print(f"[DEBUG TREINAMENTO] Resposta preparada com sucesso")
        print(f"[DEBUG TREINAMENTO] Chaves na resposta: {resposta.keys()}")
        print(f"[DEBUG TREINAMENTO] ======= FIM CARREGAMENTO DE REGISTROS =======\n\n")
        
        return JsonResponse(resposta)
        
    except Exception as e:
        import traceback
        print(f"[ERRO TREINAMENTO] Erro ao carregar registros: {str(e)}")
        print(f"[ERRO TREINAMENTO] Traceback:")
        traceback.print_exc()
        
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao carregar registros: {str(e)}'
        }, status=500)

@login_required
def registro_detalhe_treinamento(request, registro_id):
    """View para visualizar detalhes de um registro no ambiente de treinamento."""
    try:
        print(f"[DEBUG] ======= INÍCIO DETALHES DO REGISTRO {registro_id} =======")
        
        # Obtém o registro
        registro = get_object_or_404(RegistroAcessoTreinamento, id=registro_id)
        print(f"[DEBUG] Registro encontrado: ID={registro.id}, Tipo={registro.tipo_acesso}")
        print(f"[DEBUG] Estado do objeto: saida_pendente={registro.saida_pendente}")
        print(f"[DEBUG] Data/hora entrada original (DB): {registro.data_hora}")
        print(f"[DEBUG] Data/hora saída original (DB): {registro.data_hora_saida}")
        
        # Define o timezone UTC-4
        tz = pytz.timezone('America/Manaus')
        
        # PROCESSAMENTO DA ENTRADA - Sempre obrigatória
        # Converte para timezone local e formata
        data_hora_entrada = timezone.localtime(registro.data_hora, tz)  
        data_entrada = data_hora_entrada.strftime('%d/%m/%Y')  # Formato brasileiro
        hora_entrada = data_hora_entrada.strftime('%H:%M')
        
        print(f"[DEBUG] Data entrada (timezone ajustado): {data_hora_entrada}")
        print(f"[DEBUG] Data entrada formatada (BR): {data_entrada}")
        print(f"[DEBUG] Hora entrada formatada: {hora_entrada}")
        
        # PROCESSAMENTO DA SAÍDA - Somente se existir
        # Inicializa com valores vazios
        data_saida = ""  # String vazia em vez de None para evitar confusão no frontend
        hora_saida = ""  # String vazia em vez de None para evitar confusão no frontend
        
        # Se houver data de saída registrada, processa e formata
        if registro.data_hora_saida:
            data_hora_saida = timezone.localtime(registro.data_hora_saida, tz)
            data_saida = data_hora_saida.strftime('%d/%m/%Y')  # Formato brasileiro
            hora_saida = data_hora_saida.strftime('%H:%M')
            print(f"[DEBUG] Data saída (timezone ajustado): {data_hora_saida}")
            print(f"[DEBUG] Data saída formatada (BR): {data_saida}")
            print(f"[DEBUG] Hora saída formatada: {hora_saida}")
        else:
            print(f"[DEBUG] Registro sem saída - campos de saída serão vazios")
        
        # Monta o objeto de resposta para o frontend
        response_data = {
            'id': registro.id,
            'servidor': {
                'id': registro.servidor.id,
                'nome': registro.servidor.nome,
                'documento': registro.servidor.numero_documento,
                'setor': registro.servidor.setor or '-',
                'veiculo': registro.servidor.veiculo or '-'
            },
            'tipo_acesso': registro.tipo_acesso,
            'data': data_entrada,           # Para compatibilidade com código existente
            'data_entrada': data_entrada,   # Campo específico para data de entrada
            'data_saida': data_saida,       # Campo específico para data de saída
            'hora_entrada': hora_entrada,   # Campo específico para hora de entrada
            'hora_saida': hora_saida,       # Campo específico para hora de saída
            'isv': registro.isv,
            'saida_pendente': registro.saida_pendente,
            'observacao': registro.observacao or ''
        }
        
        print(f"[DEBUG] Resposta enviada ao frontend (resumo):")
        print(f"[DEBUG] data_entrada: {response_data['data_entrada']}, hora_entrada: {response_data['hora_entrada']}")
        print(f"[DEBUG] data_saida: '{response_data['data_saida']}', hora_saida: '{response_data['hora_saida']}'")
        print(f"[DEBUG] saida_pendente: {response_data['saida_pendente']}")
        print(f"[DEBUG] ======= FIM DETALHES DO REGISTRO {registro_id} =======")
        
        return JsonResponse(response_data)
        
    except Exception as e:
        import traceback
        print(f"[ERRO] Falha ao buscar detalhes do registro {registro_id}: {str(e)}")
        traceback.print_exc()
        return JsonResponse({
            'status': 'error',
            'message': f"Erro ao carregar os dados do registro: {str(e)}"
        }, status=400)

@login_required
def buscar_servidor_treinamento(request):
    """View para buscar servidores no ambiente de treinamento."""
    print(f"\n\n[DEBUG TREINAMENTO] ======= INÍCIO BUSCA SERVIDOR =======")
    print(f"[DEBUG TREINAMENTO] Requisição recebida de: {request.user}")
    print(f"[DEBUG TREINAMENTO] Método HTTP: {request.method}")
    print(f"[DEBUG TREINAMENTO] Path: {request.path}")
    print(f"[DEBUG TREINAMENTO] GET params: {dict(request.GET)}")
    
    query = request.GET.get('query', '').strip()
    print(f"[DEBUG TREINAMENTO] Query de busca: '{query}'")
    
    if len(query) < 2:  # Alterado de 3 para 2
        print(f"[DEBUG TREINAMENTO] Query muito curta, retornando erro")
        return JsonResponse({
            'status': 'error',
            'message': 'Digite pelo menos 2 caracteres para buscar.'  # Alterado de 3 para 2
        }, status=400)
    
    try:
        # Busca o servidor no banco de dados principal
        print(f"[DEBUG TREINAMENTO] Buscando servidores com query: '{query}'")
        servidores = Servidor.objects.filter(
            Q(nome__icontains=query) |
            Q(numero_documento__icontains=query),
            ativo=True
        ).order_by('nome')[:10]
        
        print(f"[DEBUG TREINAMENTO] Servidores encontrados: {servidores.count()}")
        
        # Formata os resultados
        resultados = []
        for i, servidor in enumerate(servidores):
            print(f"[DEBUG TREINAMENTO] Processando servidor #{i+1}: ID={servidor.id}, Nome={servidor.nome}")
            resultados.append({
                'id': servidor.id,
                'nome': servidor.nome,
                'documento': servidor.numero_documento,
                'setor': servidor.setor or '-',
                'veiculo': servidor.veiculo or '-',
                'tipo_funcionario': servidor.tipo_funcionario,
                'plantao': servidor.plantao
            })
        
        print(f"[DEBUG TREINAMENTO] Total resultados formatados: {len(resultados)}")
        
        # Prepara a resposta
        resposta = {
            'status': 'success',
            'resultados': resultados
        }
        
        print(f"[DEBUG TREINAMENTO] Resposta preparada com sucesso")
        print(f"[DEBUG TREINAMENTO] Chaves na resposta: {resposta.keys()}")
        print(f"[DEBUG TREINAMENTO] ======= FIM BUSCA SERVIDOR =======\n\n")
        
        return JsonResponse(resposta)
        
    except Exception as e:
        import traceback
        print(f"[ERRO TREINAMENTO] Erro na busca de servidores: {str(e)}")
        print(f"[ERRO TREINAMENTO] Traceback:")
        traceback.print_exc()
        
        return JsonResponse({
            'status': 'error',
            'message': f'Erro na busca: {str(e)}'
        }, status=500)

@login_required
def registro_acesso_treinamento_create(request):
    """View para registrar acesso no ambiente de treinamento."""
    if request.method == 'POST':
        servidor_id = request.POST.get('servidor')
        tipo_acesso = request.POST.get('tipo_acesso')
        observacao = request.POST.get('observacao', '')
        isv = request.POST.get('isv') == 'on'
        
        servidor_original = get_object_or_404(Servidor, id=servidor_id)
        
        # Busca ou cria um ServidorTreinamento correspondente
        servidor_treinamento, created = ServidorTreinamento.objects.get_or_create(
            numero_documento=servidor_original.numero_documento,
            defaults={
                'nome': servidor_original.nome,
                'tipo_funcionario': servidor_original.tipo_funcionario,
                'plantao': servidor_original.plantao,
                'setor': servidor_original.setor,
                'veiculo': servidor_original.veiculo,
                'ativo': True
            }
        )
        
        # Verifica se já existe uma entrada sem saída
        entrada_pendente = RegistroAcessoTreinamento.objects.filter(
            servidor=servidor_treinamento,
            saida_pendente=True
        ).exists()
        
        if tipo_acesso == 'ENTRADA':
            if entrada_pendente:
                messages.error(request, 'Este servidor já possui uma entrada sem saída registrada. Registre a saída antes de fazer uma nova entrada.')
                return redirect('ambiente_treinamento')
            
            # Cria um novo registro
            registro = RegistroAcessoTreinamento.objects.create(
                servidor=servidor_treinamento,
                operador=request.user,
                tipo_acesso='ENTRADA',
                observacao=observacao,
                isv=isv,
                veiculo=servidor_treinamento.veiculo,
                setor=servidor_treinamento.setor,
                saida_pendente=True,
                status_alteracao='ORIGINAL',
                data_hora=timezone.now()
            )
            
            messages.success(request, 'Entrada registrada com sucesso!')
            return redirect('ambiente_treinamento')
            
        elif tipo_acesso == 'SAIDA':
            if not entrada_pendente:
                messages.error(request, 'Não foi encontrada uma entrada sem saída para este servidor. Registre uma entrada primeiro.')
                return redirect('ambiente_treinamento')
            
            # Procura a última entrada sem saída
            ultima_entrada = RegistroAcessoTreinamento.objects.filter(
                servidor=servidor_treinamento,
                saida_pendente=True
            ).first()
            
            # Atualiza o registro existente
            ultima_entrada.data_hora_saida = timezone.now()
            ultima_entrada.operador_saida = request.user
            ultima_entrada.observacao_saida = observacao
            ultima_entrada.saida_pendente = False
            ultima_entrada.save()
            
            messages.success(request, 'Saída registrada com sucesso!')
            return redirect('ambiente_treinamento')
    
    return redirect('ambiente_treinamento')

@login_required
def registro_manual_treinamento_create(request):
    """View para criar registros manuais no ambiente de treinamento."""
    if request.method == 'POST':
        servidor_id = request.POST.get('servidor')
        tipo_acesso = request.POST.get('tipo_acesso')
        data_hora = request.POST.get('data_hora_manual')
        justificativa = request.POST.get('justificativa')
        observacao = request.POST.get('observacao', '')
        isv = request.POST.get('isv') == 'on'
        
        servidor_original = get_object_or_404(Servidor, id=servidor_id)
        
        # Busca ou cria um ServidorTreinamento correspondente
        servidor_treinamento, created = ServidorTreinamento.objects.get_or_create(
            numero_documento=servidor_original.numero_documento,
            defaults={
                'nome': servidor_original.nome,
                'tipo_funcionario': servidor_original.tipo_funcionario,
                'plantao': servidor_original.plantao,
                'setor': servidor_original.setor,
                'veiculo': servidor_original.veiculo,
                'ativo': True
            }
        )
        
        # Cria o registro manual
        registro = RegistroAcessoTreinamento.objects.create(
            servidor=servidor_treinamento,
            operador=request.user,
            tipo_acesso=tipo_acesso,
            data_hora_manual=data_hora,
            justificativa=justificativa,
            observacao=observacao,
            isv=isv,
            veiculo=servidor_treinamento.veiculo,
            setor=servidor_treinamento.setor,
            status_alteracao='ORIGINAL'
        )
        
        # Atualiza saída pendente
        if tipo_acesso == 'ENTRADA':
            registro.saida_pendente = True
            registro.save()
        elif tipo_acesso == 'SAIDA':
            ultima_entrada = RegistroAcessoTreinamento.objects.filter(
                servidor=servidor_treinamento,
                tipo_acesso='ENTRADA',
                saida_pendente=True
            ).first()
            if ultima_entrada:
                ultima_entrada.saida_pendente = False
                ultima_entrada.save()
        
        messages.success(request, f'{tipo_acesso.title()} manual registrada com sucesso!')
        return redirect('ambiente_treinamento')
    
    return redirect('ambiente_treinamento')

@login_required
def saida_definitiva_treinamento(request):
    """View para registrar saída definitiva no ambiente de treinamento."""
    if request.method == 'POST':
        nome = request.POST.get('nome')
        numero_documento = request.POST.get('numero_documento')
        observacao = request.POST.get('observacao', '')
        
        try:
            # Validação dos campos obrigatórios
            if not nome or not numero_documento:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Nome e número do documento são obrigatórios.'
                })
            
            # Adiciona o prefixo "Egresso: " ao nome
            nome_completo = f"Egresso: {nome}"
            
            # Busca ou cria o servidor de treinamento
            servidor, created = ServidorTreinamento.objects.get_or_create(
                numero_documento=numero_documento,
                defaults={
                    'nome': nome_completo,
                    'setor': observacao,
                    'ativo': True,
                    'veiculo': None
                }
            )
            
            if not created:
                servidor.nome = nome_completo
                servidor.setor = observacao
                servidor.save()
            
            # Pega o horário atual
            data_hora = timezone.now()
            
            # Cria o registro de saída definitiva
            registro = RegistroAcessoTreinamento.objects.create(
                servidor=servidor,
                tipo_acesso='SAIDA',
                operador=request.user,
                observacao=observacao,
                data_hora=data_hora,
                data_hora_saida=data_hora,  # Adiciona o horário de saída
                veiculo=servidor.veiculo,
                setor=servidor.setor,
                status_alteracao='ORIGINAL',
                saida_pendente=False  # Marca como não pendente
            )
            
            return JsonResponse({
                'status': 'success',
                'message': f'Saída definitiva registrada com sucesso para {servidor.nome}'
            })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
            
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido'
    })

@login_required
def limpar_dashboard_treinamento(request):
    """
    View para limpar registros do ambiente de treinamento exceto os que têm saída pendente.
    Versão simplificada sem necessidade de senha para facilitar o treinamento.
    """
    if request.method == 'POST':
        try:
            # Exclui registros EXCETO os que têm saída pendente
            # Isso inclui registros com saída já registrada E saídas definitivas
            registros_excluidos = RegistroAcessoTreinamento.objects.filter(
                Q(saida_pendente=False) | Q(tipo_acesso='SAIDA')
            ).delete()
            excluidos_count = registros_excluidos[0] if registros_excluidos else 0
            
            # Retorna uma resposta JSON de sucesso
            return JsonResponse({
                'status': 'success',
                'message': 'Dashboard de treinamento limpo com sucesso! (Registros com saída pendente foram mantidos)',
                'detalhes': {
                    'registros_excluidos': excluidos_count
                }
            })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao excluir registros: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido. Use POST para esta operação.'
    }, status=405)

@login_required
def exportar_excel_treinamento(request):
    """View para exportar os dados reais do ambiente de treinamento para Excel."""
    # Obtém todos os registros do ambiente de treinamento
    registros = RegistroAcessoTreinamento.objects.all().select_related(
        'servidor', 'operador', 'operador_saida'
    ).order_by('data_hora', 'id')
    
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    agora = timezone.localtime(timezone.now(), tz)
    
    # Cria um DataFrame com os registros
    data = []
    for registro in registros:
        # Converte os horários para UTC-4
        data_hora = timezone.localtime(registro.data_hora, tz) if registro.data_hora else None
        data_hora_saida = timezone.localtime(registro.data_hora_saida, tz) if registro.data_hora_saida else None
        
        # Identifica o plantão do registro
        plantao_registro = calcular_plantao_atual(data_hora)['nome'] if data_hora else "N/A"
        
        # Se for uma entrada normal
        if registro.tipo_acesso == 'ENTRADA':
            data.append({
                'ORD': len(data) + 1,
                'Plantão': plantao_registro,
                'Data': data_hora.strftime('%d/%m/%Y') if data_hora else 'N/A',
                'Operador': registro.operador.get_full_name() or registro.operador.username,
                'Servidor': registro.servidor.nome,
                'Documento': registro.servidor.numero_documento,
                'Setor': registro.servidor.setor or '-',
                'Veículo': registro.veiculo if registro.veiculo and registro.veiculo.strip() else registro.servidor.veiculo if registro.servidor.veiculo and registro.servidor.veiculo.strip() else '-',
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': data_hora.strftime('%d/%m/%Y %H:%M') if data_hora else 'N/A',
                'Saída': data_hora_saida.strftime('%d/%m/%Y %H:%M') if data_hora_saida else 'Pendente'
            })
        # Se for uma saída definitiva
        elif registro.tipo_acesso == 'SAIDA':
            data.append({
                'ORD': len(data) + 1,
                'Plantão': plantao_registro,
                'Data': data_hora.strftime('%d/%m/%Y') if data_hora else 'N/A',
                'Operador': registro.operador.get_full_name() or registro.operador.username,
                'Servidor': f"Egresso: {registro.servidor.nome}" if not registro.servidor.nome.startswith('Egresso:') else registro.servidor.nome,
                'Documento': registro.servidor.numero_documento,
                'Setor': registro.setor or '-',  # Aqui estará a justificativa
                'Veículo': registro.veiculo if registro.veiculo and registro.veiculo.strip() else registro.servidor.veiculo if registro.servidor.veiculo and registro.servidor.veiculo.strip() else '-',
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': '-',
                'Saída': data_hora.strftime('%d/%m/%Y %H:%M') if data_hora else 'N/A'
            })
    
    # Se não houver registros, cria dados de exemplo
    if not data:
        data = [
            {
                'ORD': 1,
                'Plantão': 'DIURNO',
                'Data': agora.strftime('%d/%m/%Y'),
                'Operador': 'USUÁRIO TREINAMENTO',
                'Servidor': 'SERVIDOR EXEMPLO',
                'Documento': '12345678900',
                'Setor': 'EXEMPLO',
                'Veículo': 'ABC-1234',
                'ISV': 'Não',
                'Entrada': f"{agora.strftime('%d/%m/%Y')} 08:00",
                'Saída': 'Pendente'
            }
        ]
    
    # Cria o DataFrame com as colunas na ordem especificada
    df = pd.DataFrame(data, columns=[
        'ORD', 'Plantão', 'Data', 'Operador', 'Servidor', 'Documento', 
        'Setor', 'Veículo', 'ISV', 'Entrada', 'Saída'
    ])
    
    # Cria o arquivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=treinamento_controle_acesso_{agora.strftime("%Y%m%d_%H%M")}.xlsx'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Registros')
        
        # Ajusta a largura das colunas
        worksheet = writer.sheets['Registros']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            )
            worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
    
    return response

@login_required
def registro_acesso_treinamento_update(request, registro_id):
    """
    Atualiza um registro de acesso existente no ambiente de treinamento.
    Permite a edição de data e hora de entrada e saída por qualquer usuário.
    """
    try:
        # Tenta localizar o registro no banco de dados
        registro = RegistroAcessoTreinamento.objects.get(id=registro_id)
        
        # Para GET, retorna os detalhes do registro em JSON para AJAX
        if request.method == 'GET':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Prepara as datas em formato legível
                data_hora = None
                data_hora_saida = None
                
                if registro.data_hora:
                    data_hora = registro.data_hora.strftime('%Y-%m-%dT%H:%M')
                    
                if registro.data_hora_saida:
                    data_hora_saida = registro.data_hora_saida.strftime('%Y-%m-%dT%H:%M')
                    
                data = {
                    'id': registro.id,
                    'servidor_id': registro.servidor.id,
                    'servidor_nome': registro.servidor.nome,
                    'servidor_documento': registro.servidor.numero_documento,
                    'data_hora': data_hora,
                    'data': registro.data_hora.strftime('%Y-%m-%d') if registro.data_hora else None,
                    'hora_entrada': registro.data_hora.strftime('%H:%M') if registro.data_hora else None,
                    'data_hora_saida': data_hora_saida,
                    'data_saida': registro.data_hora_saida.strftime('%Y-%m-%d') if registro.data_hora_saida else None,
                    'hora_saida': registro.data_hora_saida.strftime('%H:%M') if registro.data_hora_saida else None,
                    'isv': registro.isv,
                    'saida_pendente': registro.saida_pendente,
                    'observacao': registro.observacao or '',
                    'setor': registro.setor
                }
                return JsonResponse(data)
            else:
                # Para acesso direto, redireciona para o ambiente de treinamento
                return redirect('ambiente_treinamento')
        
        elif request.method == 'POST':
            # Extrai os dados do formulário
            data_entrada = request.POST.get('data_entrada')
            hora_entrada = request.POST.get('hora_entrada')
            data_saida = request.POST.get('data_saida')
            hora_saida = request.POST.get('hora_saida')
            justificativa = request.POST.get('justificativa')
            isv = request.POST.get('isv') == 'on'
            
            # Compatibilidade com código anterior que usava 'data' em vez de 'data_entrada'
            if not data_entrada and request.POST.get('data'):
                data_entrada = request.POST.get('data')
            
            # Validação básica
            if not justificativa:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'A justificativa é obrigatória'
                    }, status=400)
                messages.error(request, 'A justificativa é obrigatória')
                return redirect('ambiente_treinamento')
            
            try:
                # Processa a data e hora de entrada
                entrada_datetime = None
                if data_entrada and hora_entrada:
                    try:
                        entrada_datetime = datetime.strptime(f"{data_entrada} {hora_entrada}", "%Y-%m-%d %H:%M")
                        entrada_datetime = pytz.timezone('America/Sao_Paulo').localize(entrada_datetime)
                        registro.data_hora = entrada_datetime
                    except ValueError as e:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Formato de data/hora de entrada inválido: {e}'
                        }, status=400)
                
                # Processa a data e hora de saída, se fornecidas
                saida_datetime = None
                if data_saida and hora_saida:
                    try:
                        saida_datetime = datetime.strptime(f"{data_saida} {hora_saida}", "%Y-%m-%d %H:%M")
                        saida_datetime = pytz.timezone('America/Sao_Paulo').localize(saida_datetime)
                        registro.data_hora_saida = saida_datetime
                        registro.saida_pendente = False
                    except ValueError as e:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Formato de data/hora de saída inválido: {e}'
                        }, status=400)
                
                # Se não tiver saída, marca como pendente
                if not saida_datetime:
                    registro.saida_pendente = True
                
                # Atualiza o campo de ISV
                registro.isv = isv
                
                # Registra a justificativa para a edição
                registro.justificativa_edicao = justificativa
                registro.editado_por = request.user
                registro.data_edicao = timezone.now()
                registro.status_alteracao = 'EDITADO'
                
                # Salva o registro atualizado
                registro.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success'})
                else:
                    messages.success(request, 'Registro atualizado com sucesso')
                    return redirect('ambiente_treinamento')
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Erro ao processar datas: {str(e)}'
                    }, status=500)
                else:
                    messages.error(request, f'Erro ao processar datas: {str(e)}')
                    return redirect('ambiente_treinamento')
    
    except RegistroAcessoTreinamento.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Registro não encontrado'
            }, status=404)
        else:
            messages.error(request, 'Registro não encontrado')
            return redirect('ambiente_treinamento')
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao processar a requisição: {str(e)}'
            }, status=500)
        else:
            messages.error(request, f'Erro ao processar a requisição: {str(e)}')
            return redirect('ambiente_treinamento')

@login_required
def excluir_registro_treinamento(request, registro_id):
    """View para excluir registros no ambiente de treinamento."""
    if request.method == 'POST':
        try:
            # Obtém o registro
            registro = get_object_or_404(RegistroAcessoTreinamento, id=registro_id)
            justificativa = request.POST.get('justificativa')
            
            if not justificativa:
                return JsonResponse({
                    'status': 'error',
                    'message': 'É necessário informar uma justificativa para excluir o registro.'
                }, status=400)
            
            # Cria uma cópia do registro com status EXCLUIDO para manter histórico
            registro_excluido = RegistroAcessoTreinamento.objects.create(
                servidor=registro.servidor,
                operador=registro.operador,
                tipo_acesso=registro.tipo_acesso,
                observacao=registro.observacao,
                observacao_saida=registro.observacao_saida,
                isv=registro.isv,
                veiculo=registro.veiculo,
                setor=registro.setor,
                data_hora=registro.data_hora,
                data_hora_saida=registro.data_hora_saida,
                operador_saida=registro.operador_saida,
                registro_original=registro,
                status_alteracao='EXCLUIDO',
                data_hora_alteracao=timezone.now(),
                justificativa=justificativa,
                saida_pendente=registro.saida_pendente
            )
            
            # Remove o registro original
            registro.delete()
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

@login_required
def registrar_saida_treinamento(request, registro_id):
    """Registra a saída diretamente para um registro pendente no ambiente de treinamento."""
    if request.method == 'POST':
        try:
            # Obtém o registro
            registro = get_object_or_404(RegistroAcessoTreinamento, id=registro_id)
            
            # Verifica se o registro está pendente
            if not registro.saida_pendente:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Este registro não está pendente de saída.'
                }, status=400)
            
            # Define o timezone UTC-4
            tz = pytz.timezone('America/Manaus')
            agora = timezone.now()
            
            # Atualiza o registro
            registro.data_hora_saida = agora
            registro.operador_saida = request.user
            registro.saida_pendente = False
            registro.save()
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

@login_required
def tutoriais_treinamento(request):
    """View para exibir os tutoriais em vídeo do ambiente de treinamento."""
    # Obtém todos os tutoriais ativos, ordenados por ordem e título
    tutoriais = VideoTutorial.objects.filter(ativo=True).order_by('ordem', 'titulo')
    
    # Agrupa os tutoriais por categoria
    tutoriais_por_categoria = {}
    for tutorial in tutoriais:
        categoria = tutorial.get_categoria_display()
        if categoria not in tutoriais_por_categoria:
            tutoriais_por_categoria[categoria] = []
        tutoriais_por_categoria[categoria].append(tutorial)
    
    context = {
        'tutoriais_por_categoria': tutoriais_por_categoria
    }
    
    return render(request, 'core/tutoriais.html', context)

@login_required
@user_passes_test(is_staff)
def user_reset_password(request, pk):
    user = get_object_or_404(User, pk=pk)
    
    # Apenas superusuários podem resetar senhas de outros superusuários
    if user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Apenas superusuários podem resetar senhas de outros superusuários.')
        return redirect('user_list')
    
    # Gera uma senha temporária mais intuitiva usando o nome de usuário
    # e alguns números aleatórios para garantir segurança
    random_digits = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    temp_password = f"{user.username}@{random_digits}"
    
    # Define a nova senha
    user.set_password(temp_password)
    user.save()
    
    # Atualiza ou cria o perfil do usuário
    try:
        perfil = user.perfil
    except:
        from core.models import PerfilUsuario
        perfil = PerfilUsuario.objects.create(usuario=user)
    
    perfil.precisa_trocar_senha = True
    perfil.senha_temporaria = temp_password
    perfil.save()
    
    # Registra a ação no log de auditoria
    LogAuditoria.objects.create(
        usuario=request.user,
        tipo_acao='EDICAO',
        modelo='User',
        objeto_id=user.id,
        detalhes=f'Reset de senha do usuário {user.username}'
    )
    
    messages.success(request, f'Senha resetada com sucesso! A nova senha temporária é: {temp_password}')
    return redirect('user_list')

@login_required
def trocar_senha(request):
    # Obtém ou cria o perfil do usuário
    try:
        perfil = request.user.perfil
    except:
        from core.models import PerfilUsuario
        perfil = PerfilUsuario.objects.create(
            usuario=request.user,
            precisa_trocar_senha=False
        )
    
    if request.method == 'POST':
        senha_atual = request.POST.get('senha_atual')
        nova_senha = request.POST.get('nova_senha')
        confirmar_senha = request.POST.get('confirmar_senha')
        
        # Validações básicas
        if not senha_atual or not nova_senha or not confirmar_senha:
            messages.error(request, 'Todos os campos são obrigatórios.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})
        
        if nova_senha != confirmar_senha:
            messages.error(request, 'A nova senha e a confirmação não coincidem.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})
        
        if len(nova_senha) < 8:
            messages.error(request, 'A nova senha deve ter pelo menos 8 caracteres.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})
        

        
        # Verifica se a senha atual está correta
        if not request.user.check_password(senha_atual):
            messages.error(request, 'Senha atual incorreta.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})
        
        # Validações adicionais de segurança
        if nova_senha.lower() in [request.user.username.lower(), request.user.first_name.lower(), request.user.last_name.lower()]:
            messages.error(request, 'A nova senha não pode conter seu nome de usuário ou nome pessoal.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})
        
        # Verifica se a senha não é muito simples
        senhas_comuns = ['12345678', '87654321', 'abcdefgh', 'password', 'senha123', '11111111', '00000000']
        if nova_senha.lower() in senhas_comuns:
            messages.error(request, 'Por favor, escolha uma senha mais segura.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})
        
        # Altera a senha
        request.user.set_password(nova_senha)
        request.user.save()
        
        # Atualiza o perfil do usuário
        try:
            perfil.precisa_trocar_senha = False
            perfil.senha_temporaria = None  # Limpa a senha temporária
            perfil.save()
        except Exception as e:
            # Se houver erro ao atualizar o perfil, registra o erro mas permite continuar
            logging.getLogger('django').error(f"Erro ao atualizar perfil após troca de senha: {str(e)}")
        
        messages.success(request, 'Senha alterada com sucesso! Por favor, faça login novamente.')
        return redirect('login')
    
    return render(request, 'core/trocar_senha.html', {'perfil': perfil})



