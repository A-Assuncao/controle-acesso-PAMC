"""
Views de relatórios e históricos.

Responsável por:
- Histórico completo de registros
- Filtros por data, servidor e plantão
- Exportação para Excel
- Relatórios consolidados
"""

import pytz
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q

from ..models import RegistroAcesso
from ..utils import calcular_plantao_atual


@login_required
def historico(request):
    """
    View completa de histórico de registros de acesso.
    
    Funcionalidades:
    - Filtros por data, servidor e plantão
    - Filtros rápidos (plantão atual/anterior)
    - Exportação para Excel
    - Formatação detalhada dos registros
    """
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