from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, FileResponse
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, DateTimeField, Subquery, OuterRef
from django.utils import timezone
from datetime import datetime, timedelta, date
import pandas as pd
from .models import RegistroAcesso, LogAuditoria, Servidor, RegistroDashboard
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

def is_staff(user):
    return user.is_staff

@login_required
def home(request):
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
                'hora_entrada': data_hora.strftime('%H:%M'),
                'hora_saida': data_hora_saida.strftime('%H:%M') if data_hora_saida else None,
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
                'hora_saida': data_hora.strftime('%H:%M'),
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
            hora_entrada = datetime.strptime(hora_entrada, '%H:%M').time()
            data_hora = tz.localize(datetime.combine(data_base, hora_entrada))
            
            # Cria uma cópia do registro histórico com as alterações
            novo_registro = RegistroAcesso.objects.create(
                servidor=registro_historico.servidor,
                operador=registro_historico.operador,
                tipo_acesso=registro_historico.tipo_acesso,
                observacao=registro_historico.observacao,
                observacao_saida=registro_historico.observacao_saida,
                isv=registro_historico.isv,
                veiculo=registro_historico.veiculo,
                setor=registro_historico.setor,
                data_hora=data_hora,
                operador_saida=registro_historico.operador_saida,
                registro_original=registro_historico,
                status_alteracao='EDITADO',
                data_hora_alteracao=timezone.now(),
                justificativa=justificativa
            )
            
            # Processa hora de saída
            if hora_saida:
                hora_saida = datetime.strptime(hora_saida, '%H:%M').time()
                data_hora_saida = tz.localize(datetime.combine(data_base, hora_saida))
                novo_registro.data_hora_saida = data_hora_saida
                novo_registro.saida_pendente = False
            else:
                novo_registro.data_hora_saida = None
                novo_registro.saida_pendente = True
            
            novo_registro.save()
            
            # Atualiza o registro no dashboard
            registro_dashboard.data_hora = novo_registro.data_hora
            registro_dashboard.data_hora_saida = novo_registro.data_hora_saida
            registro_dashboard.saida_pendente = novo_registro.saida_pendente
            registro_dashboard.registro_historico = novo_registro
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
    users = User.objects.all().order_by('username')
    return render(request, 'core/user_list.html', {'users': users})

@login_required
@user_passes_test(is_staff)
def user_create(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        is_staff = request.POST.get('is_staff') == 'on'
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Nome de usuário já existe!')
            return redirect('user_create')
        
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff
        )
        
        messages.success(request, 'Usuário criado com sucesso!')
        return redirect('user_list')
    
    return render(request, 'core/user_form.html', {'usuario': None})

@login_required
@user_passes_test(is_staff)
def user_update(request, pk):
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
@user_passes_test(is_staff)
def user_delete(request, pk):
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

@login_required
def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def limpar_historico(request):
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
        # Converte os horários para UTC-4
        data_hora = registro.data_hora.astimezone(tz)
        data_hora_saida = registro.data_hora_saida.astimezone(tz) if registro.data_hora_saida else None
        data_hora_alteracao = registro.data_hora_alteracao.astimezone(tz) if registro.data_hora_alteracao else None
        
        # Determina o plantão usando a função calcular_plantao_atual
        plantao_registro = calcular_plantao_atual(data_hora)['nome']
        
        registros_formatados.append({
            'id': registro.id,
            'plantao': plantao_registro,
            'data_hora': data_hora,
            'operador': registro.operador.get_full_name() or registro.operador.username,
            'servidor': registro.servidor.nome,
            'numero_documento': registro.servidor.numero_documento,
            'setor': registro.servidor.setor or '-',
            'veiculo': registro.veiculo if registro.veiculo and registro.veiculo.strip() else registro.servidor.veiculo if registro.servidor.veiculo and registro.servidor.veiculo.strip() else '-',
            'isv': 'Sim' if registro.isv else 'Não',
            'entrada': data_hora.strftime('%H:%M') if registro.tipo_acesso == 'ENTRADA' else '-',
            'observacao': registro.observacao or '-',
            'saida': data_hora_saida.strftime('%H:%M') if data_hora_saida else '-',
            'observacao_saida': registro.observacao_saida or '-',
            'status_alteracao': registro.status_alteracao or 'Original',
            'data_hora_alteracao': data_hora_alteracao.strftime('%d/%m/%Y %H:%M') if data_hora_alteracao else '-',
            'justificativa': registro.justificativa or '-'
        })
    
    # Se for solicitado exportar para Excel
    if request.GET.get('export') == 'excel':
        # Cria um DataFrame com os registros já formatados
        df = pd.DataFrame(registros_formatados)
        
        # Remove a coluna ID que é usada apenas internamente
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
        df['Data'] = df['Data'].apply(lambda x: x.strftime('%d/%m/%Y'))
        
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
@admin_required
def limpar_dashboard(request):
    if request.method == 'POST':
        try:
            senha = request.POST.get('senha')
            
            # Verifica se a senha está correta
            if not request.user.check_password(senha):
                messages.error(request, 'Senha incorreta!')
                return redirect('home')
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='RegistroDashboard',
                objeto_id=0,
                detalhes='Limpeza do dashboard (mantendo registros pendentes)'
            )
            
            # Exclui todos os registros do dashboard EXCETO os que têm saída pendente
            # Isso inclui registros com saída já registrada E saídas definitivas
            RegistroDashboard.objects.filter(
                Q(saida_pendente=False) | Q(tipo_acesso='SAIDA')
            ).delete()
            
            messages.success(request, 'Dashboard limpo com sucesso! (Registros com saída pendente foram mantidos)')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Erro ao limpar dashboard: {str(e)}')
            return redirect('home')
    
    return redirect('home')

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
    # Obtém o plantão atual
    plantao_atual = calcular_plantao_atual()
    
    # Obtém o filtro de nome da query string
    filtro_nome = request.GET.get('nome', '').strip()
    
    # Busca todos os servidores do plantão atual (case insensitive e variações do nome)
    servidores_plantao = Servidor.objects.filter(
        Q(setor__icontains='DELTA') |  # DELTA
        Q(setor__icontains='Plantão DELTA') |  # Plantão DELTA
        Q(setor__icontains='PLANTAO DELTA') |  # PLANTAO DELTA
        Q(setor__icontains='Plantao DELTA'),  # Plantao DELTA
        ativo=True
    ).order_by('nome')
    
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
            table_data = [['ORD', 'Nome', 'Documento', 'Setor']]  # Cabeçalho
            for faltoso in faltosos:
                table_data.append([
                    str(faltoso['ord']),
                    faltoso['nome'],
                    faltoso['documento'],
                    faltoso['setor']
                ])
            
            # Cria a tabela
            table = Table(table_data, colWidths=[50, 200, 100, 150])
            
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
