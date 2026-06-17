"""
Views de gerenciamento de usuários.

Responsável por:
- CRUD completo de usuários
- Sistema de permissões e tipos de usuário
- Gerenciamento de senhas temporárias
- Reset de senhas por administradores
- Troca de senha pelos próprios usuários
- Perfis de usuário
"""

import random
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Case, When, IntegerField

from ..models import LogAuditoria, PerfilUsuario
from ..decorators import log_errors


def is_staff(user):
    """Verifica se o usuário é staff."""
    return user.is_staff


@login_required
@user_passes_test(is_staff)
def user_list(request):
    """Lista todos os usuários do sistema."""
    # Verifica se o usuário tem permissão de staff
    if not request.user.is_staff:
        messages.error(request, 'Você não tem permissão para acessar a lista de usuários.')
        return redirect('home')

    # Obtém todos os usuários ordenados por tipo (superuser, staff, operador) e depois por nome
    users = User.objects.annotate(
        ordem_tipo=Case(
            When(is_superuser=True, then=1),
            When(is_staff=True, then=2),
            default=3,
            output_field=IntegerField()
        )
    ).order_by('ordem_tipo', 'username')

    # Prepara os dados para o template, incluindo informações do perfil.
    # A senha temporária NÃO é mais persistida: ela é mostrada uma única vez
    # na flash message após user_create/user_reset_password/user_update.
    # Listar usuários não regenera nem exibe a senha.
    users_data = []
    for user in users:
        # Obtém ou cria o perfil do usuário
        try:
            perfil = user.perfil
        except:
            perfil = PerfilUsuario.objects.create(
                usuario=user,
                precisa_trocar_senha=False,
                tipo_usuario='OPERADOR'
            )

        users_data.append({
            'user': user,
            'perfil': perfil,
        })

    return render(request, 'core/user_list.html', {
        'users_data': users_data,
        'is_superuser': request.user.is_superuser
    })


@login_required
@user_passes_test(is_staff)
@log_errors
def user_create(request):
    """Cria um novo usuário."""
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        tipo_usuario = request.POST.get('tipo_usuario', 'OPERADOR')

        # Define is_staff baseado no tipo de usuário
        is_staff = tipo_usuario == 'STAFF'

        # Validações
        if not username:
            messages.error(request, 'Nome de usuário é obrigatório.')
            return redirect('user_create')

        if not first_name:
            messages.error(request, 'Nome é obrigatório.')
            return redirect('user_create')

        if not last_name:
            messages.error(request, 'Sobrenome é obrigatório.')
            return redirect('user_create')

        # Verifica se o usuário já existe
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Este nome de usuário já está em uso.')
            return redirect('user_create')

        # Gera senha temporária no formato usuario@1234 (números aleatórios)
        numeros_aleatorios = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        password = f"{username}@{numeros_aleatorios}"

        # Cria o usuário
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff
        )

        # Cria o perfil do usuário
        PerfilUsuario.objects.create(
            usuario=user,
            precisa_trocar_senha=True,  # Força a troca de senha no primeiro login
            tipo_usuario=tipo_usuario  # Usa o tipo selecionado
        )

        # Registra a criação no log de auditoria
        LogAuditoria.objects.create(
            usuario=request.user,
            tipo_acao='CRIACAO',
            modelo='User',
            objeto_id=user.id,
            detalhes=f'Criação do usuário {username} ({first_name} {last_name})'
        )

        # Obtém o nome amigável do tipo de usuário
        tipo_nome = dict(PerfilUsuario.TIPO_USUARIO_CHOICES)[tipo_usuario]
        messages.success(request, 
            f'Usuário {username} ({first_name} {last_name}) criado como "{tipo_nome}" com sucesso! '
            f'A senha temporária é: {password}'
        )
        return redirect('user_list')

    return render(request, 'core/user_form.html')


