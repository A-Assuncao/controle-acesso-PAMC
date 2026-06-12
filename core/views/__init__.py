"""
Views modulares do sistema de controle de acesso.

Organizadas por responsabilidade em submodulos de core/views/.
"""
from .base_views import welcome, home
from .servidor_views import (
    servidor_list, servidor_create, servidor_update, servidor_delete,
    buscar_servidor, verificar_entrada, importar_servidores,
    download_modelo_importacao, limpar_banco_servidores
)

# Views de registros refatoradas
from .registro_views import (
    registro_acesso_create, registro_manual_create, registros_plantao,
    registro_detalhe, registro_acesso_update, excluir_registro,
    registrar_saida, saida_definitiva, limpar_dashboard, exportar_excel,
    retirar_faltas
)

# Views de usuários refatoradas
from .user_views import (
    user_list, user_create, user_update, user_delete,
    user_reset_password, trocar_senha, is_staff
)

# Views de relatórios refatoradas
from .relatorio_views import historico

# Views de treinamento e funções auxiliares refatoradas
from .treinamento_views import (
    ambiente_treinamento, registros_plantao_treinamento,
    registro_detalhe_treinamento, buscar_servidor_treinamento,
    registro_acesso_treinamento_create, registro_manual_treinamento_create,
    saida_definitiva_treinamento, limpar_dashboard_treinamento,
    exportar_excel_treinamento, registro_acesso_treinamento_update,
    excluir_registro_treinamento, registrar_saida_treinamento,
    tutoriais_treinamento, retirar_faltas_treinamento,
    is_superuser, handler500
)

# Views de autenticação Canaimé (experimental)
from .canaime_views import (
    canaime_login, test_canaime_connection, canaime_user_info, logout_canaime
) 