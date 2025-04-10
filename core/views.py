from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, DateTimeField, Subquery, OuterRef
from django.utils import timezone
from datetime import datetime, timedelta, date
import pandas as pd
from .models import RegistroAcesso, LogAuditoria, Servidor, RegistroDashboard, RegistroAcessoTreinamento, VideoTutorial, ServidorTreinamento
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
    
    # Verifica se é o primeiro acesso do usuário hoje
    ultima_visita = request.session.get('ultima_visita_dashboard')
    request.session['ultima_visita_dashboard'] = agora.isoformat()
    
    # Verifica se está no horário de troca de plantão (entre 07:15 e 07:45)
    hora_atual = agora.hour
    minuto_atual = agora.minute
    horario_troca_plantao = (hora_atual == 7 and 15 <= minuto_atual <= 45)
    
    # Define se deve mostrar o aviso
    mostrar_aviso = False
    if not ultima_visita and horario_troca_plantao:
        mostrar_aviso = True
    elif ultima_visita:
        ultima_visita = datetime.fromisoformat(ultima_visita)
        # Se a última visita foi em um dia diferente e estamos no horário de troca
        if ultima_visita.date() != agora.date() and horario_troca_plantao:
            mostrar_aviso = True
    
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
        servidores = servidores.filter(
            Q(nome__icontains=query) |
            Q(numero_documento__icontains=query)
        )
    
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
    if len(query) >= 3:
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
    
    return JsonResponse({
        'data_hora': data_hora.isoformat(),
        'hora_entrada': data_hora.strftime('%H:%M') if registro.tipo_acesso == 'ENTRADA' else '-',
        'hora_saida': data_hora_saida.strftime('%H:%M') if data_hora_saida else '-',
        'tipo_acesso': registro.tipo_acesso,
        'servidor_nome': registro.servidor.nome
    })

