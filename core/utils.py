from datetime import datetime, date, time, timedelta
from django.utils import timezone
import pytz
from typing import Dict, Any

def extrair_plantao_do_setor(setor):
    """
    Extrai o nome do plantão do campo setor.
    
    Args:
        setor: String contendo o setor do servidor
        
    Returns:
        String com o nome do plantão (ALFA, BRAVO, CHARLIE, DELTA) ou None
    """
    if not setor:
        return None
    setor_upper = setor.upper()
    plantoes = ['ALFA', 'BRAVO', 'CHARLIE', 'DELTA']
    for plantao in plantoes:
        if plantao in setor_upper:
            return plantao
    return None

def calcular_plantao_atual(data_hora: datetime = None) -> Dict[str, Any]:
    """
    Calcula o plantão baseado na data/hora fornecida ou atual.
    Os plantões são ALFA, BRAVO, CHARLIE e DELTA, se repetindo a cada 4 dias.
    O plantão ALFA começou em 01/01/2025 às 07:30h.
    Cada plantão vai das 07:30h de um dia até 07:29h do dia seguinte.
    
    Args:
        data_hora: Data/hora opcional para calcular o plantão. Se não informada, usa a data/hora atual.
    
    Returns:
        Dict contendo:
        - nome: Nome do plantão (ALFA, BRAVO, CHARLIE ou DELTA)
        - inicio: Datetime do início do plantão
        - fim: Datetime do fim do plantão
    """
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    
    # Data/hora de referência: 01/01/2025 07:30h (início do plantão ALFA)
    data_referencia = datetime.combine(date(2025, 1, 1), time(7, 30))
    data_referencia = tz.localize(data_referencia)
    
    # Momento atual em UTC-4 (ou data/hora fornecida)
    if data_hora is None:
        agora = timezone.localtime(timezone.now(), tz)
    else:
        # Se a data_hora já estiver com timezone, converte para UTC-4
        if timezone.is_aware(data_hora):
            agora = timezone.localtime(data_hora, tz)
        # Se a data_hora não tiver timezone, assume que já está em UTC-4
        else:
            agora = tz.localize(data_hora)
    
    # Se estamos antes das 07:30h, consideramos que ainda é o plantão do dia anterior
    hora_atual = agora.time()
    if hora_atual < time(7, 30):
        # O plantão começou às 07:30h do dia anterior
        data_plantao = agora.date() - timedelta(days=1)
    else:
        # O plantão começou às 07:30h do dia atual
        data_plantao = agora.date()
    
    # Início do plantão (07:30h do dia do plantão)
    inicio_plantao = datetime.combine(data_plantao, time(7, 30))
    inicio_plantao = tz.localize(inicio_plantao)
    
    # Fim do plantão (07:29:59 do dia seguinte)
    fim_plantao = inicio_plantao + timedelta(days=1) - timedelta(seconds=1)
    
    # Calcula quantos dias se passaram desde a data de referência até o dia do plantão
    dias_passados = (data_plantao - data_referencia.date()).days
    
    # Calcula qual plantão é (ciclo de 4 dias)
    # 0 = ALFA, 1 = BRAVO, 2 = CHARLIE, 3 = DELTA
    indice_plantao = dias_passados % 4
    
    # Lista de nomes dos plantões na ordem
    nomes_plantoes = ['ALFA', 'BRAVO', 'CHARLIE', 'DELTA']
    nome_plantao = nomes_plantoes[indice_plantao]
    
    return {
        'nome': nome_plantao,
        'inicio': inicio_plantao,
        'fim': fim_plantao
    }


def verificar_plantao_servidor(servidor):
    """
    Verifica se o servidor está no plantão correto.
    """
    if servidor.tipo_funcionario != 'PLANTONISTA':
        return True
    
    # Função para extrair o nome do plantão do setor
    def extrair_plantao_do_setor(setor):
        if not setor:
            return None
        setor_upper = setor.upper()
        plantoes = ['ALFA', 'BRAVO', 'CHARLIE', 'DELTA']
        for plantao in plantoes:
            if plantao in setor_upper:
                return plantao
        return None
    
    plantao_atual = calcular_plantao_atual()
    plantao_servidor = extrair_plantao_do_setor(servidor.setor)
    return plantao_servidor == plantao_atual['nome']

