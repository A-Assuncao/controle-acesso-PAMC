from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.utils import timezone
from .models import Servidor, RegistroAcesso, RegistroDashboard, LogAuditoria, VideoTutorial

@admin.register(Servidor)
class ServidorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'numero_documento', 'setor', 'veiculo', 'status_ativo', 'total_registros')
    list_filter = ('ativo', 'setor')
    search_fields = ('nome', 'numero_documento')
    ordering = ('nome',)
    list_per_page = 20
    
    def status_ativo(self, obj):
        if obj.ativo:
            return format_html(
                '<span style="color: green; font-weight: bold;">●</span> Ativo'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">●</span> Inativo'
        )
    status_ativo.short_description = 'Status'
    
    def total_registros(self, obj):
        count = RegistroAcesso.objects.filter(servidor=obj).count()
        url = reverse('admin:core_registroacesso_changelist') + f'?servidor__id={obj.id}'
        return format_html('<a href="{}">{} registros</a>', url, count)
    total_registros.short_description = 'Total de Registros'
    
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('nome', 'numero_documento')
        }),
        ('Informações Complementares', {
            'fields': ('setor', 'veiculo', 'ativo')
        }),
    )

@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(admin.ModelAdmin):
    list_display = ('data_formatada', 'servidor_link', 'tipo_acesso', 'operador', 'status_saida', 'detalhes_alteracao')
    list_filter = ('tipo_acesso', 'saida_pendente', 'status_alteracao', 'isv')
    search_fields = ('servidor__nome', 'servidor__numero_documento', 'observacao')
    date_hierarchy = 'data_hora'
    list_per_page = 20
    
    def data_formatada(self, obj):
        return obj.data_hora.strftime("%d/%m/%Y %H:%M")
    data_formatada.short_description = 'Data/Hora'
    
    def servidor_link(self, obj):
        url = reverse('admin:core_servidor_change', args=[obj.servidor.id])
        return format_html('<a href="{}">{}</a>', url, obj.servidor.nome)
    servidor_link.short_description = 'Servidor'
    
    def status_saida(self, obj):
        if obj.tipo_acesso == 'SAIDA':
            return format_html(
                '<span style="color: purple; font-weight: bold;">Saída Definitiva</span>'
            )
        elif obj.saida_pendente:
            return format_html(
                '<span style="color: red; font-weight: bold;">Pendente</span>'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">Concluído</span>'
        )
    status_saida.short_description = 'Status'
    
    def detalhes_alteracao(self, obj):
        if obj.status_alteracao == 'ORIGINAL':
            return '-'
        elif obj.status_alteracao == 'EDITADO':
            return format_html(
                '<span style="color: orange;">Editado em {}</span>',
                obj.data_hora_alteracao.strftime("%d/%m/%Y %H:%M")
            )
        return format_html(
            '<span style="color: red;">Excluído em {}</span>',
            obj.data_hora_alteracao.strftime("%d/%m/%Y %H:%M")
        )
    detalhes_alteracao.short_description = 'Alterações'
    
    fieldsets = (
        ('Informações Principais', {
            'fields': ('servidor', 'tipo_acesso', 'operador')
        }),
        ('Detalhes do Registro', {
            'fields': ('data_hora', 'data_hora_saida', 'isv', 'veiculo', 'setor')
        }),
        ('Observações', {
            'fields': ('observacao', 'observacao_saida')
        }),
        ('Status e Alterações', {
            'fields': ('saida_pendente', 'status_alteracao', 'justificativa')
        }),
    )
    
    readonly_fields = ('status_alteracao', 'data_hora_alteracao')

@admin.register(RegistroDashboard)
class RegistroDashboardAdmin(admin.ModelAdmin):
    list_display = ('data_formatada', 'servidor_link', 'tipo_acesso', 'operador', 'status_registro')
    list_filter = ('tipo_acesso', 'saida_pendente', 'isv')
    search_fields = ('servidor__nome', 'servidor__numero_documento')
    date_hierarchy = 'data_hora'
    list_per_page = 20
    
    def data_formatada(self, obj):
        return obj.data_hora.strftime("%d/%m/%Y %H:%M")
    data_formatada.short_description = 'Data/Hora'
    
    def servidor_link(self, obj):
        url = reverse('admin:core_servidor_change', args=[obj.servidor.id])
        return format_html('<a href="{}">{}</a>', url, obj.servidor.nome)
    servidor_link.short_description = 'Servidor'
    
    def status_registro(self, obj):
        if obj.tipo_acesso == 'SAIDA':
            return format_html(
                '<span style="color: purple; font-weight: bold;">●</span> Saída Definitiva'
            )
        elif obj.saida_pendente:
            return format_html(
                '<span style="color: red; font-weight: bold;">●</span> Aguardando Saída'
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">●</span> Concluído'
        )
    status_registro.short_description = 'Status'

@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('data_formatada', 'usuario', 'tipo_acao', 'modelo', 'detalhes')
    list_filter = ('tipo_acao', 'modelo', 'usuario')
    search_fields = ('detalhes', 'usuario__username')
    date_hierarchy = 'data_hora'
    list_per_page = 20
    
    def data_formatada(self, obj):
        return obj.data_hora.strftime("%d/%m/%Y %H:%M")
    data_formatada.short_description = 'Data/Hora'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(VideoTutorial)
class VideoTutorialAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'categoria', 'ordem', 'ativo', 'data_atualizacao')
    list_filter = ('categoria', 'ativo')
    search_fields = ('titulo', 'descricao')
    ordering = ('ordem', 'titulo')
    list_per_page = 20
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('titulo', 'descricao', 'categoria')
        }),
        ('URL e Ordem', {
            'fields': ('url_youtube', 'ordem')
        }),
        ('Status', {
            'fields': ('ativo',)
        })
    )

# Personalização do cabeçalho e título do admin
admin.site.site_header = 'Administração do Sistema de Controle de Acesso'
admin.site.site_title = 'Controle de Acesso'
admin.site.index_title = 'Painel de Administração'
