from datetime import datetime, date, time, timedelta
from django.utils import timezone
import pytz
from typing import Dict, Any

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

def verificar_plantao_pessoa(plantao_pessoa: str) -> bool:
    """
    Verifica se o plantão da pessoa corresponde ao plantão atual.
    
    Args:
        plantao_pessoa: Nome do plantão da pessoa (ALFA, BRAVO, CHARLIE ou DELTA)
        
    Returns:
        bool: True se o plantão da pessoa é o atual, False caso contrário
    """
    plantao_atual = calcular_plantao_atual()
    return plantao_pessoa == plantao_atual['nome']

def verificar_plantao_servidor(servidor):
    """
    Verifica se o servidor está no plantão correto.
    """
    if servidor.tipo_funcionario != 'PLANTONISTA':
        return True
    
    plantao_atual = calcular_plantao_atual()
    return servidor.plantao == plantao_atual['nome']

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