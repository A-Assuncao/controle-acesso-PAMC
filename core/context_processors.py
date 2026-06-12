from urllib.parse import quote

from .models import PerfilUsuario
from .utils import get_unidade_prisional

WHATSAPP_DESENVOLVEDOR = '5595991252718'


def montar_mensagem_whatsapp_suporte(nome: str, tipo_usuario: str, unidade: str) -> str:
    """Monta a mensagem pré-preenchida para reporte de bugs/sugestões."""
    return (
        f"🛡️ Controle de Acesso — {unidade}\n"
        f"👤 {nome} • {tipo_usuario}\n\n"
        f"🔧 Bug ou 💡 Sugestão:\n"
    )


def montar_url_whatsapp_suporte(nome: str, tipo_usuario: str, unidade: str) -> str:
    """Gera link api.whatsapp.com com texto URL-encoded para Web/Desktop."""
    mensagem = montar_mensagem_whatsapp_suporte(nome, tipo_usuario, unidade)
    texto = quote(mensagem, safe='')
    return f"https://api.whatsapp.com/send?phone={WHATSAPP_DESENVOLVEDOR}&text={texto}"


def user_permissions(request):
    """
    Context processor para adicionar permissões do usuário a todos os templates
    """
    if request.user.is_authenticated:
        nome_usuario = request.user.get_full_name() or request.user.username
        unidade = get_unidade_prisional()
        try:
            perfil = request.user.perfil
            tipo_usuario = perfil.get_tipo_usuario_display()
            return {
                'user_pode_gerenciar_servidores': perfil.pode_gerenciar_servidores(),
                'user_pode_registrar_acesso': perfil.pode_registrar_acesso(),
                'user_pode_excluir_registros': perfil.pode_excluir_registros(),
                'user_pode_limpar_dashboard': perfil.pode_limpar_dashboard(),
                'user_pode_saida_definitiva': perfil.pode_saida_definitiva(),
                'user_tipo_usuario': tipo_usuario,
                'whatsapp_suporte_url': montar_url_whatsapp_suporte(
                    nome_usuario, tipo_usuario, unidade
                ),
            }
        except PerfilUsuario.DoesNotExist:
            # Se não tem perfil, assume operador completo
            tipo_usuario = 'Operador'
            return {
                'user_pode_gerenciar_servidores': True,
                'user_pode_registrar_acesso': True,
                'user_pode_excluir_registros': True,
                'user_pode_limpar_dashboard': True,
                'user_pode_saida_definitiva': True,
                'user_tipo_usuario': tipo_usuario,
                'whatsapp_suporte_url': montar_url_whatsapp_suporte(
                    nome_usuario, tipo_usuario, unidade
                ),
            }
    
    return {
        'user_pode_gerenciar_servidores': False,
        'user_pode_registrar_acesso': False,
        'user_pode_excluir_registros': False,
        'user_pode_limpar_dashboard': False,
        'user_pode_saida_definitiva': False,
        'user_tipo_usuario': 'Anônimo',
    }

def unidade_prisional(request):
    """
    Context processor para adicionar a UNIDADE_PRISIONAL a todos os templates
    """
    return {
        'UNIDADE_PRISIONAL': get_unidade_prisional()
    }