from django.contrib import admin
from .models import Servidor, RegistroAcesso, RegistroDashboard, LogAuditoria

@admin.register(Servidor)
class ServidorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'numero_documento', 'tipo_funcionario', 'plantao', 'setor', 'veiculo', 'ativo')
    list_filter = ('tipo_funcionario', 'plantao', 'ativo')
    search_fields = ('nome', 'numero_documento')

@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ('servidor', 'data_hora', 'tipo_acesso', 'operador', 'isv', 'status_alteracao')
    list_filter = ('tipo_acesso', 'isv', 'status_alteracao', 'saida_pendente')
    search_fields = ('servidor__nome', 'servidor__numero_documento', 'operador__username')
    date_hierarchy = 'data_hora'

@admin.register(RegistroDashboard)
class RegistroDashboardAdmin(admin.ModelAdmin):
    list_display = ('servidor', 'data_hora', 'tipo_acesso', 'operador', 'isv', 'saida_pendente')
    list_filter = ('tipo_acesso', 'isv', 'saida_pendente')
    search_fields = ('servidor__nome', 'servidor__numero_documento', 'operador__username')
    date_hierarchy = 'data_hora'

@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'data_hora', 'tipo_acao', 'modelo', 'objeto_id')
    list_filter = ('tipo_acao', 'modelo')
    search_fields = ('usuario__username', 'detalhes')
    date_hierarchy = 'data_hora'
    readonly_fields = ('usuario', 'data_hora', 'tipo_acao', 'modelo', 'objeto_id', 'detalhes')
