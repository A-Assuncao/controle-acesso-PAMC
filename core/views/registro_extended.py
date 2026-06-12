"""Views de registro com logica estendida (edicao e faltas)."""

import logging
from datetime import datetime

import pytz
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from ..models import RegistroDashboard, Servidor
from ..utils import calcular_plantao_atual, extrair_plantao_do_setor

logger = logging.getLogger(__name__)

@login_required
def registro_acesso_update(request, registro_id):
    """Atualiza registro do dashboard e espelha alterações no histórico."""
    tz_sp = pytz.timezone('America/Sao_Paulo')

    try:
        dashboard = RegistroDashboard.objects.select_related(
            'registro_historico', 'servidor'
        ).get(id=registro_id)
    except RegistroDashboard.DoesNotExist:
        return JsonResponse(
            {'status': 'error', 'message': 'Registro não encontrado'},
            status=404,
        )

    if request.method != 'POST':
        return redirect('home')

    data_entrada = request.POST.get('data_entrada') or request.POST.get('data')
    hora_entrada = request.POST.get('hora_entrada')
    data_saida = request.POST.get('data_saida')
    hora_saida = request.POST.get('hora_saida')
    justificativa = request.POST.get('justificativa')
    isv = request.POST.get('isv') == 'on'

    if not justificativa:
        return JsonResponse(
            {'status': 'error', 'message': 'A justificativa é obrigatória'},
            status=400,
        )

    try:
        entrada_datetime = dashboard.data_hora
        if data_entrada and hora_entrada:
            entrada_datetime = tz_sp.localize(
                datetime.strptime(f"{data_entrada} {hora_entrada}", "%Y-%m-%d %H:%M")
            )

        saida_datetime = None
        if data_saida and hora_saida:
            saida_datetime = tz_sp.localize(
                datetime.strptime(f"{data_saida} {hora_saida}", "%Y-%m-%d %H:%M")
            )

        saida_pendente = saida_datetime is None

        dashboard.data_hora = entrada_datetime
        dashboard.data_hora_saida = saida_datetime
        dashboard.saida_pendente = saida_pendente
        dashboard.isv = isv
        if saida_datetime and not dashboard.operador_saida:
            dashboard.operador_saida = request.user
        dashboard.save()

        registro = dashboard.registro_historico
        if registro:
            registro.data_hora = entrada_datetime
            registro.data_hora_saida = saida_datetime
            registro.saida_pendente = saida_pendente
            registro.isv = isv
            registro.justificativa = justificativa
            registro.status_alteracao = 'EDITADO'
            registro.data_hora_alteracao = timezone.now()
            if saida_datetime and not registro.operador_saida:
                registro.operador_saida = request.user
            registro.save()

        return JsonResponse({'status': 'success'})

    except ValueError as exc:
        return JsonResponse(
            {'status': 'error', 'message': f'Formato de data/hora inválido: {exc}'},
            status=400,
        )
    except Exception as exc:
        logger.error(
            'Erro ao atualizar registro %s: %s', registro_id, exc, exc_info=True
        )
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=500)


@login_required
def retirar_faltas(request):
    """
    View para listar e exportar as faltas do plantão atual.

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
        
        # Busca TODOS os registros que estão no dashboard (com saída pendente)
        registros_hoje = RegistroDashboard.objects.filter(
            tipo_acesso='ENTRADA',
            saida_pendente=True  # Todos os registros ativos no dashboard
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
        
        # Processa Permutas/Reposição de hora
        # Servidores que entraram, não são ISV e têm plantão diferente do atual
        permutas_reposicao = []
        print(f"\n[DEBUG PERMUTAS] ======= INÍCIO PROCESSAMENTO PERMUTAS =======")
        print(f"[DEBUG PERMUTAS] Plantão atual: {nome_plantao}")
        print(f"[DEBUG PERMUTAS] Total de registros hoje: {len(registros_hoje)}")
        
        for registro in registros_hoje:
            servidor = registro.servidor
            print(f"\n[DEBUG PERMUTAS] --- Analisando registro ---")
            print(f"[DEBUG PERMUTAS] Nome: {servidor.nome}")
            print(f"[DEBUG PERMUTAS] Documento: {servidor.numero_documento}")
            print(f"[DEBUG PERMUTAS] ISV: {registro.isv}")
            print(f"[DEBUG PERMUTAS] Setor do servidor: {servidor.setor}")
            
            # Extrai o plantão do setor
            plantao_servidor = extrair_plantao_do_setor(servidor.setor)
            print(f"[DEBUG PERMUTAS] Plantão extraído: {plantao_servidor}")
            
            # Verifica se não é ISV e tem plantão diferente do atual
            if not registro.isv:
                print(f"[DEBUG PERMUTAS] OK - Não é ISV")
                if plantao_servidor:
                    print(f"[DEBUG PERMUTAS] OK - Tem plantão definido: {plantao_servidor}")
                    if plantao_servidor != nome_plantao:
                        print(f"[DEBUG PERMUTAS] OK - Plantão diferente do atual ({plantao_servidor} != {nome_plantao})")
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
                        print(f"[DEBUG PERMUTAS] OK - ADICIONADO À LISTA DE PERMUTAS: {permuta_data}")
                    else:
                        print(f"[DEBUG PERMUTAS] X - Plantão igual ao atual ({plantao_servidor} == {nome_plantao})")
                else:
                    print(f"[DEBUG PERMUTAS] X - Não tem plantão definido (plantao = {plantao_servidor})")
            else:
                print(f"[DEBUG PERMUTAS] X - É ISV")
        
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
                
                # Seção de Permutas/Reposição de hora
                if permutas_reposicao:
                    elements.append(Paragraph("Permutas/Reposição de Hora", subtitle_style))
                    
                    # Dados da tabela
                    table_data = [['ORD', 'Nome', 'Documento', 'Plantão', 'Hora']]
                    for permuta in permutas_reposicao:
                        table_data.append([
                            str(permuta['ord']),
                            permuta['nome'],
                            permuta['documento'],
                            f"{permuta['plantao_servidor']} -> {permuta['plantao_atual']}",
                            permuta['hora_entrada']
                        ])
                    
                    # Cria e estiliza tabela
                    table = Table(table_data, colWidths=[50, 280, 120, 80, 50])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FF8C00')),
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
        return redirect('home')

