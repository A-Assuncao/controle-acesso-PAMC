from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
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
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy

def is_staff(user):
    return user.is_staff

@login_required
def home(request):
    plantao_atual = calcular_plantao_atual()
    
    # Filtra registros do plantão atual
    registros = RegistroAcesso.objects.filter(
        data_hora__gte=plantao_atual['inicio'],
        data_hora__lte=plantao_atual['fim']
    ).select_related('servidor', 'operador').order_by('-data_hora')
    
    # Calcula totais para os cards
    total_entradas = registros.filter(tipo_acesso='ENTRADA').count()
    total_saidas = registros.filter(tipo_acesso='SAIDA').count()
    total_pendentes = registros.filter(tipo_acesso='ENTRADA', saida_pendente=True).count()
    
    # Lista de servidores para os modais
    servidores = Servidor.objects.filter(ativo=True).order_by('nome')
    
    context = {
        'plantao_atual': plantao_atual,
        'registros': registros,
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
        ).values('id', 'nome', 'numero_documento')
        return JsonResponse(list(servidores), safe=False)
    return JsonResponse([], safe=False)

@login_required
def registro_acesso_create(request):
    if request.method == 'POST':
        servidor_id = request.POST.get('servidor')
        tipo_acesso = request.POST.get('tipo_acesso')
        observacao = request.POST.get('observacao', '')
        isv = request.POST.get('isv') == 'on'
        
        servidor = get_object_or_404(Servidor, id=servidor_id)
        
        # Cria o registro
        registro = RegistroAcesso.objects.create(
            servidor=servidor,
            operador=request.user,
            tipo_acesso=tipo_acesso,
            observacao=observacao,
            isv=isv
        )
        
        # Atualiza saída pendente
        if tipo_acesso == 'ENTRADA':
            registro.saida_pendente = True
            registro.save()
        elif tipo_acesso == 'SAIDA':
            # Marca a última entrada como não pendente
            ultima_entrada = RegistroAcesso.objects.filter(
                servidor=servidor,
                tipo_acesso='ENTRADA',
                saida_pendente=True
            ).first()
            if ultima_entrada:
                ultima_entrada.saida_pendente = False
                ultima_entrada.save()
        
        messages.success(request, f'{tipo_acesso.title()} registrada com sucesso!')
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
        data_hora__lte=plantao_atual['fim']
    ).select_related('servidor', 'operador').order_by('-data_hora')
    
    data = []
    for registro in registros:
        data.append({
            'id': registro.id,
            'plantao': plantao_atual['nome'],
            'data': registro.data_hora.strftime('%d/%m/%Y'),
            'hora': registro.data_hora.strftime('%H:%M'),
            'operador': registro.operador.get_full_name() or registro.operador.username,
            'servidor_nome': registro.servidor.nome,
            'servidor_documento': registro.servidor.numero_documento,
            'setor': registro.servidor.setor or '-',
            'veiculo': registro.veiculo or '-',
            'tipo_acesso': registro.tipo_acesso,
            'isv': registro.isv
        })
    
    return JsonResponse(data, safe=False)

@login_required
def registro_acesso_update(request, registro_id):
    registro = get_object_or_404(RegistroAcesso, id=registro_id)
    
    if request.method == 'POST':
        tipo_acesso = request.POST.get('tipo_acesso')
        observacao = request.POST.get('observacao', '')
        justificativa = request.POST.get('justificativa')
        isv = request.POST.get('isv') == 'on'
        data_hora = request.POST.get('data_hora')
        
        if not justificativa:
            messages.error(request, 'É necessário informar uma justificativa para editar o registro.')
            return redirect('home')
        
        # Registra a edição no log de auditoria
        LogAuditoria.objects.create(
            usuario=request.user,
            tipo_acao='EDICAO',
            modelo='RegistroAcesso',
            objeto_id=registro.id,
            detalhes=f"Edição de registro de {registro.servidor.nome}. Justificativa: {justificativa}"
        )
        
        # Atualiza o registro
        registro.tipo_acesso = tipo_acesso
        registro.observacao = observacao
        registro.isv = isv
        registro.data_hora = data_hora
        registro.save()
        
        messages.success(request, 'Registro atualizado com sucesso!')
        return redirect('home')
    
    return render(request, 'core/registro_form.html', {'registro': registro})

