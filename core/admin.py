from django.contrib import admin
from .models import Servidor, RegistroAcesso, LogAuditoria

@admin.register(Servidor)
class ServidorAdmin(admin.ModelAdmin):
    list_display = ['nome', 'numero_documento', 'setor', 'veiculo', 'ativo']
    list_filter = ['ativo']
    search_fields = ['nome', 'numero_documento']

@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ['servidor', 'data_hora', 'tipo_acesso', 'operador', 'isv']
    list_filter = ['tipo_acesso', 'isv', 'data_hora']
    search_fields = ['servidor__nome', 'operador__username']
    readonly_fields = ('data_hora', 'operador')

@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ['data_hora', 'usuario', 'tipo_acao', 'modelo', 'objeto_id']
    list_filter = ['tipo_acao', 'modelo', 'data_hora']
    search_fields = ['usuario__username', 'detalhes']
    readonly_fields = ('data_hora', 'usuario', 'tipo_acao', 'modelo', 'objeto_id', 'detalhes')