def verificar_saida_pendente(servidor):
    """
    Verifica se o servidor tem uma saída pendente (mais de 10 horas desde a última entrada).
    """
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    
    ultima_entrada = servidor.registroacesso_set.filter(
        tipo_acesso='ENTRADA'
    ).order_by('-data_hora').first()
    
    if ultima_entrada:
        agora = timezone.localtime(timezone.now(), tz)
        ultima_entrada_local = timezone.localtime(ultima_entrada.data_hora, tz)
        tempo_decorrido = agora - ultima_entrada_local
        return tempo_decorrido > timedelta(hours=10)
    return False

def determinar_tipo_acesso(servidor):
    """
    Determina automaticamente o tipo de acesso com base no último registro.
    """
    ultimo_registro = servidor.registroacesso_set.order_by('-data_hora').first()
    
    if not ultimo_registro or ultimo_registro.tipo_acesso == 'SAIDA':
        return 'ENTRADA'
    return 'SAIDA'

def formatar_registros_para_json(registros, modelo_dashboard=None, is_treinamento=False):
    """
    Formata registros para JSON de forma padronizada entre produção e treinamento.
    
    Args:
        registros: QuerySet de registros (RegistroAcesso ou RegistroAcessoTreinamento)
        modelo_dashboard: Modelo do dashboard (RegistroDashboard) - apenas para produção
        is_treinamento: Boolean indicando se é ambiente de treinamento
    
    Returns:
        List de dicionários com registros formatados
    """
    import pytz
    from django.utils import timezone
    
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    registros_formatados = []
    
    for registro in registros:
        # Converte os horários para UTC-4
        data_hora_entrada = timezone.localtime(registro.data_hora, tz)
        
        # Processa data e hora de entrada
        data_entrada = data_hora_entrada.strftime('%d/%m/%Y')
        hora_entrada = data_hora_entrada.strftime('%H:%M')
        
        # Processa data e hora de saída (se existir)
        data_saida = ''
        hora_saida = ''
        if registro.data_hora_saida:
            data_hora_saida = timezone.localtime(registro.data_hora_saida, tz)
            data_saida = data_hora_saida.strftime('%d/%m/%Y')
            hora_saida = data_hora_saida.strftime('%H:%M')
        
        # Para ambiente de treinamento, usa todos os registros
        # Para produção, usa apenas registros do dashboard atual
        if is_treinamento or not modelo_dashboard:
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
            registros_formatados.append(registro_formatado)
    
    return registros_formatados

def calcular_totais_registros(registros, is_treinamento=False):
    """
    Calcula totais de registros de forma padronizada.
    
    Args:
        registros: QuerySet de registros
        is_treinamento: Boolean indicando se é ambiente de treinamento
    
    Returns:
        Dict com total_entradas, total_saidas, total_pendentes
    """
    if is_treinamento:
        # Para treinamento, conta todos os registros
        total_entradas = registros.filter(tipo_acesso='ENTRADA').count()
        total_saidas = registros.filter(data_hora_saida__isnull=False).count()
        total_pendentes = registros.filter(tipo_acesso='ENTRADA', saida_pendente=True).count()
    else:
        # Para produção, usa a lógica específica do dashboard
        total_entradas = registros.count()  # Todos os registros do dashboard são entradas
        total_saidas = registros.filter(data_hora_saida__isnull=False).count()
        total_pendentes = registros.filter(saida_pendente=True).count()
    
    return {
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_pendentes': total_pendentes
    }