@login_required
def registro_acesso_update(request, registro_id):
    if request.method == 'POST':
        try:
            # Obtém o registro do dashboard
            registro_dashboard = get_object_or_404(RegistroDashboard, id=registro_id)
            registro_historico = registro_dashboard.registro_historico
            
            # Obtém os dados do formulário
            data = request.POST.get('data')
            hora_entrada = request.POST.get('hora_entrada')
            hora_saida = request.POST.get('hora_saida')
            justificativa = request.POST.get('justificativa')
            
            if not justificativa:
                return JsonResponse({
                    'status': 'error',
                    'message': 'É necessário informar uma justificativa para editar o registro.'
                }, status=400)
            
            # Define o timezone UTC-4
            tz = pytz.timezone('America/Manaus')
            
            # Converte a data e hora para datetime
            data_base = datetime.strptime(data, '%Y-%m-%d').date()
            
            if hora_entrada and registro_historico.tipo_acesso == 'ENTRADA':
                hora_entrada = datetime.strptime(hora_entrada, '%H:%M').time()
                registro_historico.data_hora = tz.localize(datetime.combine(data_base, hora_entrada))
            
            if hora_saida:
                hora_saida = datetime.strptime(hora_saida, '%H:%M').time()
                registro_historico.data_hora_saida = tz.localize(datetime.combine(data_base, hora_saida))
                registro_historico.saida_pendente = False
            else:
                registro_historico.data_hora_saida = None
                registro_historico.saida_pendente = True
            
            registro_historico.save()
            
            # Atualiza o registro no dashboard
            registro_dashboard.data_hora = registro_historico.data_hora
            registro_dashboard.data_hora_saida = registro_historico.data_hora_saida
            registro_dashboard.saida_pendente = registro_historico.saida_pendente
            registro_dashboard.registro_historico = registro_historico
            registro_dashboard.save()
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

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
    plantao_atual = calcular_plantao_atual()
    inicio_plantao = plantao_atual['inicio']
    fim_plantao = plantao_atual['fim']
    
    registros = RegistroAcesso.objects.filter(
        data_hora__gte=inicio_plantao,
        data_hora__lte=fim_plantao
    ).select_related('servidor', 'operador', 'operador_saida').order_by('data_hora', 'id')
    
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    
    # Cria um DataFrame com os registros
    data = []
    for registro in registros:
        # Converte os horários para UTC-4
        data_hora = timezone.localtime(registro.data_hora, tz)
        data_hora_saida = timezone.localtime(registro.data_hora_saida, tz) if registro.data_hora_saida else None
        
        # Se for uma entrada normal
        if registro.tipo_acesso == 'ENTRADA':
            data.append({
                'ORD': len(data) + 1,
                'Plantão': plantao_atual['nome'],
                'Data': data_hora.strftime('%d/%m/%Y'),
                'Operador': registro.operador.get_full_name() or registro.operador.username,
                'Servidor': registro.servidor.nome,
                'Documento': registro.servidor.numero_documento,
                'Setor': registro.servidor.setor or '-',
                'Veículo': registro.veiculo if registro.veiculo and registro.veiculo.strip() else registro.servidor.veiculo if registro.servidor.veiculo and registro.servidor.veiculo.strip() else '-',
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': data_hora.strftime('%H:%M'),
                'Saída': data_hora_saida.strftime('%H:%M') if data_hora_saida else 'Pendente'
            })
        # Se for uma saída definitiva
        elif registro.tipo_acesso == 'SAIDA':
            data.append({
                'ORD': len(data) + 1,
                'Plantão': plantao_atual['nome'],
                'Data': data_hora.strftime('%d/%m/%Y'),
                'Operador': registro.operador.get_full_name() or registro.operador.username,
                'Servidor': f"Egresso: {registro.servidor.nome}" if not registro.servidor.nome.startswith('Egresso:') else registro.servidor.nome,
                'Documento': registro.servidor.numero_documento,
                'Setor': registro.setor or '-',  # Aqui estará a justificativa
                'Veículo': registro.veiculo if registro.veiculo and registro.veiculo.strip() else registro.servidor.veiculo if registro.servidor.veiculo and registro.servidor.veiculo.strip() else '-',
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': '-',
                'Saída': data_hora.strftime('%H:%M')
            })
    
    # Cria o DataFrame com as colunas na ordem especificada
    df = pd.DataFrame(data, columns=[
        'ORD', 'Plantão', 'Data', 'Operador', 'Servidor', 'Documento', 
        'Setor', 'Veículo', 'ISV', 'Entrada', 'Saída'
    ])
    
    # Cria o arquivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=plantao_{plantao_atual["nome"].lower()}_{timezone.localtime(timezone.now(), tz).strftime("%Y%m%d_%H%M")}.xlsx'
    
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
            # Decodifica o arquivo CSV
            decoded_file = arquivo.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            servidores_criados = 0
            servidores_atualizados = 0
            
            for row in reader:
                servidor, created = Servidor.objects.update_or_create(
                    numero_documento=row['Número do Documento'],
                    defaults={
                        'nome': row['Nome'],
                        'setor': row['Setor'],
                        'veiculo': row['Veículo'],
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
    
    writer = csv.writer(response)
    writer.writerow(['Nome', 'Número do Documento', 'Setor', 'Veículo'])
    writer.writerow(['João da Silva', '12.345.678-9', 'Administrativo', 'ABC-1234'])
    
    return response

@login_required
@admin_required
def limpar_banco_servidores(request):
    if request.method == 'POST':
        try:
            senha = request.POST.get('senha')
            
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
    Aceita o método GET para listar as faltas e também para exportar em PDF.
    """
    # Obtém o plantão atual
    plantao_atual = calcular_plantao_atual()
    nome_plantao = plantao_atual['nome']
    
    # Obtém o filtro de nome da query string
    filtro_nome = request.GET.get('nome', '').strip()
    
    # Busca todos os servidores do plantão atual verificando se o nome do plantão
    # está contido no campo setor (case insensitive)
    servidores_plantao = Servidor.objects.filter(
        setor__icontains=nome_plantao,
        ativo=True
    ).order_by('nome')
    
    # Para fins de debug, vamos registrar quantos servidores foram encontrados
    print(f"[DEBUG] Plantão atual: {nome_plantao}, Servidores encontrados: {servidores_plantao.count()}")
    
    # Aplica filtro por nome se fornecido
    if filtro_nome:
        servidores_plantao = servidores_plantao.filter(
            Q(nome__icontains=filtro_nome) |
            Q(numero_documento__icontains=filtro_nome)
        )
    
    # Busca os servidores que já entraram hoje
    hoje = timezone.now().date()
    servidores_presentes = RegistroDashboard.objects.filter(
        data_hora__date=hoje,
        tipo_acesso='ENTRADA'
    ).values_list('servidor_id', flat=True)
    
    # Lista de faltosos (servidores do plantão que não entraram)
    faltosos = []
    for servidor in servidores_plantao:
        if servidor.id not in servidores_presentes:
            faltosos.append({
                'ord': len(faltosos) + 1,  # Adiciona número de ordem
                'nome': servidor.nome,
                'documento': servidor.numero_documento,
                'setor': servidor.setor
            })
    
    # Ordena a lista de faltosos por nome
    faltosos.sort(key=lambda x: x['nome'])
    
    # Atualiza os números de ordem após a ordenação
    for i, faltoso in enumerate(faltosos, 1):
        faltoso['ord'] = i
    
    # Se for solicitado PDF
    if request.GET.get('format') == 'pdf':
        # Cria um buffer para o PDF
        buffer = BytesIO()
        
        # Cria o documento PDF
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Define estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Centralizado
        )
        
        # Adiciona título
        title = Paragraph(f"Faltas do Plantão {plantao_atual['nome']}", title_style)
        elements.append(title)
        
        # Adiciona data e hora
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=1  # Centralizado
        )
        current_datetime = timezone.localtime().strftime("%d/%m/%Y %H:%M:%S")
        date_paragraph = Paragraph(f"Gerado em: {current_datetime}", date_style)
        elements.append(date_paragraph)
        
        if faltosos:
            # Prepara dados da tabela
            table_data = [['ORD', 'Nome', 'Documento']]  # Cabeçalho
            for faltoso in faltosos:
                table_data.append([
                    str(faltoso['ord']),
                    faltoso['nome'],
                    faltoso['documento']
                ])
            
            # Cria a tabela
            table = Table(table_data, colWidths=[50, 350, 150])
            
            # Estilo da tabela
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Centraliza coluna ORD
                ('ALIGN', (1, 0), (-1, -1), 'LEFT'),  # Alinha à esquerda as outras colunas
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)
        else:
            # Mensagem quando não há faltosos
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=12,
                spaceAfter=20,
                alignment=1
            )
            no_data = Paragraph("Não há faltas registradas para o plantão atual!", no_data_style)
            elements.append(no_data)
        
        # Gera o PDF
        doc.build(elements)
        
        # Prepara a resposta
        buffer.seek(0)
        filename = f"faltas_plantao_{plantao_atual['nome'].replace(' ', '_')}_{hoje.strftime('%Y%m%d')}.pdf"
        
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type='application/pdf'
        )
    
    # Retorna JSON para requisição normal
    return JsonResponse({
        'plantao_atual': plantao_atual['nome'],
        'faltosos': faltosos,
        'total': len(faltosos)
    })

@login_required
def ambiente_treinamento(request):
    """View principal do ambiente de treinamento."""
    # Define o timezone UTC-4
    tz = pytz.timezone('America/Manaus')
    agora = timezone.now()
    
    # Obtém o plantão atual
    plantao_atual = calcular_plantao_atual()
    
    # Obtém os registros do plantão atual
    registros = RegistroAcessoTreinamento.objects.filter(
        data_hora__date=agora.date()
    ).select_related('servidor', 'operador', 'operador_saida')
    
    # Calcula os totais
    total_entradas = registros.filter(tipo_acesso='ENTRADA').count()
    total_saidas = registros.filter(tipo_acesso='SAIDA').count()
    total_pendentes = registros.filter(saida_pendente=True).count()
    
    context = {
        'plantao_atual': plantao_atual,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_pendentes': total_pendentes,
        'registros': registros,
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
    
    if len(query) < 3:
        print(f"[DEBUG TREINAMENTO] Query muito curta, retornando erro")
        return JsonResponse({
            'status': 'error',
            'message': 'Digite pelo menos 3 caracteres para buscar.'
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
        try:
            # Obtém os dados do formulário
            servidor_id = request.POST.get('servidor')
            tipo_acesso = request.POST.get('tipo_acesso')
            isv = request.POST.get('isv') == 'on'
            
            # Obtém o servidor original
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
            
            # Define o timezone UTC-4
            tz = pytz.timezone('America/Manaus')
            agora = timezone.now()
            
            # Verifica se já existe uma entrada sem saída
            if tipo_acesso == 'ENTRADA':
                entrada_pendente = RegistroAcessoTreinamento.objects.filter(
                    servidor=servidor_treinamento,
                    saida_pendente=True
                ).exists()
                
                if entrada_pendente:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Este servidor já possui uma entrada sem saída registrada.'
                    }, status=400)
            
            # Cria o registro
            registro = RegistroAcessoTreinamento.objects.create(
                servidor=servidor_treinamento,
                operador=request.user,
                tipo_acesso=tipo_acesso,
                data_hora=agora,
                isv=isv,
                veiculo=servidor_treinamento.veiculo,
                setor=servidor_treinamento.setor,
                saida_pendente=(tipo_acesso == 'ENTRADA')
            )
            
            return JsonResponse({
                'status': 'success',
                'message': f'{tipo_acesso.title()} registrada com sucesso!'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido'
    }, status=405)

@login_required
def registro_manual_treinamento_create(request):
    """View para criar registros manuais no ambiente de treinamento."""
    if request.method == 'POST':
        servidor_id = request.POST.get('servidor')
        tipo_acesso = request.POST.get('tipo_acesso')
        data_hora = request.POST.get('data_hora')
        observacao = request.POST.get('observacao', '')
        isv = request.POST.get('isv') == 'on'
        
        servidor = get_object_or_404(ServidorTreinamento, id=servidor_id)
        
        try:
            data_hora = timezone.make_aware(datetime.strptime(data_hora, '%Y-%m-%dT%H:%M'))
        except ValueError:
            messages.error(request, 'Data/hora inválida.')
            return redirect('ambiente_treinamento')
        
        RegistroAcessoTreinamento.objects.create(
            servidor=servidor,
            operador=request.user,
            tipo_acesso=tipo_acesso,
            data_hora=data_hora,
            observacao=observacao,
            isv=isv,
            veiculo=servidor.veiculo,
            setor=servidor.setor,
            saida_pendente=tipo_acesso == 'ENTRADA'
        )
        
        messages.success(request, 'Registro manual criado com sucesso!')
        return redirect('ambiente_treinamento')
    
    return redirect('ambiente_treinamento')

@login_required
def saida_definitiva_treinamento(request):
    """View para registrar saída definitiva no ambiente de treinamento."""
    if request.method == 'POST':
        try:
            # Obtém os dados do formulário
            servidor_id = request.POST.get('servidor_id')
            observacao = request.POST.get('observacao')
            
            # Obtém o servidor
            servidor = get_object_or_404(ServidorTreinamento, id=servidor_id)
            
            # Define o timezone UTC-4
            tz = pytz.timezone('America/Manaus')
            agora = timezone.now()
            
            # Cria o registro de saída
            registro = RegistroAcessoTreinamento.objects.create(
                servidor=servidor,
                operador=request.user,
                tipo_acesso='SAIDA',
                data_hora=agora,
                observacao=observacao
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Saída definitiva registrada com sucesso.'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

@login_required
def limpar_dashboard_treinamento(request):
    """View para limpar todos os registros do ambiente de treinamento."""
    if request.method == 'POST':
        try:
            print(f"\n\n[DEBUG TREINAMENTO] ======= INÍCIO LIMPEZA DASHBOARD =======")
            print(f"[DEBUG TREINAMENTO] Requisição recebida de: {request.user}")
            print(f"[DEBUG TREINAMENTO] Método HTTP: {request.method}")
            print(f"[DEBUG TREINAMENTO] Path: {request.path}")
            print(f"[DEBUG TREINAMENTO] Corpo da requisição: {request.body.decode('utf-8')[:100]}")
            print(f"[DEBUG TREINAMENTO] Headers: {dict(request.headers)}")
            
            # Verificar CSRF token
            csrf_token = request.headers.get('X-CSRFToken')
            print(f"[DEBUG TREINAMENTO] CSRF Token: {csrf_token}")
            
            # Contagem de registros antes da exclusão
            total_registros_antes = RegistroAcessoTreinamento.objects.count()
            total_servidores_antes = ServidorTreinamento.objects.count()
            print(f"[DEBUG TREINAMENTO] Registros antes da limpeza: {total_registros_antes}")
            print(f"[DEBUG TREINAMENTO] Servidores antes da limpeza: {total_servidores_antes}")
            
            # Limpa todos os registros de acesso
            print(f"[DEBUG TREINAMENTO] Excluindo registros de acesso")
            RegistroAcessoTreinamento.objects.all().delete()
            
            # Contagem após exclusão de registros
            total_registros_depois = RegistroAcessoTreinamento.objects.count()
            print(f"[DEBUG TREINAMENTO] Registros após exclusão: {total_registros_depois}")
            print(f"[DEBUG TREINAMENTO] {total_registros_antes - total_registros_depois} registros excluídos")
            
            # Limpa todos os servidores de treinamento
            print(f"[DEBUG TREINAMENTO] Excluindo servidores")
            ServidorTreinamento.objects.all().delete()
            
            # Contagem após exclusão de servidores
            total_servidores_depois = ServidorTreinamento.objects.count()
            print(f"[DEBUG TREINAMENTO] Servidores após exclusão: {total_servidores_depois}")
            print(f"[DEBUG TREINAMENTO] {total_servidores_antes - total_servidores_depois} servidores excluídos")
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='RegistroAcessoTreinamento',
                objeto_id=0,
                detalhes=f'Limpeza do ambiente de treinamento: {total_registros_antes} registros e {total_servidores_antes} servidores excluídos'
            )
            print(f"[DEBUG TREINAMENTO] Log de auditoria registrado")
            
            # Prepara a resposta
            resposta = {
                'status': 'success',
                'message': 'Ambiente de treinamento limpo com sucesso.',
                'detalhes': {
                    'registros_excluidos': total_registros_antes,
                    'servidores_excluidos': total_servidores_antes
                }
            }
            
            print(f"[DEBUG TREINAMENTO] Resposta preparada com sucesso")
            print(f"[DEBUG TREINAMENTO] Chaves na resposta: {resposta.keys()}")
            print(f"[DEBUG TREINAMENTO] ======= FIM LIMPEZA DASHBOARD =======\n\n")
            
            return JsonResponse(resposta)
            
        except Exception as e:
            import traceback
            print(f"[ERRO TREINAMENTO] Erro ao limpar dashboard: {str(e)}")
            print(f"[ERRO TREINAMENTO] Traceback:")
            traceback.print_exc()
            
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao limpar dashboard: {str(e)}'
            }, status=500)
    
    print(f"[ERRO TREINAMENTO] Método não permitido: {request.method}")
    return JsonResponse({
        'status': 'error',
        'message': f'Método não permitido: {request.method}'
    }, status=405)

@login_required
def exportar_excel_treinamento(request):
    """View para exportar os dados do ambiente de treinamento para Excel."""
    try:
        print(f"\n\n[DEBUG TREINAMENTO] ======= INÍCIO EXPORTAÇÃO EXCEL =======")
        print(f"[DEBUG TREINAMENTO] Requisição recebida de: {request.user}")
        print(f"[DEBUG TREINAMENTO] Método HTTP: {request.method}")
        print(f"[DEBUG TREINAMENTO] Path: {request.path}")
        print(f"[DEBUG TREINAMENTO] GET params: {dict(request.GET)}")
        
        # Define o timezone UTC-4
        tz = pytz.timezone('America/Manaus')
        agora = timezone.now()
        print(f"[DEBUG TREINAMENTO] Data/hora atual (UTC): {agora}")
        print(f"[DEBUG TREINAMENTO] Data/hora atual (local): {timezone.localtime(agora, tz)}")
        
        print(f"[DEBUG TREINAMENTO] Criando dados de exemplo para o Excel")
        # Cria uma lista de dados de exemplo
        dados = [
            {
                'ORD': 1,
                'Operador': 'MARIA SILVA',
                'Servidor': 'JOÃO SANTOS',
                'Documento': '12345678900',
                'Setor': 'ADMINISTRATIVO',
                'Veículo': 'ABC-1234',
                'ISV': 'Sim',
                'Entrada': f"{agora.strftime('%d/%m/%Y')} 07:15",
                'Saída': f"{agora.strftime('%d/%m/%Y')} 17:00"
            },
            {
                'ORD': 2,
                'Operador': 'PEDRO OLIVEIRA',
                'Servidor': 'CARLOS FERREIRA',
                'Documento': '98765432100',
                'Setor': 'MANUTENÇÃO',
                'Veículo': '-',
                'ISV': 'Não',
                'Entrada': f"{agora.strftime('%d/%m/%Y')} 08:00",
                'Saída': f"{agora.strftime('%d/%m/%Y')} 16:30"
            },
            {
                'ORD': 3,
                'Operador': 'ANA COSTA',
                'Servidor': 'MARCOS SOUZA',
                'Documento': '45678912300',
                'Setor': 'SEGURANÇA',
                'Veículo': 'XYZ-9876',
                'ISV': 'Não',
                'Entrada': f"{agora.strftime('%d/%m/%Y')} 09:00",
                'Saída': 'Pendente'
            },
            {
                'ORD': 4,
                'Operador': 'JOSÉ PEREIRA',
                'Servidor': 'Egresso: LUCAS LIMA',
                'Documento': '78912345600',
                'Setor': 'Alvará de Soltura',
                'Veículo': '-',
                'ISV': 'Não',
                'Entrada': '-',
                'Saída': f"{agora.strftime('%d/%m/%Y')} 10:45"
            },
            {
                'ORD': 5,
                'Operador': 'MARIA SILVA',
                'Servidor': 'PATRICIA ROCHA',
                'Documento': '32165498700',
                'Setor': 'JURÍDICO',
                'Veículo': 'DEF-5678',
                'ISV': 'Sim',
                'Entrada': f"{agora.strftime('%d/%m/%Y')} 13:00",
                'Saída': f"{agora.strftime('%d/%m/%Y')} 18:00"
            }
        ]
        
        print(f"[DEBUG TREINAMENTO] Criando DataFrame pandas com {len(dados)} linhas")
        # Cria um DataFrame com os dados
        df = pd.DataFrame(dados)
        
        # Define a ordem das colunas
        colunas = [
            'ORD', 'Operador', 'Servidor', 'Documento', 'Setor', 'Veículo', 'ISV', 'Entrada', 'Saída'
        ]
        df = df[colunas]
        print(f"[DEBUG TREINAMENTO] DataFrame criado com sucesso, colunas: {', '.join(colunas)}")
        
        print(f"[DEBUG TREINAMENTO] Criando resposta HTTP para download do Excel")
        # Cria a resposta Excel
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=exemplo_planilha_controle_acesso.xlsx'
        
        print(f"[DEBUG TREINAMENTO] Salvando DataFrame no Excel")
        # Salva o DataFrame no Excel
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Registros')
            
            print(f"[DEBUG TREINAMENTO] Ajustando largura das colunas")
            # Ajusta a largura das colunas
            worksheet = writer.sheets['Registros']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(str(col))
                )
                worksheet.column_dimensions[get_column_letter(idx + 1)].width = max_length + 2
        
        print(f"[DEBUG TREINAMENTO] Excel gerado com sucesso")
        print(f"[DEBUG TREINAMENTO] ======= FIM EXPORTAÇÃO EXCEL =======\n\n")
        
        return response
        
    except Exception as e:
        import traceback
        print(f"[ERRO TREINAMENTO] Erro ao exportar Excel: {str(e)}")
        print(f"[ERRO TREINAMENTO] Traceback:")
        traceback.print_exc()
        
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao exportar Excel: {str(e)}'
        }, status=500)

@login_required
def registro_acesso_treinamento_update(request, registro_id):
    """View para atualizar um registro de acesso no ambiente de treinamento."""
    if request.method == 'POST':
        try:
            # Obtém os dados do formulário
            data_entrada = request.POST.get('data_entrada')
            hora_entrada = request.POST.get('hora_entrada')
            data_saida = request.POST.get('data_saida')
            hora_saida = request.POST.get('hora_saida')
            isv = request.POST.get('isv') == 'on'
            justificativa = request.POST.get('justificativa', 'Treinamento')  # Valor padrão se não for fornecido
            
            # Debug completo dos dados recebidos
            print(f"[DEBUG] ======= INÍCIO DA EDIÇÃO DE REGISTRO {registro_id} =======")
            print(f"[DEBUG] Dados brutos recebidos do formulário:")
            print(f"[DEBUG] data_entrada={data_entrada}, hora_entrada={hora_entrada}")
            print(f"[DEBUG] data_saida={data_saida}, hora_saida={hora_saida}")
            print(f"[DEBUG] isv={isv}, justificativa={justificativa}")
            
            # Obtém o registro a ser atualizado
            registro = get_object_or_404(RegistroAcessoTreinamento, id=registro_id)
            
            # Log estado atual do registro antes da atualização
            print(f"[DEBUG] Estado ATUAL do registro antes da atualização:")
            print(f"[DEBUG] ID: {registro.id}, Tipo: {registro.tipo_acesso}")
            print(f"[DEBUG] Data/Hora Entrada: {registro.data_hora}")
            print(f"[DEBUG] Data/Hora Saída: {registro.data_hora_saida}")
            print(f"[DEBUG] Saída Pendente: {registro.saida_pendente}")
            
            # Salva os valores originais para comparação
            data_hora_original = registro.data_hora
            data_hora_saida_original = registro.data_hora_saida
            
            # Define o timezone UTC-4
            tz = pytz.timezone('America/Manaus')
            
            # PROCESSAMENTO DE ENTRADA - Somente se ambos os campos estão preenchidos
            if data_entrada and hora_entrada:
                try:
                    # Combina data e hora de entrada (formato esperado: YYYY-MM-DD HH:MM)
                    data_hora_str = f"{data_entrada} {hora_entrada}"
                    print(f"[DEBUG] String de data/hora entrada para parsing: '{data_hora_str}'")
                    
                    # Parse da data e hora
                    data_hora_dt = datetime.strptime(data_hora_str, '%Y-%m-%d %H:%M')
                    print(f"[DEBUG] Data/hora entrada após parsing: {data_hora_dt}")
                    
                    # Adiciona timezone
                    data_hora_tz = tz.localize(data_hora_dt)
                    print(f"[DEBUG] Data/hora entrada com timezone: {data_hora_tz}")
                    
                    # Atualiza APENAS a data/hora de entrada do registro
                    registro.data_hora = data_hora_tz
                    print(f"[DEBUG] Registro com nova data/hora de entrada: {registro.data_hora}")
                    
                    # Verifica se a data foi realmente alterada
                    if data_hora_original != registro.data_hora:
                        print(f"[DEBUG] Data/hora de entrada foi alterada: {data_hora_original} -> {registro.data_hora}")
                    else:
                        print(f"[DEBUG] Data/hora de entrada permanece a mesma")
                    
                except Exception as e:
                    import traceback
                    print(f"[ERRO] Falha ao processar data/hora de entrada: {str(e)}")
                    traceback.print_exc()
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Erro ao processar a data/hora de entrada: {str(e)}"
                    }, status=400)
            else:
                print("[ERRO] Data ou hora de entrada não informada. Ambas são obrigatórias.")
                return JsonResponse({
                    'status': 'error',
                    'message': "Data e hora de entrada são obrigatórias."
                }, status=400)
            
            # PROCESSAMENTO DE SAÍDA - Lógica completamente separada da entrada
            # Se ambos os campos de saída estão preenchidos, atualiza a saída
            if data_saida and hora_saida:
                try:
                    # Combina data e hora de saída (formato esperado: YYYY-MM-DD HH:MM)
                    data_hora_saida_str = f"{data_saida} {hora_saida}"
                    print(f"[DEBUG] String de data/hora saída para parsing: '{data_hora_saida_str}'")
                    
                    # Parse da data e hora
                    data_hora_saida_dt = datetime.strptime(data_hora_saida_str, '%Y-%m-%d %H:%M')
                    print(f"[DEBUG] Data/hora saída após parsing: {data_hora_saida_dt}")
                    
                    # Adiciona timezone
                    data_hora_saida_tz = tz.localize(data_hora_saida_dt)
                    print(f"[DEBUG] Data/hora saída com timezone: {data_hora_saida_tz}")
                    
                    # Atualiza APENAS os campos relacionados à saída
                    registro.data_hora_saida = data_hora_saida_tz
                    registro.operador_saida = request.user
                    registro.saida_pendente = False
                    print(f"[DEBUG] Registro com nova data/hora de saída: {registro.data_hora_saida}")
                    
                    # Verifica se a data de saída foi realmente alterada
                    if data_hora_saida_original != registro.data_hora_saida:
                        print(f"[DEBUG] Data/hora de saída foi alterada: {data_hora_saida_original} -> {registro.data_hora_saida}")
                    else:
                        print(f"[DEBUG] Data/hora de saída permanece a mesma")
                    
                # Se ocorrer erro no processamento da saída, continua sem saída
                except Exception as e:
                    import traceback
                    print(f"[ERRO] Falha ao processar data/hora de saída: {str(e)}")
                    traceback.print_exc()
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Erro ao processar a data/hora de saída: {str(e)}"
                    }, status=400)
            
            # Se ambos os campos de saída estão vazios, limpa a saída
            elif not data_saida and not hora_saida:
                print("[DEBUG] Ambos os campos de saída estão vazios, limpando dados de saída")
                
                # Só registra alteração se havia uma saída antes
                if registro.data_hora_saida is not None:
                    print(f"[DEBUG] Removendo data/hora de saída: {registro.data_hora_saida} -> None")
                    registro.data_hora_saida = None
                    registro.operador_saida = None
                    registro.saida_pendente = True
                else:
                    print(f"[DEBUG] Data/hora de saída já era None, mantendo")
            
            # Se apenas um dos campos está preenchido, retorna erro
            elif (data_saida and not hora_saida) or (not data_saida and hora_saida):
                missing = "hora" if not hora_saida else "data"
                print(f"[ERRO] Campo de saída incompleto. Faltando: {missing}")
                return JsonResponse({
                    'status': 'error',
                    'message': f"Para registrar uma saída, preencha tanto a data quanto a hora. Campo faltando: {missing}"
                }, status=400)
            
            # Atualiza os outros campos
            registro.isv = isv
            registro.observacao = justificativa
            
            # Salva as alterações
            registro.save()
            
            # Log do estado final após a atualização
            print(f"[DEBUG] Estado FINAL do registro após atualização:")
            print(f"[DEBUG] ID: {registro.id}")
            print(f"[DEBUG] Data/Hora Entrada: {registro.data_hora}")
            print(f"[DEBUG] Data/Hora Saída: {registro.data_hora_saida}")
            print(f"[DEBUG] Saída Pendente: {registro.saida_pendente}")
            print(f"[DEBUG] ======= FIM DA EDIÇÃO DE REGISTRO {registro_id} =======")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Registro atualizado com sucesso!'
            })
            
        except Exception as e:
            import traceback
            print(f"[ERRO] Exceção não tratada ao atualizar registro: {str(e)}")
            traceback.print_exc()
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Método não permitido'
    }, status=405)

@login_required
def excluir_registro_treinamento(request, registro_id):
    """View para excluir registros no ambiente de treinamento."""
    if request.method == 'POST':
        try:
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
    """View para registrar saída no ambiente de treinamento."""
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
            
            # Obtém os dados do formulário
            observacao = request.POST.get('observacao')
            
            # Define o timezone UTC-4
            tz = pytz.timezone('America/Manaus')
            agora = timezone.now()
            
            # Atualiza o registro
            registro.data_hora_saida = agora
            registro.operador_saida = request.user
            registro.observacao_saida = observacao
            registro.saida_pendente = False
            registro.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Saída registrada com sucesso.'
            })
            
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
        perfil = PerfilUsuario(usuario=user)
    
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
    if request.method == 'POST':
        senha_atual = request.POST.get('senha_atual')
        nova_senha = request.POST.get('nova_senha')
        confirmar_senha = request.POST.get('confirmar_senha')
        
        # Validações básicas
        if not senha_atual or not nova_senha or not confirmar_senha:
            messages.error(request, 'Todos os campos são obrigatórios.')
            return redirect('trocar_senha')
        
        if nova_senha != confirmar_senha:
            messages.error(request, 'A nova senha e a confirmação não coincidem.')
            return redirect('trocar_senha')
        
        if len(nova_senha) < 8:
            messages.error(request, 'A nova senha deve ter pelo menos 8 caracteres.')
            return redirect('trocar_senha')
        
        # Verifica se a senha atual está correta
        if not request.user.check_password(senha_atual):
            messages.error(request, 'Senha atual incorreta.')
            return redirect('trocar_senha')
        
        # Altera a senha
        request.user.set_password(nova_senha)
        request.user.save()
        
        # Atualiza o perfil do usuário
        try:
            perfil = request.user.perfil
            perfil.precisa_trocar_senha = False
            perfil.senha_temporaria = None  # Limpa a senha temporária
            perfil.save()
        except Exception as e:
            # Se houver erro ao atualizar o perfil, registra o erro mas permite continuar
            logging.getLogger('django').error(f"Erro ao atualizar perfil após troca de senha: {str(e)}")
        
        messages.success(request, 'Senha alterada com sucesso! Por favor, faça login novamente.')
        return redirect('login')
    
    return render(request, 'core/trocar_senha.html')

