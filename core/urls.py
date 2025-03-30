from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('servidores/', views.servidor_list, name='servidor_list'),
    path('servidores/novo/', views.servidor_create, name='servidor_create'),
    path('servidores/<int:pk>/editar/', views.servidor_update, name='servidor_update'),
    path('servidores/<int:pk>/excluir/', views.servidor_delete, name='servidor_delete'),
    path('servidores/importar/', views.importar_servidores, name='importar_servidores'),
    path('servidores/limpar-banco/', views.limpar_banco_servidores, name='limpar_banco_servidores'),
    path('buscar-servidor/', views.buscar_servidor, name='buscar_servidor'),
    path('registro/criar/', views.registro_acesso_create, name='registro_acesso_create'),
    path('registro/manual/', views.registro_manual_create, name='registro_manual_create'),
    path('registro/saida-definitiva/', views.saida_definitiva, name='saida_definitiva'),
    path('registros-plantao/', views.registros_plantao, name='registros_plantao'),
    path('registro/<int:registro_id>/editar/', views.registro_acesso_update, name='registro_acesso_update'),
    path('registro/<int:registro_id>/excluir/', views.excluir_registro, name='excluir_registro'),
    path('encerrar-plantao/', views.encerrar_plantao, name='encerrar_plantao'),
    path('limpar-plantao/', views.limpar_plantao, name='limpar_plantao'),
    path('usuarios/', views.user_list, name='user_list'),
    path('usuarios/novo/', views.user_create, name='user_create'),
    path('usuarios/<int:pk>/editar/', views.user_update, name='user_update'),
    path('usuarios/<int:pk>/excluir/', views.user_delete, name='user_delete'),
    path('historico/', views.historico, name='historico'),
    path('download-modelo-importacao/', views.download_modelo_importacao, name='download_modelo_importacao'),
] 