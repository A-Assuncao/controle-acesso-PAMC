from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, DateTimeField
from django.utils import timezone
from datetime import datetime, timedelta
import pandas as pd
from .models import RegistroAcesso, LogAuditoria, Servidor
from .forms import RegistroAcessoForm, ServidorForm
from .utils import calcular_plantao_atual, determinar_tipo_acesso, verificar_plantao_servidor, verificar_saida_pendente
from .decorators import admin_required
from django.contrib.auth.models import User
import json
import csv
import pytz
from io import BytesIO

def is_staff(user):
    return user.is_staff

@login_required
def home(request):
    plantao_atual = calcular_plantao_atual()
    
    # Filtra registros do plantão atual
    registros = RegistroAcesso.objects.filter(
        data_hora__gte=plantao_atual['inicio'],
        data_hora__lte=plantao_atual['fim'],
        tipo_acesso='ENTRADA'
    ).select_related('servidor', 'operador')
    
    # Calcula totais para os cards
    total_entradas = registros.count()  # Total de entradas
    total_saidas = registros.filter(data_hora_saida__isnull=False).count()  # Entradas que já têm saída
    total_pendentes = registros.filter(saida_pendente=True).count()  # Entradas sem saída
    
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
        entrada_pendente = RegistroAcesso.objects.filter(
            servidor=servidor,
            data_hora__gte=plantao_atual['inicio'],
            data_hora__lte=plantao_atual['fim'],
            tipo_acesso='ENTRADA',
            saida_pendente=True
        ).exists()
        
        if tipo_acesso == 'ENTRADA':
            if entrada_pendente:
                messages.error(request, 'Este servidor já possui uma entrada sem saída registrada. Registre a saída antes de fazer uma nova entrada.')
                return redirect('home')
            
            # Cria um novo registro de entrada
            registro = RegistroAcesso.objects.create(
                servidor=servidor,
                operador=request.user,
                tipo_acesso='ENTRADA',
                observacao=observacao,
                isv=isv,
                saida_pendente=True,
                status_alteracao='ORIGINAL'
            )
            
            messages.success(request, 'Entrada registrada com sucesso!')
            return redirect('home')
            
        elif tipo_acesso == 'SAIDA':
            if not entrada_pendente:
                messages.error(request, 'Não foi encontrada uma entrada sem saída para este servidor. Registre uma entrada primeiro.')
                return redirect('home')
            
            # Procura a última entrada sem saída
            ultima_entrada = RegistroAcesso.objects.filter(
                servidor=servidor,
                data_hora__gte=plantao_atual['inicio'],
                data_hora__lte=plantao_atual['fim'],
                tipo_acesso='ENTRADA',
                saida_pendente=True,
                data_hora_saida__isnull=True
            ).first()
            
            # Atualiza a entrada com os dados da saída
            ultima_entrada.data_hora_saida = timezone.now()
            ultima_entrada.operador_saida = request.user
            ultima_entrada.observacao_saida = observacao
            ultima_entrada.saida_pendente = False
            ultima_entrada.save()
            
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
    plantao_atual = calcular_plantao_atual()
    registros = RegistroAcesso.objects.filter(
        data_hora__gte=plantao_atual['inicio'],
        data_hora__lte=plantao_atual['fim'],
        status_alteracao__in=['ORIGINAL', 'EDITADO']  # Mostra apenas registros originais e editados
    ).select_related('servidor', 'operador', 'operador_saida').order_by('data_hora', 'id')
    
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
                'hora_saida': data_hora_saida.strftime('%H:%M') if data_hora_saida else None
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
                'hora_saida': data_hora.strftime('%H:%M')
            })
    
    return JsonResponse(data, safe=False)