def buscar_servidores_helper(query, formato='detalhado'):
    """
    Função auxiliar para buscar servidores de forma padronizada.
    
    Args:
        query: String de busca
        formato: 'simples' para autocomplete ou 'detalhado' para ajax
    
    Returns:
        List de dicionários com dados dos servidores
    """
    from django.db.models import Q
    from .models import Servidor
    
    if len(query) < 2:
        return []
    
    servidores = Servidor.objects.filter(
        Q(nome__icontains=query) |
        Q(numero_documento__icontains=query),
        ativo=True
    ).order_by('nome')[:10]
    
    resultados = []
    
    if formato == 'simples':
        # Para autocomplete simples
        for servidor in servidores:
            resultados.append({
                'id': servidor.id,
                'nome': servidor.nome,
                'numero_documento': servidor.numero_documento,
                'setor': servidor.setor or '-'
            })
    else:
        # Para ajax detalhado
        for servidor in servidores:
            resultados.append({
                'id': servidor.id,
                'nome': servidor.nome,
                'documento': servidor.numero_documento,
                'setor': servidor.setor or '-',
                'veiculo': servidor.veiculo or '-',
                'tipo_funcionario': servidor.tipo_funcionario,
                'plantao': extrair_plantao_do_setor(servidor.setor)
            })
    
    return resultados

def exportar_excel_helper(registros, nome_arquivo, is_treinamento=False):
    """
    Função auxiliar para exportar registros para Excel de forma padronizada.
    
    Args:
        registros: QuerySet de registros (RegistroDashboard ou RegistroAcessoTreinamento)
        nome_arquivo: Prefixo do nome do arquivo
        is_treinamento: Boolean indicando se é ambiente de treinamento
    
    Returns:
        HttpResponse com arquivo Excel
    """
    from django.http import HttpResponse
    from django.utils import timezone
    import pandas as pd
    import pytz
    
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    agora = timezone.localtime(timezone.now(), tz)
    
    # Processa os registros
    data = []
    for registro in registros:
        # Converte os horários para UTC-4
        data_hora = timezone.localtime(registro.data_hora, tz) if registro.data_hora else None
        data_hora_saida = timezone.localtime(registro.data_hora_saida, tz) if registro.data_hora_saida else None
        
        # Identifica o plantão do registro
        plantao_registro = calcular_plantao_atual(data_hora)['nome'] if data_hora else "N/A"
        
        # Processa veículo
        veiculo = '-'
        if registro.veiculo and registro.veiculo.strip():
            veiculo = registro.veiculo
        elif hasattr(registro, 'servidor') and registro.servidor and registro.servidor.veiculo and registro.servidor.veiculo.strip():
            veiculo = registro.servidor.veiculo
        
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
                'Veículo': veiculo,
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': data_hora.strftime('%d/%m/%Y %H:%M') if data_hora else 'N/A',
                'Saída': data_hora_saida.strftime('%d/%m/%Y %H:%M') if data_hora_saida else 'Pendente'
            })
        # Se for uma saída definitiva
        elif registro.tipo_acesso == 'SAIDA':
            servidor_nome = registro.servidor.nome
            if not servidor_nome.startswith('Egresso:'):
                servidor_nome = f"Egresso: {servidor_nome}"
                
            data.append({
                'ORD': len(data) + 1,
                'Plantão': plantao_registro,
                'Data': data_hora.strftime('%d/%m/%Y') if data_hora else 'N/A',
                'Operador': registro.operador.get_full_name() or registro.operador.username,
                'Servidor': servidor_nome,
                'Documento': registro.servidor.numero_documento,
                'Setor': registro.setor or '-',  # Aqui estará a justificativa
                'Veículo': veiculo,
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': '-',
                'Saída': data_hora.strftime('%d/%m/%Y %H:%M') if data_hora else 'N/A'
            })
    
    # Se não houver registros no treinamento, cria dados de exemplo
    if is_treinamento and not data:
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
    
    # Cria o DataFrame
    df = pd.DataFrame(data, columns=[
        'ORD', 'Plantão', 'Data', 'Operador', 'Servidor', 'Documento', 
        'Setor', 'Veículo', 'ISV', 'Entrada', 'Saída'
    ])
    
    # Cria a resposta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={nome_arquivo}_{agora.strftime("%Y%m%d_%H%M")}.xlsx'
    
    # Escreve o Excel
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