@login_required
def excluir_registro(request, registro_id):
    if request.method == 'POST':
        registro = get_object_or_404(RegistroAcesso, id=registro_id)
        justificativa = request.POST.get('justificativa')
        
        if not justificativa:
            return JsonResponse({
                'status': 'error',
                'message': 'É necessário informar uma justificativa para excluir o registro.'
            }, status=400)
        
        # Registra a exclusão no log de auditoria
        LogAuditoria.objects.create(
            usuario=request.user,
            tipo_acao='EXCLUSAO',
            modelo='RegistroAcesso',
            objeto_id=registro.id,
            detalhes=f"Exclusão de {registro.get_tipo_acesso_display()} de {registro.servidor.nome}. Justificativa: {justificativa}"
        )
        
        registro.delete()
        return JsonResponse({'status': 'success'})
    
    return JsonResponse({'status': 'error'}, status=405)

@login_required
def encerrar_plantao(request):
    plantao_atual = calcular_plantao_atual()
    inicio_plantao = plantao_atual['inicio']
    fim_plantao = plantao_atual['fim']
    
    registros = RegistroAcesso.objects.filter(
        data_hora__gte=inicio_plantao,
        data_hora__lte=fim_plantao
    ).select_related('servidor', 'operador').order_by('data_hora')
    
    # Cria um DataFrame com os registros
    data = []
    for registro in registros:
        data.append({
            'Data/Hora': registro.data_hora.strftime('%d/%m/%Y %H:%M'),
            'Servidor': registro.servidor.nome,
            'Tipo': registro.get_tipo_acesso_display(),
            'Função': registro.servidor.get_tipo_funcionario_display(),
            'Plantão': registro.servidor.get_plantao_display() or '-',
            'ISV': 'Sim' if registro.isv else 'Não',
            'Operador': registro.operador.get_full_name() or registro.operador.username,
            'Observação': registro.observacao or '-'
        })
    
    df = pd.DataFrame(data)
    
    # Cria o arquivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=plantao_{plantao_atual["nome"].lower()}_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Registros')
    
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
@user_passes_test(is_staff)
def historico(request):
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    plantao = request.GET.get('plantao')
    servidor = request.GET.get('servidor')
    format = request.GET.get('format')
    
    registros = RegistroAcesso.objects.all().select_related('servidor', 'operador')
    
    if data_inicio:
        registros = registros.filter(data_hora__date__gte=data_inicio)
    if data_fim:
        registros = registros.filter(data_hora__date__lte=data_fim)
    if plantao:
        registros = registros.filter(servidor__plantao=plantao)
    if servidor:
        registros = registros.filter(
            Q(servidor__nome__icontains=servidor) |
            Q(servidor__numero_documento__icontains=servidor)
        )
    
    registros = registros.order_by('-data_hora')
    
    if format == 'excel':
        # Cria um DataFrame com os registros
        data = []
        for registro in registros:
            data.append({
                'ORD': len(data) + 1,
                'Plantão': registro.servidor.get_plantao_display() or '-',
                'Data': registro.data_hora.strftime('%d/%m/%Y'),
                'Operador': registro.operador.get_full_name() or registro.operador.username,
                'Servidor': registro.servidor.nome,
                'Documento': registro.servidor.numero_documento,
                'Setor': registro.servidor.setor or '-',
                'Veículo': registro.veiculo or '-',
                'ISV': 'Sim' if registro.isv else 'Não',
                'Entrada': registro.data_hora.strftime('%H:%M') if registro.tipo_acesso == 'ENTRADA' else '-',
                'Saída': registro.data_hora.strftime('%H:%M') if registro.tipo_acesso == 'SAIDA' else '-',
                'Alterado': registro.data_hora_manual.strftime('%d/%m/%Y %H:%M') if registro.data_hora_manual else '-',
                'Justificativa': registro.justificativa or '-'
            })
        
        df = pd.DataFrame(data)
        
        # Cria o arquivo Excel
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename=historico_acessos_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Histórico')
        
        return response
    
    context = {
        'registros': registros,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'plantao': plantao,
            'servidor': servidor
        }
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
                data_hora=timezone.now()
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

class CustomLoginView(LoginView):
    template_name = 'core/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('home')
