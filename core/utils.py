from datetime import datetime, date, time, timedelta
from django.utils import timezone
import logging
import os
import re
import pytz
import unicodedata
from typing import Dict, Any

logger = logging.getLogger(__name__)

PREFIXO_EGRESSO = 'Egresso: '


def colapsar_espacos(texto: str | None) -> str:
    """
    Remove BOM, NBSP e reduz espacos/tabs/quebras repetidos a um unico espaco.
    """
    if texto is None:
        return ''
    valor = str(texto).replace('\ufeff', '').replace('\u00a0', ' ')
    return re.sub(r'\s+', ' ', valor).strip()


def texto_caixa_alta(texto):
    """
    Converte texto para caixa alta (maiúsculas), removendo espaços nas pontas.

    Usado em nome e setor de servidores para padronizar cadastro e exibição.
    """
    if texto is None:
        return ''
    valor = colapsar_espacos(texto)
    if not valor:
        return ''
    return valor.upper()


def texto_caixa_alta_nome_servidor(nome):
    """
    Converte nome do servidor para caixa alta, preservando o prefixo fixo
    "Egresso: " (saída definitiva de interno) em caixa baixa/mista original.
    """
    if nome is None:
        return ''
    valor = colapsar_espacos(nome)
    if not valor:
        return ''

    if normalizar_texto(valor).startswith('egresso:'):
        _, _, resto = valor.partition(':')
        resto = colapsar_espacos(resto)
        if resto:
            return f'{PREFIXO_EGRESSO}{resto.upper()}'
        return PREFIXO_EGRESSO.rstrip()

    return valor.upper()


def normalizar_texto(texto):
    """
    Normaliza texto removendo acentos e convertendo para minúsculas.
    
    Args:
        texto: String a ser normalizada
        
    Returns:
        String normalizada (sem acentos, em minúsculas)
    """
    if not texto:
        return ''
    
    # Remove acentos usando unicodedata
    texto_sem_acento = unicodedata.normalize('NFD', str(texto))
    texto_sem_acento = ''.join(char for char in texto_sem_acento 
                              if unicodedata.category(char) != 'Mn')
    
    # Converte para minúsculas
    return texto_sem_acento.lower()


def normalizar_documento(documento):
    """
    Remove pontuação e mantém apenas dígitos para busca por documento.

    Args:
        documento: Número do documento (CPF, RG, etc.)

    Returns:
        String contendo somente os dígitos
    """
    if not documento:
        return ''

    return ''.join(char for char in str(documento) if char.isdigit())


def texto_contem_todas_palavras(texto_normalizado, query_normalizada):
    """
    Verifica se o texto contém todas as palavras da query.

    Ex.: a query "anderson assuncao" encontra "anderson gomes assuncao".

    Args:
        texto_normalizado: Texto alvo já normalizado (sem acentos, minúsculas)
        query_normalizada: Termo de busca já normalizado

    Returns:
        True se cada palavra da query estiver presente no texto
    """
    if not query_normalizada:
        return False

    palavras = query_normalizada.split()
    if not palavras:
        return False

    return all(palavra in texto_normalizado for palavra in palavras)


def eh_servidor_egresso(nome):
    """Verifica se o servidor é egresso pelo prefixo no nome."""
    return normalizar_texto(nome).startswith('egresso:')


def servidor_corresponde_busca(servidor, query, query_normalizada):
    """
    Aplica as regras de correspondência por nome, documento e setor.

    - Nome/setor: todas as palavras digitadas devem aparecer no texto
    - Documento: busca apenas pelos dígitos, ignorando pontos e traços
    """
    nome_normalizado = normalizar_texto(servidor.nome)
    setor_normalizado = normalizar_texto(servidor.setor or '')

    nome_match = texto_contem_todas_palavras(nome_normalizado, query_normalizada)
    setor_match = texto_contem_todas_palavras(setor_normalizado, query_normalizada)

    query_digitos = normalizar_documento(query)
    documento_digitos = normalizar_documento(servidor.numero_documento)
    documento_match = len(query_digitos) >= 2 and query_digitos in documento_digitos

    return nome_match or documento_match or setor_match


def dashboard_registros_ativos():
    """Registros do dashboard cujo servidor ainda está ativo no cadastro."""
    from .models import RegistroDashboard

    return RegistroDashboard.objects.filter(servidor__ativo=True)


