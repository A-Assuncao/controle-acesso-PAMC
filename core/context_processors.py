from .models import PerfilUsuario

def user_permissions(request):
    """
    Context processor para adicionar permissões do usuário a todos os templates
    """
    if request.user.is_authenticated:
        try:
            perfil = request.user.perfil
            return {
                'user_pode_gerenciar_servidores': perfil.pode_gerenciar_servidores(),
                'user_pode_registrar_acesso': perfil.pode_registrar_acesso(),
                'user_pode_excluir_registros': perfil.pode_excluir_registros(),
                'user_pode_limpar_dashboard': perfil.pode_limpar_dashboard(),
                'user_pode_saida_definitiva': perfil.pode_saida_definitiva(),
                'user_tipo_usuario': perfil.get_tipo_usuario_display(),
            }
        except PerfilUsuario.DoesNotExist:
            # Se não tem perfil, assume operador completo
            return {
                'user_pode_gerenciar_servidores': True,
                'user_pode_registrar_acesso': True,
                'user_pode_excluir_registros': True,
                'user_pode_limpar_dashboard': True,
                'user_pode_saida_definitiva': True,
                'user_tipo_usuario': 'Operador',
            }
    
    return {
        'user_pode_gerenciar_servidores': False,
        'user_pode_registrar_acesso': False,
        'user_pode_excluir_registros': False,
        'user_pode_limpar_dashboard': False,
        'user_pode_saida_definitiva': False,
        'user_tipo_usuario': 'Anônimo',
    } 