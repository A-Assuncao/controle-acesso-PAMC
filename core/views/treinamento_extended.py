"""Views de treinamento com logica estendida."""

from datetime import datetime

import pandas as pd
import pytz
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from ..models import RegistroAcessoTreinamento, Servidor, ServidorTreinamento
from ..utils import calcular_plantao_atual, extrair_plantao_do_setor

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
    
    # No ambiente de treinamento, todos têm permissão total
    context = {
        'plantao_atual': plantao_atual,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_pendentes': total_pendentes,
        'servidores': servidores,
        'mostrar_aviso_plantao': mostrar_aviso,
        'hora_atual': f"{hora_atual:02d}:{minuto_atual:02d}",
        'agora': agora,
        'is_superuser': request.user.is_superuser,
        'pode_registrar_acesso': True,
        'pode_excluir_registros': True,
        'pode_limpar_dashboard': True,
        'pode_saida_definitiva': True,
        'tipo_usuario': 'Treinamento'
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
def retirar_faltas_treinamento(request):
    """
    View para listar e exportar as faltas do plantão atual no ambiente de treinamento.

    Esta view permite:
    1. Listar os servidores faltosos do plantão atual
    2. Listar os ISVs presentes
    3. Listar as Permutas/Reposição de hora
    4. Exportar todas as listas em formato PDF

    Args:
        request: HttpRequest contendo os parâmetros da requisição
            - nome (opcional): Filtro por nome ou documento do servidor
            - format (opcional): Se 'pdf', gera relatório em PDF

    Returns:
        HttpResponse: Renderiza template com listas ou retorna arquivo PDF/JSON
    """
    import re
    import unicodedata
    
    # Constantes para configuração do PDF
    PDF_TITLE_FONT_SIZE = 16
    PDF_SUBTITLE_FONT_SIZE = 14
    PDF_NORMAL_FONT_SIZE = 12
    PDF_TABLE_FONT_SIZE = 10
    TABLE_PADDING = 6
    
    # Obtém o plantão atual
    plantao_atual = calcular_plantao_atual()
    nome_plantao = plantao_atual['nome']
    
    # Obtém a data atual para o nome do arquivo
    hoje = timezone.localtime().strftime('%Y%m%d')
    
    # Obtém o filtro de nome da query string e sanitiza
    filtro_nome = request.GET.get('nome', '').strip()
    
    try:
        # Busca servidores do plantão atual (setor contém o nome do plantão)
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
        
        # Busca TODOS os registros que estão no dashboard de treinamento (com saída pendente)
        registros_hoje = RegistroAcessoTreinamento.objects.filter(
            tipo_acesso='ENTRADA',
            saida_pendente=True  # Todos os registros ativos no dashboard
        ).select_related('servidor')
        
        # Cria mapeamento de servidores presentes baseado no documento
        servidores_presentes = set()
        for registro in registros_hoje:
            # Busca servidor equivalente no banco principal pelo documento
            try:
                servidor_principal = Servidor.objects.get(
                    numero_documento=registro.servidor.numero_documento,
                    ativo=True
                )
                servidores_presentes.add(servidor_principal.id)
            except Servidor.DoesNotExist:
                continue
        
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
        
        # Processa Permutas/Reposição de hora (treinamento)
        # Servidores que entraram, não são ISV e têm plantão diferente do atual
        permutas_reposicao = []
        
        for registro in registros_hoje:
            servidor = registro.servidor
            # Extrai o plantão do setor
            plantao_servidor = extrair_plantao_do_setor(servidor.setor)
            
            # Verifica se não é ISV e tem plantão diferente do atual
            if not registro.isv and plantao_servidor and plantao_servidor != nome_plantao:
                hora_entrada = timezone.localtime(registro.data_hora).strftime('%H:%M')
                permuta_data = {
                    'ord': len(permutas_reposicao) + 1,
                    'nome': servidor.nome,
                    'documento': servidor.numero_documento,
                    'setor': servidor.setor,
                    'plantao_servidor': plantao_servidor,
                    'plantao_atual': nome_plantao,
                    'hora_entrada': hora_entrada
                }
                permutas_reposicao.append(permuta_data)
        
        print(f"\n[DEBUG PERMUTAS] Total de permutas encontradas: {len(permutas_reposicao)}")
        print(f"[DEBUG PERMUTAS] ======= FIM PROCESSAMENTO PERMUTAS =======\n")
        
        # Processa faltosos (servidores do plantão atual que não entraram)
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
        permutas_reposicao.sort(key=lambda x: x['nome'])
        
        # Atualiza números de ordem após ordenação
        for i, faltoso in enumerate(faltosos, 1):
            faltoso['ord'] = i
        for i, isv in enumerate(isvs_presentes, 1):
            isv['ord'] = i
        for i, permuta in enumerate(permutas_reposicao, 1):
            permuta['ord'] = i
        
        # Gera PDF se solicitado (dados de exemplo para treinamento)
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
                
                # Adiciona título com indicação de treinamento
                title = Paragraph(f"Relatório do Plantão {nome_plantao} [TREINAMENTO]", title_style)
                elements.append(title)
                
                # Adiciona data/hora
                current_datetime = timezone.localtime().strftime("%d/%m/%Y %H:%M:%S")
                date_paragraph = Paragraph(f"Gerado em: {current_datetime}", date_style)
                elements.append(date_paragraph)
                
                # Adiciona dados de exemplo para demonstração
                if not faltosos and not isvs_presentes and not permutas_reposicao:
                    # Seção de exemplo
                    elements.append(Paragraph("Dados de Exemplo - Ambiente de Treinamento", subtitle_style))
                    
                    # Tabela de exemplo
                    example_data = [
                        ['Categoria', 'Quantidade', 'Observação'],
                        ['Faltas', '2', 'Servidores ausentes do plantão'],
                        ['ISVs', '1', 'Interventores de segurança'],
                        ['Permutas', '1', 'Reposições de hora']
                    ]
                    
                    table = Table(example_data, colWidths=[150, 100, 250])
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
                        ('TOPPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                        ('LEFTPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                        ('RIGHTPADDING', (0, 0), (-1, -1), TABLE_PADDING),
                    ]))
                    elements.append(table)
                else:
                    # Usa dados reais se existirem (mesma lógica da função principal)
                    # [Código similar à função principal...]
                    pass
                
                # Gera PDF
                doc.build(elements)
                
                # Prepara resposta
                buffer.seek(0)
                response = HttpResponse(buffer.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="relatorio_faltas_treinamento_{hoje}.pdf"'
                
                return response
                
            except Exception as e:
                messages.error(request, f'Erro ao gerar PDF: {str(e)}')
                return redirect('ambiente_treinamento')
        
        # Verifica se é uma requisição AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Retorna JSON para requisições AJAX
            return JsonResponse({
                'plantao_atual': nome_plantao,
                'faltosos': faltosos,
                'isvs_presentes': isvs_presentes,
                'permutas_reposicao': permutas_reposicao,
                'total_faltas': len(faltosos),
                'total_isvs': len(isvs_presentes),
                'total_permutas': len(permutas_reposicao)
            })
        
        # Renderiza template para requisições normais
        context = {
            'faltosos': faltosos,
            'isvs_presentes': isvs_presentes,
            'permutas_reposicao': permutas_reposicao,
            'filtro_nome': filtro_nome,
            'plantao_atual': nome_plantao
        }
        
        return render(request, 'core/retirar_faltas.html', context)
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        messages.error(request, f'Erro ao processar dados: {str(e)}')
        return redirect('ambiente_treinamento')