@login_required
def user_update(request, pk):
    """Atualiza um usuário existente."""
    # Verifica se o usuário tem permissão de staff
    if not request.user.is_staff:
        messages.error(request, 'Você não tem permissão para editar usuários.')
        return redirect('home')

    usuario = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        usuario.email = request.POST.get('email')
        usuario.first_name = request.POST.get('first_name')
        usuario.last_name = request.POST.get('last_name')
        tipo_usuario = request.POST.get('tipo_usuario', 'OPERADOR')

        # Define is_staff baseado no tipo de usuário
        usuario.is_staff = tipo_usuario == 'STAFF'

        # Atualiza o perfil do usuário
        try:
            perfil = usuario.perfil
        except:
            perfil = PerfilUsuario.objects.create(
                usuario=usuario,
                tipo_usuario=tipo_usuario,
                precisa_trocar_senha=False
            )

        perfil.tipo_usuario = tipo_usuario
        perfil.save()

        # Processa redefinição de senha se solicitada
        redefinir_senha = request.POST.get('redefinir_senha') == 'on'
        forcar_troca = request.POST.get('forcar_troca') == 'on'

        if redefinir_senha:
            numeros_aleatorios = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            nova_senha = f"{usuario.username}@{numeros_aleatorios}"
            usuario.set_password(nova_senha)
            perfil.precisa_trocar_senha = True
            perfil.save()
            messages.success(request, f'Usuário atualizado! Nova senha temporária: {nova_senha}')
        elif forcar_troca:
            perfil.precisa_trocar_senha = True
            perfil.save()
            messages.success(request, 'Usuário atualizado! Será obrigado a trocar a senha no próximo login.')
        else:
            messages.success(request, 'Usuário atualizado com sucesso!')

        usuario.save()
        return redirect('user_list')

    return render(request, 'core/user_form.html', {'usuario': usuario})


@login_required
def user_delete(request, pk):
    """Exclui um usuário."""
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
@user_passes_test(is_staff)
def user_reset_password(request, pk):
    """Reseta a senha de um usuário (apenas para staff)."""
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
        perfil = PerfilUsuario.objects.create(usuario=user, tipo_usuario='OPERADOR')

    # Para usuários de visualização, não força a troca de senha
    # A senha é exibida uma única vez na flash message abaixo.
    if perfil.tipo_usuario == 'VISUALIZACAO':
        perfil.precisa_trocar_senha = False
    else:
        perfil.precisa_trocar_senha = True

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
    """Permite que o usuário troque sua própria senha."""
    # Obtém ou cria o perfil do usuário
    try:
        perfil = request.user.perfil
    except:
        perfil = PerfilUsuario.objects.create(
            usuario=request.user,
            precisa_trocar_senha=False,
            tipo_usuario='OPERADOR'
        )

    if request.method == 'POST':
        senha_atual = request.POST.get('senha_atual')
        nova_senha = request.POST.get('nova_senha')
        confirmar_senha = request.POST.get('confirmar_senha')

        # Validações básicas
        if not senha_atual or not nova_senha or not confirmar_senha:
            messages.error(request, 'Todos os campos são obrigatórios.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})

        if nova_senha != confirmar_senha:
            messages.error(request, 'A nova senha e a confirmação não coincidem.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})

        if len(nova_senha) < 8:
            messages.error(request, 'A nova senha deve ter pelo menos 8 caracteres.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})

        # Verifica se a senha atual está correta
        if not request.user.check_password(senha_atual):
            messages.error(request, 'Senha atual incorreta.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})

        # Validações adicionais de segurança
        if nova_senha.lower() in [request.user.username.lower(), request.user.first_name.lower(), request.user.last_name.lower()]:
            messages.error(request, 'A nova senha não pode conter seu nome de usuário ou nome pessoal.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})

        # Verifica se a senha não é muito simples
        senhas_comuns = ['12345678', '87654321', 'abcdefgh', 'password', 'senha123', '11111111', '00000000']
        if nova_senha.lower() in senhas_comuns:
            messages.error(request, 'Por favor, escolha uma senha mais segura.')
            return render(request, 'core/trocar_senha.html', {'perfil': perfil})

        # Altera a senha
        request.user.set_password(nova_senha)
        request.user.save()

        # Atualiza o perfil do usuário
        try:
            perfil.precisa_trocar_senha = False
            perfil.save()
        except Exception as e:
            # Se houver erro ao atualizar o perfil, registra o erro mas permite continuar
            logging.getLogger('django').error(f"Erro ao atualizar perfil após troca de senha: {str(e)}")

        messages.success(request, 'Senha alterada com sucesso! Por favor, faça login novamente.')
        return redirect('login')

    return render(request, 'core/trocar_senha.html', {'perfil': perfil}) 