@login_required
def registro_detalhe(request, registro_id):
    """Retorna os detalhes de um registro para edição."""
    registro = get_object_or_404(RegistroAcesso, id=registro_id)
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
            registro = get_object_or_404(RegistroAcesso, id=registro_id)
            
            # Verifica se a justificativa foi fornecida
            justificativa = request.POST.get('justificativa')
            if not justificativa:
                return JsonResponse({
                    'status': 'error',
                    'message': 'É necessário informar uma justificativa para editar o registro.'
                }, status=400)
            
            # Converte a data e hora para datetime
            data_base = datetime.strptime(request.POST.get('data'), '%Y-%m-%d')
            tz = pytz.timezone('America/Manaus')
            
            # Cria uma cópia do registro original com as novas informações
            novo_registro = RegistroAcesso.objects.create(
                servidor=registro.servidor,
                operador=request.user,
                tipo_acesso=registro.tipo_acesso,
                observacao=registro.observacao,
                isv=registro.isv,
                veiculo=registro.veiculo,
                setor=registro.setor,
                registro_original=registro,
                status_alteracao='EDITADO',
                data_hora_alteracao=timezone.now(),
                justificativa=justificativa,
                data_hora=registro.data_hora  # Mantém a data/hora original
            )
            
            # Processa hora de entrada
            hora_entrada = request.POST.get('hora_entrada')
            if hora_entrada and registro.tipo_acesso == 'ENTRADA':
                hora_entrada = datetime.strptime(hora_entrada, '%H:%M').time()
                data_hora = tz.localize(datetime.combine(data_base.date(), hora_entrada))
                novo_registro.data_hora = data_hora
                novo_registro.data_hora_manual = data_hora
            
            # Processa hora de saída
            hora_saida = request.POST.get('hora_saida')
            if hora_saida:
                hora_saida = datetime.strptime(hora_saida, '%H:%M').time()
                data_hora_saida = tz.localize(datetime.combine(data_base.date(), hora_saida))
                novo_registro.data_hora_saida = data_hora_saida
                novo_registro.saida_pendente = False
            else:
                novo_registro.data_hora_saida = None
                novo_registro.saida_pendente = True
            
            novo_registro.save()
            
            # Atualiza o registro no dashboard (mantém o original no histórico)
            if registro.data_hora >= calcular_plantao_atual()['inicio'] and registro.data_hora <= calcular_plantao_atual()['fim']:
                registro.data_hora = novo_registro.data_hora
                registro.data_hora_saida = novo_registro.data_hora_saida
                registro.saida_pendente = novo_registro.saida_pendente
                registro.status_alteracao = 'EDITADO'
                registro.save()
            
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
            registro = get_object_or_404(RegistroAcesso, id=registro_id)
            justificativa = request.POST.get('justificativa')
            
            if not justificativa:
                return JsonResponse({
                    'status': 'error',
                    'message': 'É necessário informar uma justificativa para excluir o registro.'
                }, status=400)
            
            # Cria uma cópia do registro com status EXCLUIDO para o histórico
            registro_excluido = RegistroAcesso.objects.create(
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
            
            # Remove apenas do dashboard (plantão atual)
            if registro.data_hora >= calcular_plantao_atual()['inicio'] and registro.data_hora <= calcular_plantao_atual()['fim']:
                registro.delete()
            else:
                # Se não estiver no plantão atual, apenas marca como excluído
                registro.status_alteracao = 'EXCLUIDO'
                registro.data_hora_alteracao = timezone.now()
                registro.justificativa = justificativa
                registro.save()
            
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
                'Veículo': registro.veiculo or '-',
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
                'Veículo': registro.veiculo or '-',
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
def historico(request):
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    plantao = request.GET.get('plantao')
    servidor = request.GET.get('servidor')
    
    registros = RegistroAcesso.objects.all().select_related('servidor', 'operador', 'operador_saida')
    
    if data_inicio:
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        registros = registros.filter(data_hora__date__gte=data_inicio)
    
    if data_fim:
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
        registros = registros.filter(data_hora__date__lte=data_fim)
    
    if plantao:
        registros = registros.filter(
            Q(servidor__nome__icontains=servidor) |
            Q(servidor__numero_documento__icontains=servidor)
        )
    
    # Ordena por data_hora_alteracao (se existir) ou data_hora, mais recentes primeiro
    registros = registros.order_by(
        Case(
            When(data_hora_alteracao__isnull=False, then='data_hora_alteracao'),
            default='data_hora'
        ),
        '-data_hora'
    )
    
    if request.GET.get('format') == 'excel':
        # Cria um DataFrame com os registros
        data = []
        for registro in registros:
            # Calcula o plantão com base na data/hora do registro
            plantao_registro = calcular_plantao_atual(registro.data_hora)
            data.append({
                'Plantão': plantao_registro['nome'],
                'Data': registro.data_hora.strftime('%d/%m/%Y'),
                'Operador': registro.operador.get_full_name() or registro.operador.username,
                'Servidor': registro.servidor.nome,
                'Documento': registro.servidor.numero_documento,
                'Setor': registro.servidor.setor or '-',
                'Veículo': registro.veiculo or '-',
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': registro.data_hora.strftime('%H:%M') if registro.tipo_acesso == 'ENTRADA' else '-',
                'OBS Entrada': registro.observacao or '-',
                'Saída': registro.data_hora_saida.strftime('%H:%M') if registro.data_hora_saida else '-',
                'OBS Saída': registro.observacao_saida or '-',
                'Alteração': registro.status_alteracao or 'Original',
                'Data/Hora': registro.data_hora_alteracao.strftime('%d/%m/%Y %H:%M') if registro.data_hora_alteracao else '-',
                'Justificativa': registro.justificativa or '-'
            })
        
        df = pd.DataFrame(data)
        
        # Cria o arquivo Excel
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=historico_acessos_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Histórico')
            
            # Ajusta a largura das colunas
            worksheet = writer.sheets['Histórico']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                )
                worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
        
        return response
    
    # Prepara os registros para exibição na tabela
    registros_formatados = []
    for registro in registros:
        # Calcula o plantão com base na data/hora do registro
        plantao_registro = calcular_plantao_atual(registro.data_hora)
        registros_formatados.append({
            'plantao': plantao_registro['nome'],
            'data_hora': registro.data_hora,
            'operador': registro.operador,
            'servidor': registro.servidor,
            'tipo_acesso': registro.tipo_acesso,
            'observacao': registro.observacao,
            'observacao_saida': registro.observacao_saida,
            'isv': registro.isv,
            'veiculo': registro.veiculo,
            'data_hora_saida': registro.data_hora_saida,
            'status_alteracao': registro.status_alteracao,
            'data_hora_alteracao': registro.data_hora_alteracao,
            'justificativa': registro.justificativa
        })
    
    context = {
        'registros': registros_formatados,
        'data_inicio': data_inicio.strftime('%Y-%m-%d') if data_inicio else '',
        'data_fim': data_fim.strftime('%Y-%m-%d') if data_fim else '',
        'plantao': plantao or '',
        'servidor': servidor or ''
    }
    return render(request, 'core/historico.html', context)