def registrar_entrada_helper(servidor, operador, observacao, isv, is_treinamento=False):
    """
    Função auxiliar para registrar entradas de forma padronizada.
    
    Args:
        servidor: Instância do servidor (Servidor ou ServidorTreinamento)
        operador: Usuário que está registrando
        observacao: Observação do registro
        isv: Boolean indicando se é ISV
        is_treinamento: Boolean indicando se é ambiente de treinamento
    
    Returns:
        Tuple (sucesso: bool, mensagem: str)
    """
    from django.utils import timezone
    
    if is_treinamento:
        from .models import RegistroAcessoTreinamento
        
        # Verifica se já existe uma entrada sem saída
        entrada_pendente = RegistroAcessoTreinamento.objects.filter(
            servidor=servidor,
            saida_pendente=True
        ).exists()
        
        if entrada_pendente:
            return False, 'Este servidor já possui uma entrada sem saída registrada. Registre a saída antes de fazer uma nova entrada.'
        
        # Cria o registro de entrada
        RegistroAcessoTreinamento.objects.create(
            servidor=servidor,
            operador=operador,
            tipo_acesso='ENTRADA',
            observacao=observacao,
            isv=isv,
            veiculo=servidor.veiculo,
            setor=servidor.setor,
            saida_pendente=True,
            status_alteracao='ORIGINAL',
            data_hora=timezone.now()
        )
        
        return True, 'Entrada registrada com sucesso!'
    
    else:
        from .models import RegistroAcesso, RegistroDashboard
        
        # Verifica se já existe uma entrada sem saída no dashboard
        entrada_pendente = RegistroDashboard.objects.filter(
            servidor=servidor,
            saida_pendente=True
        ).exists()
        
        if entrada_pendente:
            return False, 'Este servidor já possui uma entrada sem saída registrada. Registre a saída antes de fazer uma nova entrada.'
        
        # Cria registro no histórico
        registro_historico = RegistroAcesso.objects.create(
            servidor=servidor,
            operador=operador,
            tipo_acesso='ENTRADA',
            observacao=observacao,
            isv=isv,
            veiculo=servidor.veiculo,
            setor=servidor.setor,
            saida_pendente=True,
            status_alteracao='ORIGINAL',
            data_hora=timezone.now()
        )
        
        # Cria registro no dashboard
        RegistroDashboard.objects.create(
            servidor=servidor,
            operador=operador,
            tipo_acesso='ENTRADA',
            isv=isv,
            veiculo=servidor.veiculo,
            setor=servidor.setor,
            data_hora=registro_historico.data_hora,
            saida_pendente=True,
            registro_historico=registro_historico
        )
        
        return True, 'Entrada registrada com sucesso!'

def registrar_saida_helper(servidor, operador, observacao, is_treinamento=False):
    """
    Função auxiliar para registrar saídas de forma padronizada.
    
    Args:
        servidor: Instância do servidor (Servidor ou ServidorTreinamento)
        operador: Usuário que está registrando
        observacao: Observação do registro
        is_treinamento: Boolean indicando se é ambiente de treinamento
    
    Returns:
        Tuple (sucesso: bool, mensagem: str)
    """
    from django.utils import timezone
    
    if is_treinamento:
        from .models import RegistroAcessoTreinamento
        
        # Verifica se existe entrada pendente
        entrada_pendente = RegistroAcessoTreinamento.objects.filter(
            servidor=servidor,
            saida_pendente=True
        ).first()
        
        if not entrada_pendente:
            return False, 'Não foi encontrada uma entrada sem saída para este servidor. Registre uma entrada primeiro.'
        
        # Atualiza o registro existente
        entrada_pendente.data_hora_saida = timezone.now()
        entrada_pendente.operador_saida = operador
        entrada_pendente.observacao_saida = observacao
        entrada_pendente.saida_pendente = False
        entrada_pendente.save()
        
        return True, 'Saída registrada com sucesso!'
    
    else:
        from .models import RegistroDashboard
        
        # Verifica se existe entrada pendente no dashboard
        entrada_pendente = RegistroDashboard.objects.filter(
            servidor=servidor,
            saida_pendente=True
        ).first()
        
        if not entrada_pendente:
            return False, 'Não foi encontrada uma entrada sem saída para este servidor. Registre uma entrada primeiro.'
        
        # Atualiza o registro histórico
        registro_historico = entrada_pendente.registro_historico
        registro_historico.data_hora_saida = timezone.now()
        registro_historico.operador_saida = operador
        registro_historico.observacao_saida = observacao
        registro_historico.saida_pendente = False
        registro_historico.save()
        
        # Atualiza o registro no dashboard
        entrada_pendente.data_hora_saida = registro_historico.data_hora_saida
        entrada_pendente.operador_saida = operador
        entrada_pendente.saida_pendente = False
        entrada_pendente.save()
        
        return True, 'Saída registrada com sucesso!'

