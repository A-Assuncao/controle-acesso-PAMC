from datetime import datetime, date, time, timedelta
from django.utils import timezone
from typing import Dict, Any

def calcular_plantao_atual() -> Dict[str, Any]:
    """
    Calcula o plantão atual baseado na data/hora.
    Os plantões são ALFA, BRAVO, CHARLIE e DELTA, se repetindo a cada 4 dias.
    O plantão ALFA começou em 01/01/2025 às 07:30h.
    Cada plantão vai das 07:30h de um dia até 07:30h do dia seguinte.
    
    Returns:
        Dict contendo:
        - nome: Nome do plantão (ALFA, BRAVO, CHARLIE ou DELTA)
        - inicio: Datetime do início do plantão
        - fim: Datetime do fim do plantão
    """
    # Data/hora de referência: 01/01/2025 07:30h (início do plantão ALFA)
    data_referencia = timezone.make_aware(
        datetime.combine(date(2025, 1, 1), time(7, 30))
    )
    
    # Momento atual
    agora = timezone.localtime()
    
    # Se estamos antes das 07:30h, consideramos que ainda é o plantão do dia anterior
    hora_atual = agora.time()
    if hora_atual < time(7, 30):
        agora = agora - timedelta(days=1)
    
    # Início do plantão atual (07:30h do dia atual)
    inicio_plantao = timezone.make_aware(
        datetime.combine(agora.date(), time(7, 30))
    )
    
    # Fim do plantão atual (07:30h do dia seguinte)
    fim_plantao = inicio_plantao + timedelta(days=1)
    
    # Calcula quantos dias se passaram desde a data de referência
    dias_passados = (agora.date() - data_referencia.date()).days
    
    # Calcula qual plantão é hoje (ciclo de 4 dias)
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
    ultima_entrada = servidor.registroacesso_set.filter(
        tipo_acesso='ENTRADA'
    ).order_by('-data_hora').first()
    
    if ultima_entrada:
        tempo_decorrido = timezone.now() - ultima_entrada.data_hora
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