def desativar_servidor(servidor):
    """
    Exclusão operacional: inativa o cadastro e remove do dashboard atual.

    O histórico (RegistroAcesso) permanece intacto para consulta e relatórios.
    """
    from .models import RegistroDashboard

    RegistroDashboard.objects.filter(servidor=servidor).delete()
    servidor.ativo = False
    servidor.save(update_fields=['ativo'])


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

def buscar_servidores_helper(query, formato='detalhado', excluir_egressos=False):
    """
    Função auxiliar para buscar servidores de forma padronizada.
    Busca normalizada (sem acentos, case-insensitive).

    Args:
        query: String de busca
        formato: 'simples' para autocomplete ou 'detalhado' para ajax
        excluir_egressos: Se True, ignora servidores com prefixo "Egresso:"

    Returns:
        List de dicionários com dados dos servidores
    """
    from .models import Servidor

    if len(query) < 2:
        return []

    query_normalizada = normalizar_texto(query)
    servidores_raw = Servidor.objects.filter(ativo=True).order_by('nome')

    servidores_filtrados = []
    for servidor in servidores_raw:
        if excluir_egressos and eh_servidor_egresso(servidor.nome):
            continue

        if servidor_corresponde_busca(servidor, query, query_normalizada):
            servidores_filtrados.append(servidor)

        if len(servidores_filtrados) >= 10:
            break
    
    resultados = []
    
    if formato == 'simples':
        # Para autocomplete simples
        for servidor in servidores_filtrados:
            resultados.append({
                'id': servidor.id,
                'nome': servidor.nome,
                'numero_documento': servidor.numero_documento,
                'setor': servidor.setor or '-'
            })
    else:
        # Para ajax detalhado
        for servidor in servidores_filtrados:
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
        from .models import Servidor, ServidorTreinamento, RegistroAcessoTreinamento

        # Verifica se já existe uma entrada sem saída
        # (query no model RegistroAcessoTreinamento, que tem o campo
        # saida_pendente - nao em ServidorTreinamento, que e o cadastro).
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

        # Verifica se existe entrada pendente (query no model
        # RegistroAcessoTreinamento, que tem o campo saida_pendente).
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
        servidor_original = get_object_or_404(Servidor, id=servidor_id, ativo=True)
        
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
        servidor = get_object_or_404(Servidor, id=servidor_id, ativo=True)
    
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

def get_unidade_prisional():
    """
    Retorna o nome da unidade prisional das variáveis de ambiente.
    Padrão: PAMC se não estiver configurado.
    """
    return os.getenv('UNIDADE_PRISIONAL', 'PAMC')