def processar_registro_acesso_helper(request, is_treinamento=False):
    """
    Função auxiliar para processar registros de acesso de forma padronizada.
    
    Args:
        request: HttpRequest contendo os dados do formulário
        is_treinamento: Boolean indicando se é ambiente de treinamento
    
    Returns:
        Tuple (sucesso: bool, mensagem: str, redirect_url: str)
    """
    from django.shortcuts import get_object_or_404
    from django.contrib import messages
    
    servidor_id = request.POST.get('servidor')
    tipo_acesso = request.POST.get('tipo_acesso')
    observacao = request.POST.get('observacao', '')
    isv = request.POST.get('isv') == 'on'
    
    redirect_url = 'ambiente_treinamento' if is_treinamento else 'home'
    
    if is_treinamento:
        from .models import Servidor, ServidorTreinamento
        
        # Obtém o servidor original
        servidor_original = get_object_or_404(Servidor, id=servidor_id)
        
        # Busca ou cria um ServidorTreinamento correspondente
        servidor, created = ServidorTreinamento.objects.get_or_create(
            numero_documento=servidor_original.numero_documento,
            defaults={
                'nome': servidor_original.nome,
                'tipo_funcionario': servidor_original.tipo_funcionario,
                'setor': servidor_original.setor,
                'veiculo': servidor_original.veiculo,
                'ativo': True
            }
        )
    else:
        from .models import Servidor
        servidor = get_object_or_404(Servidor, id=servidor_id)
    
    # Processa entrada ou saída
    if tipo_acesso == 'ENTRADA':
        sucesso, mensagem = registrar_entrada_helper(servidor, request.user, observacao, isv, is_treinamento)
    elif tipo_acesso == 'SAIDA':
        sucesso, mensagem = registrar_saida_helper(servidor, request.user, observacao, is_treinamento)
    else:
        return False, 'Tipo de acesso inválido', redirect_url
    
    return sucesso, mensagem, redirect_url

