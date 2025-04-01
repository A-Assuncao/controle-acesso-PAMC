from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.home, name='home'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('servidor/', views.servidor_list, name='servidor_list'),
    path('servidor/novo/', views.servidor_create, name='servidor_create'),
    path('servidor/<int:pk>/editar/', views.servidor_update, name='servidor_update'),
    path('servidor/<int:pk>/excluir/', views.servidor_delete, name='servidor_delete'),
    path('buscar-servidor/', views.buscar_servidor, name='buscar_servidor'),
    path('registro-acesso/criar/', views.registro_acesso_create, name='registro_acesso_create'),
    path('registro-manual/criar/', views.registro_manual_create, name='registro_manual_create'),
    path('registros-plantao/', views.registros_plantao, name='registros_plantao'),
    path('registro/<int:registro_id>/', views.registro_detalhe, name='registro_detalhe'),
    path('registro/<int:registro_id>/editar/', views.registro_acesso_update, name='registro_acesso_update'),
    path('registro/<int:registro_id>/excluir/', views.excluir_registro, name='excluir_registro'),
    path('exportar-excel/', views.exportar_excel, name='exportar_excel'),
    path('usuarios/', views.user_list, name='user_list'),
    path('usuarios/novo/', views.user_create, name='user_create'),
    path('usuarios/<int:pk>/editar/', views.user_update, name='user_update'),
    path('usuarios/<int:pk>/excluir/', views.user_delete, name='user_delete'),
    path('historico/', views.historico, name='historico'),
    path('registro/saida-definitiva/', views.saida_definitiva, name='saida_definitiva'),
    path('importar-servidores/', views.importar_servidores, name='importar_servidores'),
    path('download-modelo-importacao/', views.download_modelo_importacao, name='download_modelo_importacao'),
    path('limpar-banco-servidores/', views.limpar_banco_servidores, name='limpar_banco_servidores'),
    path('verificar-entrada/<int:servidor_id>/', views.verificar_entrada, name='verificar_entrada'),
    path('limpar-dashboard/', views.limpar_dashboard, name='limpar_dashboard'),
] 