def enviar_senha_usuario(user, senha, request=None):
    """
    Envia email transacional com a senha temporária do usuário.

    Retorna tupla (sucesso: bool, mensagem: str).
    Falha silenciosa em log de warning se SMTP nao estiver configurado
    ou se o envio retornar erro - a view de chamada deve mostrar o
    feedback no template e nao quebrar o fluxo de criacao/reset.
    """
    from django.core.mail import send_mail, BadHeaderError, get_connection
    from django.conf import settings
    from django.utils.html import escape

    if not user.email:
        return False, 'Usuário sem email cadastrado - não foi possível enviar.'

    if not getattr(settings, 'EMAIL_HOST', ''):
        return False, (
            'SMTP não configurado (EMAIL_HOST ausente no .env). '
            'A senha foi exibida na tela, copie e envie por outro canal.'
        )

    unidade = get_unidade_prisional()
    login_url = ''
    if request is not None:
        try:
            login_url = request.build_absolute_uri('/login/')
        except Exception:
            login_url = '/login/'

    full_name = user.get_full_name() or user.username

    assunto = f'[{unidade}] Suas credenciais de acesso ao Controle de Acesso'

    texto_plano = (
        f'Olá {full_name},\n\n'
        f'Sua conta no sistema de Controle de Acesso da {unidade} foi criada/resetada.\n\n'
        f'Login: {user.username}\n'
        f'Senha temporária: {senha}\n\n'
        f'Por segurança, troque a senha no primeiro acesso.\n\n'
        f'--\n'
        f'Controle de Acesso {unidade}\n'
        f'Este é um email automático, não responda.'
    )

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"></head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Tahoma, sans-serif; background: #f0f2f5;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #f0f2f5; padding: 32px 16px;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(15,23,42,0.08);">

          <tr>
            <td style="background: linear-gradient(135deg, #0a2540 0%, #1e3a5f 100%); padding: 32px 24px; text-align: center;">
              <img src="data:image/jpeg;base64,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" alt="{unidade}" width="84" height="84" style="display: block; margin: 0 auto 16px; border-radius: 50%; border: 3px solid rgba(255,255,255,0.2); box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
              <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 600; letter-spacing: -0.01em;">Controle de Acesso</h1>
              <p style="margin: 6px 0 0; color: #94a3b8; font-size: 13px; font-weight: 400;">{escape(unidade)} &bull; Sistema de Portaria</p>
            </td>
          </tr>

          <tr>
            <td style="padding: 40px 32px;">

              <p style="margin: 0 0 8px; font-size: 14px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">Ol&aacute;,</p>
              <h2 style="margin: 0 0 20px; font-size: 22px; color: #0f172a; font-weight: 600;">{escape(full_name)}</h2>

              <p style="margin: 0 0 24px; font-size: 15px; color: #475569; line-height: 1.6;">
                Sua conta no <strong style="color: #0f172a;">Controle de Acesso da {escape(unidade)}</strong> foi criada ou teve a senha redefinida.
              </p>

              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; margin: 0 0 24px;">
                <tr>
                  <td style="padding: 20px;">

                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 12px;">
                      <tr>
                        <td style="padding: 10px 14px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; width: 30%; vertical-align: middle;">
                          <span style="display: block; font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 2px;">&#128100; Login</span>
                        </td>
                        <td style="padding: 10px 14px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; vertical-align: middle;">
                          <code style="font-family: 'SF Mono', Consolas, monospace; font-size: 15px; color: #0f172a; font-weight: 500;">{escape(user.username)}</code>
                        </td>
                      </tr>
                    </table>

                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                      <tr>
                        <td style="padding: 10px 14px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; width: 30%; vertical-align: middle;">
                          <span style="display: block; font-size: 11px; color: #991b1b; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 2px;">&#128274; Senha</span>
                        </td>
                        <td style="padding: 10px 14px; background: #ffffff; border: 1px solid #fecaca; border-radius: 6px; vertical-align: middle;">
                          <code style="font-family: 'SF Mono', Consolas, monospace; font-size: 16px; color: #dc2625; font-weight: 600; letter-spacing: 0.05em;">{escape(senha)}</code>
                        </td>
                      </tr>
                    </table>

                  </td>
                </tr>
              </table>

              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: #fffbeb; border-left: 3px solid #f59e0b; border-radius: 6px; margin: 0 0 24px;">
                <tr>
                  <td style="padding: 14px 18px;">
                    <p style="margin: 0; font-size: 14px; color: #78350f; line-height: 1.5;">
                      <strong style="color: #92400e;">&#9888;&#65039; Importante:</strong> Por seguran&ccedil;a, troque esta senha no seu primeiro acesso ao sistema.
                    </p>
                  </td>
                </tr>
              </table>

              <p style="margin: 0; font-size: 14px; color: #475569; line-height: 1.6;">
                Em caso de d&uacute;vidas, entre em contato com a administra&ccedil;&atilde;o da unidade.
              </p>

            </td>
          </tr>

          <tr>
            <td style="background: #f8fafc; padding: 20px 32px; text-align: center; border-top: 1px solid #e2e8f0;">
              <p style="margin: 0; font-size: 12px; color: #94a3b8; line-height: 1.5;">
                Controle de Acesso {escape(unidade)}<br>
                <span style="color: #cbd5e1;">Email autom&aacute;tico &mdash; n&atilde;o responda</span>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


    try:
        connection = get_connection() if settings.EMAIL_HOST else None
        sent = send_mail(
            subject=assunto,
            message=texto_plano,
            from_email=None,  # usa DEFAULT_FROM_EMAIL
            recipient_list=[user.email],
            html_message=html,
            connection=connection,
            fail_silently=False,
        )
        if sent:
            return True, f'Email enviado para {user.email}.'
        return False, 'Falha desconhecida ao enviar email.'
    except BadHeaderError as e:
        logger.warning('enviar_senha_usuario: BadHeaderError %s', e)
        return False, f'Cabeçalho de email inválido: {e}'
    except Exception as e:
        logger.warning('enviar_senha_usuario: falha SMTP %s', e)
        return False, (
            f'Não foi possível enviar email: {e}. '
            'A senha foi exibida na tela, copie e envie por outro canal.'
        ) 