def saida_definitiva_helper(request, is_treinamento=False):
    """
    Função auxiliar para processar saída definitiva de forma padronizada.
    
    Args:
        request: HttpRequest contendo os dados do formulário
        is_treinamento: Boolean indicando se é ambiente de treinamento
    
    Returns:
        Dict com status e mensagem para JsonResponse
    """
    from django.utils import timezone
    
    nome = request.POST.get('nome')
    numero_documento = request.POST.get('numero_documento')
    justificativa = request.POST.get('justificativa', '')
    
    # Validação dos campos obrigatórios
    if not nome or not numero_documento:
        return {
            'status': 'error',
            'message': 'Nome e número do documento são obrigatórios.'
        }
    
    # Adiciona o prefixo "Egresso: " ao nome
    nome_completo = f"Egresso: {nome}"
    
    try:
        if is_treinamento:
            from .models import ServidorTreinamento, RegistroAcessoTreinamento
            
            # Busca ou cria o servidor de treinamento
            servidor, created = ServidorTreinamento.objects.get_or_create(
                numero_documento=numero_documento,
                defaults={
                    'nome': nome_completo,
                    'setor': justificativa,
                    'ativo': True,
                    'veiculo': None
                }
            )
            
            if not created:
                servidor.nome = nome_completo
                servidor.setor = justificativa
                servidor.save()
            
            # Cria o registro de saída definitiva
            data_hora = timezone.now()
            RegistroAcessoTreinamento.objects.create(
                servidor=servidor,
                tipo_acesso='SAIDA',
                operador=request.user,
                observacao=justificativa,
                data_hora=data_hora,
                data_hora_saida=data_hora,
                veiculo=servidor.veiculo,
                setor=servidor.setor,
                status_alteracao='ORIGINAL',
                saida_pendente=False
            )
        else:
            from .models import Servidor, RegistroAcesso, RegistroDashboard
            
            # Busca ou cria o servidor
            servidor, created = Servidor.objects.get_or_create(
                numero_documento=numero_documento,
                defaults={
                    'nome': nome_completo,
                    'setor': justificativa,
                    'ativo': True,
                    'veiculo': None
                }
            )
            
            if not created:
                servidor.nome = nome_completo
                servidor.setor = justificativa
                servidor.save()
            
            # Cria o registro no histórico
            data_hora = timezone.now()
            registro_historico = RegistroAcesso.objects.create(
                servidor=servidor,
                tipo_acesso='SAIDA',
                operador=request.user,
                observacao=justificativa,
                data_hora=data_hora,
                data_hora_saida=data_hora,
                veiculo=servidor.veiculo,
                setor=servidor.setor,
                status_alteracao='ORIGINAL',
                saida_pendente=False
            )
            
            # Cria o registro no dashboard
            RegistroDashboard.objects.create(
                servidor=servidor,
                tipo_acesso='SAIDA',
                operador=request.user,
                data_hora=data_hora,
                data_hora_saida=data_hora,
                veiculo=servidor.veiculo,
                setor=servidor.setor,
                saida_pendente=False,
                registro_historico=registro_historico
            )
        
        return {
            'status': 'success',
            'message': f'Saída definitiva registrada com sucesso para {servidor.nome}'
        }
        
    except Exception as e:
                 return {
             'status': 'error',
             'message': str(e)
         }

def limpar_dashboard_helper(request, is_treinamento=False):
    """
    Função auxiliar para limpar dashboard de forma padronizada.
    
    Args:
        request: HttpRequest contendo os dados do formulário
        is_treinamento: Boolean indicando se é ambiente de treinamento
    
    Returns:
        Dict com status e mensagem para JsonResponse
    """
    from django.db.models import Q
    
    senha = request.POST.get('senha')
    
    # Verifica se a senha foi fornecida
    if not senha:
        return {
            'status': 'error',
            'message': 'Senha não fornecida. Por favor, tente novamente.'
        }
    
    # Verifica se a senha está correta
    if not request.user.check_password(senha):
        return {
            'status': 'error',
            'message': 'Senha incorreta! Por favor, tente novamente.'
        }
    
    try:
        if is_treinamento:
            from .models import RegistroAcessoTreinamento, LogAuditoria
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='RegistroAcessoTreinamento',
                objeto_id=0,
                detalhes='Limpeza do dashboard de treinamento (mantendo registros pendentes)'
            )
            
            # Exclui todos os registros EXCETO os que têm saída pendente
            registros_excluidos = RegistroAcessoTreinamento.objects.filter(
                saida_pendente=False
            ).delete()
        else:
            from .models import RegistroDashboard, LogAuditoria
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='RegistroDashboard',
                objeto_id=0,
                detalhes='Limpeza do dashboard (mantendo registros pendentes)'
            )
            
            # Exclui todos os registros EXCETO os que têm saída pendente
            # Isso inclui registros com saída já registrada E saídas definitivas
            registros_excluidos = RegistroDashboard.objects.filter(
                Q(saida_pendente=False) | Q(tipo_acesso='SAIDA')
            ).delete()
        
        excluidos_count = registros_excluidos[0] if registros_excluidos else 0
        
        ambiente = "treinamento" if is_treinamento else "produção"
        return {
            'status': 'success',
            'message': f'Dashboard de {ambiente} limpo com sucesso! (Registros com saída pendente foram mantidos)',
            'detalhes': {
                'registros_excluidos': excluidos_count
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Erro inesperado: {str(e)}'
        } 