@login_required
def saida_definitiva(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Cria ou obtém o servidor
            servidor, created = Servidor.objects.get_or_create(
                nome=data['nome'],
                numero_documento=data['numero_documento'],
                defaults={'ativo': True}
            )
            
            # Cria o registro de saída
            registro = RegistroAcesso.objects.create(
                servidor=servidor,
                operador=request.user,
                tipo_acesso='SAIDA',
                setor=data['justificativa'],  # Usa o campo setor para a justificativa
                data_hora=timezone.now(),
                status_alteracao='ORIGINAL'  # Marca como registro original
            )
            
            # Registra no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='CRIACAO',
                modelo='RegistroAcesso',
                objeto_id=registro.id,
                detalhes=f"Saída definitiva registrada para {servidor.nome}"
            )
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Método não permitido'}, status=405)

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
def limpar_plantao(request):
    if request.method == 'POST':
        try:
            senha = request.POST.get('senha')
            
            # Verifica se a senha está correta
            if not request.user.check_password(senha):
                messages.error(request, 'Senha incorreta!')
                return redirect('home')
            
            plantao_atual = calcular_plantao_atual()
            
            # Registra a ação no log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                tipo_acao='EXCLUSAO',
                modelo='RegistroAcesso',
                objeto_id=None,
                detalhes=f'Limpeza dos registros do plantão {plantao_atual["nome"]}'
            )
            
            # Exclui todos os registros do plantão atual
            RegistroAcesso.objects.filter(
                data_hora__gte=plantao_atual['inicio'],
                data_hora__lte=plantao_atual['fim']
            ).delete()
            
            messages.success(request, 'Registros do plantão limpos com sucesso!')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Erro ao limpar registros do plantão: {str(e)}')
            return redirect('home')
    
    return redirect('home')

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
