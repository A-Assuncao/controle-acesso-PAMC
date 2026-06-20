# -*- coding: utf-8 -*-
"""Admin customizado (Servidor, RegistroAcesso, LogAuditoria, etc).

UI em admin_custom.css/js — ver static/.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import SafeString
from django.urls import reverse, path
from django.db.models import Count, Q
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.uploadedfile import SimpleUploadedFile

from . import admin_io
from django.contrib.admin import SimpleListFilter
from django.forms import ModelForm, Select, TextInput, Textarea
from datetime import datetime, timedelta
import json

from .models import (
    Servidor, RegistroAcesso, RegistroDashboard, 
    LogAuditoria, VideoTutorial, PerfilUsuario
)
from .utils import get_unidade_prisional


def _html_estatico(conteudo: str) -> SafeString:
    """HTML fixo para colunas do admin (Django 6+ rejeita format_html sem args)."""
    return SafeString(conteudo)

# =============================================================================
# WIDGETS E FORMULÁRIOS CUSTOMIZADOS
# =============================================================================

class ModernTextInput(TextInput):
    """Widget de texto com estilo moderno"""
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control',
            'style': 'border-radius: 6px; border: 1px solid #ddd;'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

class ModernTextarea(Textarea):
    """Widget de textarea com estilo moderno"""
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control',
            'style': 'border-radius: 6px; border: 1px solid #ddd; min-height: 80px;',
            'rows': 3
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

class ServidorForm(ModelForm):
    """Formulário customizado para Servidor"""
    class Meta:
        model = Servidor
        fields = '__all__'
        widgets = {
            'nome': ModernTextInput(attrs={
                'placeholder': 'Nome completo do servidor',
                'style': 'text-transform: uppercase',
            }),
            'numero_documento': ModernTextInput(attrs={'placeholder': 'CPF ou matrícula'}),
            'setor': ModernTextInput(attrs={
                'placeholder': 'Setor de trabalho',
                'style': 'text-transform: uppercase',
            }),
            'veiculo': ModernTextInput(attrs={'placeholder': 'Placa do veículo (opcional)'}),
        }

# =============================================================================
# FILTROS CUSTOMIZADOS AVANÇADOS
# =============================================================================

class PlantaoFilter(SimpleListFilter):
    """Filtro por plantão baseado no setor"""
    title = '🏢 Plantão'
    parameter_name = 'plantao'

    def lookups(self, request, model_admin):
        return (
            ('ALFA', '🅰️ ALFA'),
            ('BRAVO', '🅱️ BRAVO'),
            ('CHARLIE', '🅲️ CHARLIE'),
            ('DELTA', '🅳️ DELTA'),
            ('OUTROS', '🔸 Outros'),
        )

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == 'OUTROS':
                return queryset.exclude(
                    setor__icontains='ALFA'
                ).exclude(
                    setor__icontains='BRAVO'
                ).exclude(
                    setor__icontains='CHARLIE'
                ).exclude(
                    setor__icontains='DELTA'
                )
            else:
                return queryset.filter(setor__icontains=self.value())
        return queryset

class PeriodoFilter(SimpleListFilter):
    """Filtro por período temporal"""
    title = '📅 Período'
    parameter_name = 'periodo'

    def lookups(self, request, model_admin):
        return (
            ('hoje', '📌 Hoje'),
            ('ontem', '📍 Ontem'),
            ('semana', '📊 Esta Semana'),
            ('mes', '📈 Este Mês'),
            ('trimestre', '📋 Último Trimestre'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'hoje':
            return queryset.filter(data_hora__date=timezone.now().date())
        elif self.value() == 'ontem':
            ontem = timezone.now().date() - timedelta(days=1)
            return queryset.filter(data_hora__date=ontem)
        elif self.value() == 'semana':
            inicio_semana = timezone.now().date() - timedelta(days=timezone.now().weekday())
            return queryset.filter(data_hora__date__gte=inicio_semana)
        elif self.value() == 'mes':
            inicio_mes = timezone.now().replace(day=1).date()
            return queryset.filter(data_hora__date__gte=inicio_mes)
        elif self.value() == 'trimestre':
            tres_meses = timezone.now().date() - timedelta(days=90)
            return queryset.filter(data_hora__date__gte=tres_meses)
        return queryset

class StatusAtivoFilter(SimpleListFilter):
    """Filtro por status de atividade"""
    title = '🔄 Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return (
            ('ativo', '✅ Ativos'),
            ('inativo', '❌ Inativos'),
            ('com_registros', '📊 Com Registros'),
            ('sem_registros', '📭 Sem Registros'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'ativo':
            return queryset.filter(ativo=True)
        elif self.value() == 'inativo':
            return queryset.filter(ativo=False)
        elif self.value() == 'com_registros':
            return queryset.annotate(
                total_registros=Count('registroacesso')
            ).filter(total_registros__gt=0)
        elif self.value() == 'sem_registros':
            return queryset.annotate(
                total_registros=Count('registroacesso')
            ).filter(total_registros=0)
        return queryset

# =============================================================================
# AÇÕES EM MASSA PERSONALIZADAS
# =============================================================================

def ativar_servidores_selecionados(modeladmin, request, queryset):
    """Ativa servidores selecionados em massa"""
    updated = queryset.update(ativo=True)
    messages.success(
        request,
        f'✅ {updated} servidor(es) ativado(s) com sucesso!'
    )
ativar_servidores_selecionados.short_description = "✅ Ativar servidores selecionados"

def desativar_servidores_selecionados(modeladmin, request, queryset):
    """Desativa servidores selecionados em massa"""
    updated = queryset.update(ativo=False)
    messages.warning(
        request,
        f'❌ {updated} servidor(es) desativado(s) com sucesso!'
    )
desativar_servidores_selecionados.short_description = "❌ Desativar servidores selecionados"

def exportar_relatorio_servidores(modeladmin, request, queryset):
    """Exporta relatório dos servidores selecionados"""
    # Aqui você pode implementar a lógica de exportação
    messages.info(
        request,
        f'📊 Relatório de {queryset.count()} servidor(es) exportado!'
    )
exportar_relatorio_servidores.short_description = "📊 Exportar relatório dos selecionados"

def exportar_csv_action(modeladmin, request, queryset):
    """Action generica: exporta queryset selecionado para CSV."""
    model_name = queryset.model.__name__
    if model_name not in admin_io.EXPORT_FIELDS:
        messages.error(request, f'Modelo {model_name} nao suporta export CSV.')
        return
    return admin_io.exportar_csv(request, queryset, model_name)
exportar_csv_action.short_description = "📄 Exportar selecionados para CSV"

def exportar_xlsx_action(modeladmin, request, queryset):
    """Action generica: exporta queryset selecionado para XLSX."""
    model_name = queryset.model.__name__
    if model_name not in admin_io.EXPORT_FIELDS:
        messages.error(request, f'Modelo {model_name} nao suporta export XLSX.')
        return
    return admin_io.exportar_xlsx(request, queryset, model_name)
exportar_xlsx_action.short_description = "📊 Exportar selecionados para XLSX"

def importar_arquivo_action(modeladmin, request, queryset):
    """Redireciona para o form de importacao."""
    model_name = queryset.model.__name__
    return redirect(f'admin:core_{model_name.lower()}_importar')
importar_arquivo_action.short_description = "📥 Importar arquivo (CSV/XLSX)"

# =============================================================================
# AÇÕES PERSONALIZADAS PARA LOGS DE AUDITORIA
# =============================================================================

def exportar_logs_selecionados(modeladmin, request, queryset):
    """Exporta logs de auditoria selecionados para análise"""
    from django.http import HttpResponse
    import csv
    from datetime import datetime
    
    # Criar resposta HTTP para download
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="logs_auditoria_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Configurar CSV com UTF-8 BOM para Excel
    response.write('\ufeff')  # BOM para UTF-8
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Data/Hora', 'Usuário', 'Ação', 'Modelo', 'Objeto', 'IP', 'Detalhes'
    ])
    
    for log in queryset.order_by('-data_hora'):
        writer.writerow([
            log.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
            log.usuario.username,
            log.get_tipo_acao_display(),
            log.modelo,
            log.objeto_repr,
            log.ip_address or 'N/A',
            log.detalhes
        ])
    
    count = queryset.count()
    modeladmin.message_user(
        request,
        f'📊 {count} log(s) de auditoria exportado(s) com sucesso para análise!',
        messages.SUCCESS
    )
    
    return response

exportar_logs_selecionados.short_description = "📊 Exportar logs selecionados (CSV)"

def resetar_logs_selecionados(modeladmin, request, queryset):
    """Deleta os logs selecionados e cria 1 log de auditoria registrando o reset.

    ATENCAO: esta action e destrutiva. Para acionar, o admin deve
    selecionar os logs que deseja remover e confirmar via JS.
    """
    from .models import LogAuditoria

    total_deletados = queryset.count()
    if total_deletados == 0:
        modeladmin.message_user(request, 'Nenhum log selecionado.', messages.WARNING)
        return

    # Pega os primeiros 5 IDs para o log de rastreabilidade
    primeiros_ids = list(queryset.order_by('id').values_list('id', flat=True)[:5])

    queryset.delete()

    LogAuditoria.objects.create(
        usuario=request.user,
        tipo_acao='EXCLUSAO',
        modelo='LogAuditoria',
        objeto_id=None,
        detalhes=(
            f'Reset de logs via admin: {total_deletados} log(s) deletado(s) por {request.user.username}. '
            f'Primeiros IDs deletados: {primeiros_ids}'
        ),
    )

    modeladmin.message_user(
        request,
        f'🗑️ {total_deletados} log(s) deletado(s). Um log do proprio reset foi criado para rastreabilidade.',
        messages.SUCCESS,
    )

resetar_logs_selecionados.short_description = "🗑️ Resetar (deletar) logs selecionados"

def marcar_logs_para_analise(modeladmin, request, queryset):
    """Marca logs para análise futura (não modifica os logs, apenas registra a ação)"""
    count = queryset.count()
    
    # Registrar a ação de marcação no próprio sistema de logs
    from .models import LogAuditoria
    LogAuditoria.objects.create(
        usuario=request.user,
        tipo_acao='VIEW',
        modelo='LogAuditoria',
        objeto_repr=f'{count} logs marcados para análise',
        detalhes=f'Administrador {request.user.username} marcou {count} logs para análise detalhada'
    )
    
    modeladmin.message_user(
        request,
        f'🔍 {count} log(s) marcado(s) para análise. '
        f'Ação registrada no sistema de auditoria.',
        messages.INFO
    )

marcar_logs_para_analise.short_description = "🔍 Marcar logs para análise"

# =============================================================================
# AÇÕES PERSONALIZADAS PARA REGISTROS DE ACESSO
# =============================================================================

def exportar_registros_selecionados(modeladmin, request, queryset):
    """Exporta registros de acesso selecionados"""
    from django.http import HttpResponse
    import csv
    from datetime import datetime
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="registros_acesso_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    response.write('\ufeff')  # BOM para UTF-8
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Data/Hora', 'Servidor', 'Documento', 'Tipo Acesso', 'Setor', 
        'Veículo', 'ISV', 'Operador', 'Status', 'Observação'
    ])
    
    for reg in queryset.order_by('-data_hora'):
        writer.writerow([
            reg.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
            reg.servidor.nome,
            reg.servidor.numero_documento,
            reg.get_tipo_acesso_display(),
            reg.setor or reg.servidor.setor,
            reg.veiculo or reg.servidor.veiculo,
            'Sim' if reg.isv else 'Não',
            reg.operador.username,
            'Pendente' if reg.saida_pendente else 'Completo',
            reg.observacao or ''
        ])
    
    count = queryset.count()
    modeladmin.message_user(
        request,
        f'📊 {count} registro(s) de acesso exportado(s) com sucesso!',
        messages.SUCCESS
    )
    
    return response

exportar_registros_selecionados.short_description = "📊 Exportar registros selecionados (CSV)"

def finalizar_entradas_pendentes(modeladmin, request, queryset):
    """Finaliza entradas pendentes marcando saída automática"""
    from django.utils import timezone
    
    entradas_pendentes = queryset.filter(tipo_acesso='ENTRADA', saida_pendente=True)
    count = entradas_pendentes.count()
    
    if count == 0:
        modeladmin.message_user(
            request,
            '⚠️ Nenhuma entrada pendente encontrada nos registros selecionados.',
            messages.WARNING
        )
        return
    
    # Finalizar entradas pendentes
    for entrada in entradas_pendentes:
        entrada.data_hora_saida = timezone.now()
        entrada.saida_pendente = False
        entrada.observacao_saida = f'Finalizada automaticamente por {request.user.username}'
        entrada.save()
    
    modeladmin.message_user(
        request,
        f'✅ {count} entrada(s) pendente(s) finalizada(s) com sucesso!',
        messages.SUCCESS
    )

finalizar_entradas_pendentes.short_description = "✅ Finalizar entradas pendentes"

# =============================================================================
# AÇÕES PERSONALIZADAS PARA VÍDEOS TUTORIAIS
# =============================================================================

def ativar_videos_selecionados(modeladmin, request, queryset):
    """Ativa vídeos tutoriais selecionados"""
    updated = queryset.update(ativo=True)
    modeladmin.message_user(
        request,
        f'✅ {updated} vídeo(s) tutorial ativado(s) com sucesso!',
        messages.SUCCESS
    )

ativar_videos_selecionados.short_description = "✅ Ativar vídeos selecionados"

def desativar_videos_selecionados(modeladmin, request, queryset):
    """Desativa vídeos tutoriais selecionados"""
    updated = queryset.update(ativo=False)
    modeladmin.message_user(
        request,
        f'❌ {updated} vídeo(s) tutorial desativado(s) com sucesso!',
        messages.WARNING
    )

desativar_videos_selecionados.short_description = "❌ Desativar vídeos selecionados"

# =============================================================================
# ADMIN CUSTOMIZADO: SERVIDOR
# =============================================================================

@admin.register(Servidor)
class ServidorAdmin(admin.ModelAdmin):
    form = ServidorForm

    # Layout principal
    list_display = (
        'nome_formatado', 'documento_mascarado', 'setor_colorido',
        'veiculo_badge', 'status_visual', 'estatisticas_registros', 'acoes_rapidas'
    )

    def get_queryset(self, request):
        """Anota contagens agregadas de registros para evitar N+1."""
        qs = super().get_queryset(request)
        return qs.annotate(
            _total_registros=Count('registroacesso'),
            _total_entradas=Count('registroacesso', filter=Q(registroacesso__tipo_acesso='ENTRADA')),
            _total_saidas=Count('registroacesso', filter=Q(registroacesso__tipo_acesso='SAIDA')),
        )
    
    list_filter = (StatusAtivoFilter, PlantaoFilter, 'ativo', 'setor')
    search_fields = ('nome', 'numero_documento', 'setor', 'veiculo')
    ordering = ('nome',)
    list_per_page = 25
    list_max_show_all = 200  # Limite máximo em "Mostrar todos"
    actions = [
        ativar_servidores_selecionados,
        desativar_servidores_selecionados,
        exportar_relatorio_servidores,
        exportar_csv_action,
        exportar_xlsx_action,
    ]
    
    # Organização dos campos
    fieldsets = (
        ('👤 Informações Pessoais', {
            'fields': ('nome', 'numero_documento'),
            'classes': ('wide',),
        }),
        ('🏢 Informações Profissionais', {
            'fields': ('setor', 'veiculo'),
            'classes': ('wide',),
        }),
        ('⚙️ Configurações', {
            'fields': ('ativo',),
            'classes': ('collapse',),
        }),
    )
    
    # Métodos de exibição customizados
    def nome_formatado(self, obj):
        if obj.ativo:
            return format_html(
                '<strong style="color: #28a745;">{}</strong>',
                obj.nome
            )
        return format_html(
            '<span style="color: #6c757d; text-decoration: line-through;">{}</span>',
            obj.nome
        )
    nome_formatado.short_description = '👤 Nome'
    
    def documento_mascarado(self, obj):
        if len(obj.numero_documento) == 11:  # CPF
            return format_html(
                '<code>{}</code>',
                f"{obj.numero_documento[:3]}.{obj.numero_documento[3:6]}.{obj.numero_documento[6:9]}-{obj.numero_documento[9:]}"
            )
        return format_html('<code>{}</code>', obj.numero_documento)
    documento_mascarado.short_description = '🆔 Documento'
    
    def setor_colorido(self, obj):
        cores = {
            'ALFA': '#007bff', 'BRAVO': '#28a745', 
            'CHARLIE': '#ffc107', 'DELTA': '#dc3545'
        }
        cor = '#6c757d'  # cinza padrão
        
        for plantao, cor_plantao in cores.items():
            if plantao in obj.setor.upper():
                cor = cor_plantao
                break
                
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            cor, obj.setor[:20]
        )
    setor_colorido.short_description = '🏢 Setor'
    
    def veiculo_badge(self, obj):
        if obj.veiculo:
            return format_html(
                '<span style="background: #17a2b8; color: white; padding: 2px 6px; border-radius: 8px; font-size: 10px;">🚗 {}</span>',
                obj.veiculo
            )
        return _html_estatico('<span style="color: #6c757d;">-</span>')
    veiculo_badge.short_description = '🚗 Veículo'
    
    def status_visual(self, obj):
        if obj.ativo:
            return _html_estatico(
                '<span style="color: #28a745; font-size: 16px;" title="Ativo">●</span>'
            )
        return _html_estatico(
            '<span style="color: #dc3545; font-size: 16px;" title="Inativo">●</span>'
        )
    status_visual.short_description = '🔄 Status'
    
    def estatisticas_registros(self, obj):
        # Contagens já vêm anotadas pelo get_queryset (evita N+1)
        total = getattr(obj, '_total_registros', 0)
        entradas = getattr(obj, '_total_entradas', 0)
        saidas = getattr(obj, '_total_saidas', 0)

        url = reverse('admin:core_registroacesso_changelist') + f'?servidor__id={obj.id}'

        return format_html(
            '<a href="{}" style="text-decoration: none;">'
            '<div style="text-align: center; line-height: 1.2;">'
            '<strong style="color: #007bff; font-size: 14px;">{}</strong><br>'
            '<small style="color: #28a745;">↗️{}</small> '
            '<small style="color: #dc3545;">↙️{}</small>'
            '</div></a>',
            url, total, entradas, saidas
        )
    estatisticas_registros.short_description = '📊 Registros'
    estatisticas_registros.admin_order_field = '_total_registros'
    
    def acoes_rapidas(self, obj):
        urls = {
            'edit': reverse('admin:core_servidor_change', args=[obj.id]),
            'registros': reverse('admin:core_registroacesso_changelist') + f'?servidor__id={obj.id}',
        }
        
        return format_html(
            '<div style="white-space: nowrap;">'
            '<a href="{}" title="Editar" style="margin-right: 5px;">✏️</a>'
            '<a href="{}" title="Ver Registros" style="margin-right: 5px;">📋</a>'
            '</div>',
            urls['edit'], urls['registros']
        )
    acoes_rapidas.short_description = '⚡ Ações'

# =============================================================================
# MIXIN: colunas visuais compartilhadas (RegistroAcesso + RegistroDashboard)
# =============================================================================

class ColunasRegistroMixin:
    """Metodos de list_display reutilizados no admin de registros."""

    def data_hora_formatada(self, obj):
        return format_html(
            '<div style="text-align: center; line-height: 1.3;">'
            '<strong style="color: #007bff;">{}</strong><br>'
            '<small style="color: #6c757d;">{}</small>'
            '</div>',
            obj.data_hora.strftime("%d/%m/%Y"),
            obj.data_hora.strftime("%H:%M"),
        )

    data_hora_formatada.short_description = '📅 Data/Hora'

    def servidor_info(self, obj):
        url = reverse('admin:core_servidor_change', args=[obj.servidor.id])
        return format_html(
            '<a href="{}" style="text-decoration: none;">'
            '<div style="line-height: 1.3;">'
            '<strong style="color: #28a745;">{}</strong><br>'
            '<small style="color: #6c757d;">{}</small>'
            '</div></a>',
            url,
            obj.servidor.nome[:25],
            obj.servidor.numero_documento,
        )

    servidor_info.short_description = '👤 Servidor'

    def tipo_acesso_visual(self, obj):
        if obj.tipo_acesso == 'ENTRADA':
            return _html_estatico(
                '<span style="background: #28a745; color: white; padding: 4px 8px; '
                'border-radius: 12px; font-weight: bold;">ENTRADA</span>'
            )
        return _html_estatico(
            '<span style="background: #dc3545; color: white; padding: 4px 8px; '
            'border-radius: 12px; font-weight: bold;">SAIDA</span>'
        )

    tipo_acesso_visual.short_description = '🚪 Tipo'

    def operador_badge(self, obj):
        nome = obj.operador.get_full_name() or obj.operador.username
        return format_html(
            '<span style="background: #6f42c1; color: white; padding: 2px 6px; '
            'border-radius: 8px; font-size: 11px;">{}</span>',
            nome[:15],
        )

    operador_badge.short_description = '👨‍💼 Operador'

    def status_completo(self, obj):
        if obj.tipo_acesso == 'SAIDA':
            return _html_estatico(
                '<span style="color: #6f42c1; font-weight: bold;">Definitiva</span>'
            )
        if obj.saida_pendente:
            return _html_estatico(
                '<span style="color: #dc3545; font-weight: bold;">Pendente</span>'
            )
        return _html_estatico(
            '<span style="color: #28a745; font-weight: bold;">Concluido</span>'
        )

    status_completo.short_description = '📊 Status'


# =============================================================================
# ADMIN CUSTOMIZADO: REGISTRO DE ACESSO
# =============================================================================

@admin.register(RegistroAcesso)
class RegistroAcessoAdmin(ColunasRegistroMixin, admin.ModelAdmin):
    
    list_display = (
        'data_hora_formatada', 'servidor_info', 'tipo_acesso_visual', 
        'operador_badge', 'status_completo', 'isv_badge', 'acoes_registro'
    )
    
    list_filter = (
        PeriodoFilter, 'tipo_acesso', 'saida_pendente', 
        'status_alteracao', 'isv', PlantaoFilter
    )
    
    search_fields = (
        'servidor__nome', 'servidor__numero_documento', 
        'operador__username', 'operador__first_name', 'observacao'
    )
    
    date_hierarchy = 'data_hora'
    list_per_page = 30
    list_max_show_all = 150  # Limite máximo em "Mostrar todos"
    
    # Ações personalizadas para registros
    actions = [
        'exportar_registros_selecionados',
        'finalizar_entradas_pendentes',
        exportar_csv_action,
        exportar_xlsx_action,
    ]
    
    fieldsets = (
        ('📝 Informações Principais', {
            'fields': ('servidor', 'tipo_acesso', 'operador'),
            'classes': ('wide',),
        }),
        ('⏰ Dados Temporais', {
            'fields': ('data_hora', 'data_hora_saida'),
            'classes': ('wide',),
        }),
        ('🚗 Informações Complementares', {
            'fields': ('isv', 'veiculo', 'setor'),
            'classes': ('wide',),
        }),
        ('📄 Observações', {
            'fields': ('observacao', 'observacao_saida'),
            'classes': ('wide',),
        }),
        ('🔧 Controle e Auditoria', {
            'fields': (
                'saida_pendente', 'status_alteracao', 
                'justificativa', 'data_hora_alteracao'
            ),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('data_hora_alteracao',)
    
    def isv_badge(self, obj):
        if obj.isv:
            return _html_estatico(
                '<span style="background: #fd7e14; color: white; padding: 2px 4px; '
                'border-radius: 6px; font-size: 10px;">ISV</span>'
            )
        return _html_estatico('<span style="color: #6c757d;">-</span>')
    isv_badge.short_description = '🔒 ISV'
    
    def acoes_registro(self, obj):
        edit_url = reverse('admin:core_registroacesso_change', args=[obj.id])
        return format_html(
            '<a href="{}" title="Editar Registro" style="font-size: 16px;">✏️</a>',
            edit_url
        )
    acoes_registro.short_description = '⚡ Ações'

# =============================================================================
# ADMIN CUSTOMIZADO: PERFIL USUÁRIO
# =============================================================================

class PerfilUsuarioInline(admin.StackedInline):
    """Inline para editar perfil junto com o usuário"""
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = '👤 Perfil do Usuário'
    fieldsets = (
        ('🔐 Configurações de Acesso', {
            'fields': ('tipo_usuario', 'precisa_trocar_senha'),
        }),
    )

# =============================================================================
# ADMIN CUSTOMIZADO: OUTROS MODELOS
# =============================================================================

@admin.register(RegistroDashboard)
class RegistroDashboardAdmin(ColunasRegistroMixin, admin.ModelAdmin):
    list_display = (
        'data_hora_formatada', 'servidor_info', 'tipo_acesso_visual', 
        'operador_badge', 'status_completo'
    )
    list_filter = (PeriodoFilter, 'tipo_acesso', 'saida_pendente', 'isv')
    search_fields = ('servidor__nome', 'servidor__numero_documento')
    date_hierarchy = 'data_hora'
    list_per_page = 25
    list_max_show_all = 100  # Limite máximo em "Mostrar todos"
    
    # Ações disponíveis para registros do dashboard
    actions = [
        'exportar_registros_selecionados'
    ]

@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = (
        'data_hora_formatada', 'usuario_info', 'tipo_acao_badge', 
        'modelo_badge', 'detalhes_resumo'
    )
    list_filter = ('tipo_acao', 'modelo', 'usuario', PeriodoFilter)
    search_fields = ('detalhes', 'usuario__username', 'usuario__first_name')
    date_hierarchy = 'data_hora'
    list_per_page = 25  # Reduzido de 20 para 25 para melhor balanço
    list_max_show_all = 100  # Limite máximo em "Mostrar todos"
    
    # Ações personalizadas para logs (seguras)
    actions = ['exportar_logs_selecionados', 'marcar_logs_para_analise', resetar_logs_selecionados]

    def data_hora_formatada(self, obj):
        return format_html(
            '<div style="text-align: center;">'
            '<strong>{}</strong><br>'
            '<small>{}</small>'
            '</div>',
            obj.data_hora.strftime("%d/%m/%Y"),
            obj.data_hora.strftime("%H:%M:%S")
        )
    data_hora_formatada.short_description = '📅 Data/Hora'
    
    def usuario_info(self, obj):
        nome = obj.usuario.get_full_name() or obj.usuario.username
        return format_html(
            '<strong style="color: #007bff;">{}</strong>',
            nome
        )
    usuario_info.short_description = '👤 Usuário'
    
    def tipo_acao_badge(self, obj):
        cores = {
            'CREATE': '#28a745', 'UPDATE': '#ffc107', 
            'DELETE': '#dc3545', 'VIEW': '#17a2b8'
        }
        cor = cores.get(obj.tipo_acao, '#6c757d')
        
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 6px; border-radius: 8px; font-size: 11px;">{}</span>',
            cor, obj.tipo_acao
        )
    tipo_acao_badge.short_description = '🔧 Ação'
    
    def modelo_badge(self, obj):
        return format_html(
            '<span style="background: #6f42c1; color: white; padding: 2px 6px; border-radius: 8px; font-size: 11px;">{}</span>',
            obj.modelo
        )
    modelo_badge.short_description = '📋 Modelo'
    
    def detalhes_resumo(self, obj):
        detalhes = obj.detalhes[:50] + '...' if len(obj.detalhes) > 50 else obj.detalhes
        return format_html('<small style="color: #6c757d;">{}</small>', detalhes)
    detalhes_resumo.short_description = '📄 Detalhes'
    
    # Somente leitura para logs
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # Apenas superusers podem deletar logs

@admin.register(VideoTutorial)
class VideoTutorialAdmin(admin.ModelAdmin):
    list_display = (
        'titulo_formatado', 'categoria_badge', 'ordem_visual', 
        'status_ativo', 'data_atualizacao_formatada', 'acoes_video'
    )
    list_filter = ('categoria', 'ativo')
    search_fields = ('titulo', 'descricao')
    ordering = ('ordem', 'titulo')
    list_per_page = 15
    list_max_show_all = 50  # Limite máximo em "Mostrar todos"
    
    # Ações personalizadas para vídeos
    actions = [
        'ativar_videos_selecionados',
        'desativar_videos_selecionados'
    ]
    
    fieldsets = (
        ('📺 Informações do Vídeo', {
            'fields': ('titulo', 'descricao', 'categoria'),
            'classes': ('wide',),
        }),
        ('🔗 Configurações', {
            'fields': ('url_youtube', 'ordem'),
            'classes': ('wide',),
        }),
        ('⚙️ Status', {
            'fields': ('ativo',),
        }),
    )
    
    def titulo_formatado(self, obj):
        return format_html(
            '<strong style="color: #007bff;">{}</strong><br>'
            '<small style="color: #6c757d;">{}</small>',
            obj.titulo,
            obj.descricao[:50] + '...' if len(obj.descricao) > 50 else obj.descricao
        )
    titulo_formatado.short_description = '📺 Título'
    
    def categoria_badge(self, obj):
        cores = {
            'BASICO': '#28a745', 'AVANCADO': '#dc3545',
            'TUTORIAL': '#007bff', 'DICAS': '#ffc107'
        }
        cor = cores.get(obj.categoria, '#6c757d')
        
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            cor, obj.get_categoria_display()
        )
    categoria_badge.short_description = '🏷️ Categoria'
    
    def ordem_visual(self, obj):
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 2px 6px; border-radius: 50%; font-weight: bold;">{}</span>',
            obj.ordem
        )
    ordem_visual.short_description = '#️⃣ Ordem'
    
    def status_ativo(self, obj):
        if obj.ativo:
            return _html_estatico(
                '<span style="color: #28a745; font-size: 16px;">●</span> Ativo'
            )
        return _html_estatico(
            '<span style="color: #dc3545; font-size: 16px;">●</span> Inativo'
        )
    status_ativo.short_description = '🔄 Status'
    
    def data_atualizacao_formatada(self, obj):
        return format_html(
            '<small>{}</small>',
            obj.data_atualizacao.strftime("%d/%m/%Y")
        )
    data_atualizacao_formatada.short_description = '📅 Atualizado'
    
    def acoes_video(self, obj):
        edit_url = reverse('admin:core_videotutorial_change', args=[obj.id])
        return format_html(
            '<a href="{}" title="Editar" style="margin-right: 5px;">✏️</a>'
            '<a href="{}" target="_blank" title="Ver Vídeo">📺</a>',
            edit_url, obj.url_youtube
        )
    acoes_video.short_description = '⚡ Ações'

# =============================================================================
# PERSONALIZAÇÃO GLOBAL DO ADMIN
# =============================================================================

# Títulos e cabeçalhos personalizados
unidade = get_unidade_prisional()
admin.site.site_header = _html_estatico(
    f'<span style="color: #007bff; font-weight: bold;">Sistema de Controle de Acesso {unidade}</span>'
)
admin.site.site_title = f'Controle de Acesso {unidade}'
def importar_view(request, model_name):
    """View customizada de import - GET mostra form, POST processa."""
    if model_name not in admin_io.EXPORT_FIELDS:
        messages.error(request, f'Modelo {model_name} nao suporta import.')
        return redirect('/admin/')

    if request.method == 'POST':
        arquivo = request.FILES.get('arquivo')
        if not arquivo:
            messages.error(request, 'Nenhum arquivo enviado.')
            return redirect(request.path)

        result = admin_io.importar_arquivo(arquivo, model_name, request.user)
        if result['criados']:
            messages.success(request, f"{result['criados']} registro(s) importado(s).")
        if result['erros']:
            for erro in result['erros'][:10]:
                messages.warning(request, erro)
            if len(result['erros']) > 10:
                messages.warning(request, f"... e mais {len(result['erros']) - 10} erro(s).")

        # Volta para lista do modelo
        app_label = 'core'
        return redirect(f'/admin/{app_label}/{model_name.lower()}/')

    return render(request, 'admin/importar_form.html', {
        'model_name': model_name,
        'title': f'Importar {model_name}',
    })


def _add_import_url(admin_class, model_name):
    """Adiciona URL customizada de import ao get_urls() do ModelAdmin."""
    original_get_urls = admin_class.get_urls

    def get_urls(self):
        from django.urls import path
        urls = original_get_urls(self)
        custom = [
            path(
                'importar/',
                admin.site.admin_view(
                    lambda r, mn=model_name: importar_view(r, mn)
                ),
                name=f'core_{model_name.lower()}_importar',
            ),
        ]
        return custom + urls

    admin_class.get_urls = get_urls


_add_import_url(ServidorAdmin, 'Servidor')
_add_import_url(RegistroAcessoAdmin, 'RegistroAcesso')


admin.site.index_title = _html_estatico(
    '<span style="color: #28a745;">Painel de Administracao Avancado</span>'
)

# CSS customizado para melhorar a aparência
admin.site.enable_nav_sidebar = True

# =============================================================================
# CONFIGURAÇÃO DE MÍDIA PERSONALIZADA
# =============================================================================

class AdminMediaMixin:
    """Mixin para incluir CSS e JS customizados em todas as páginas do admin"""
    
    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }
        js = ('js/admin_custom.js',)

# Aplicar o mixin em todas as classes Admin
for admin_class in [
    ServidorAdmin, RegistroAcessoAdmin, RegistroDashboardAdmin, 
    LogAuditoriaAdmin, VideoTutorialAdmin
]:
    # Adicionar o mixin dinamicamente
    admin_class.Media = AdminMediaMixin.Media
