"""Signals para o admin Django.

Captura diff antes/depois em alteracoes de objetos via pre_save,
armazena no proprio instance via atributo _admin_diff, e expõe
helper para ModelAdmin injetar o contexto no template.
"""

import json
from datetime import date, datetime

from django.db.models.signals import pre_save
from django.dispatch import receiver

# Modelos que devem ter diff capturado.
MODELOS_COM_DIFF = {
    'Servidor': ['nome', 'numero_documento', 'tipo_funcionario', 'plantao', 'setor', 'veiculo', 'ativo'],
    'RegistroAcesso': ['tipo_acesso', 'observacao', 'isv', 'veiculo', 'setor', 'observacao_saida', 'saida_pendente', 'status_alteracao', 'justificativa'],
    'VideoTutorial': ['titulo', 'descricao', 'url_youtube', 'ordem', 'categoria', 'ativo'],
}


def _normalizar(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if v is None:
        return ''
    return v


def calcular_diff_entre(antes, depois, modelo_nome):
    """Calcula diff entre 2 instancias. Retorna dict {campo: {antes, depois}} ou None."""
    campos = MODELOS_COM_DIFF.get(modelo_nome, [])
    alteracoes = {}
    for campo in campos:
        v_antes = _normalizar(getattr(antes, campo, None))
        v_depois = _normalizar(getattr(depois, campo, None))
        if v_antes != v_depois:
            alteracoes[campo] = {'antes': v_antes, 'depois': v_depois}
    return alteracoes if alteracoes else None


@receiver(pre_save)
def capturar_estado_antes(sender, instance, **kwargs):
    """Captura estado atual do banco antes do save."""
    if sender.__name__ not in MODELOS_COM_DIFF:
        return
    if not instance.pk:
        instance._admin_diff_antes = None
        return
    try:
        instance._admin_diff_antes = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._admin_diff_antes = None


def diff_response_change(view, request, obj):
    """
    Helper para ModelAdmin: apos um save bem-sucedido, gera o
    diff antes/depois e adiciona em messages para exibicao.
    Chame do response_change() do ModelAdmin.
    """
    if obj is None or not hasattr(obj, '_admin_diff_antes'):
        return None
    antes = obj._admin_diff_antes
    if antes is None:
        # Objeto novo (criacao) - nao ha diff, mas pode registrar
        from django.contrib import messages
        messages.success(request, f'✅ {obj.__class__.__name__} criado com sucesso.')
        return None

    diff = calcular_diff_entre(antes, obj, obj.__class__.__name__)
    if not diff:
        return None

    from django.contrib import messages
    diff_str = ' | '.join(f"{c}: '{m['antes']}' -> '{m['depois']}'" for c, m in diff.items())
    messages.info(request, f'📝 Alteracoes: {diff_str}')

    # Log de auditoria consolidado
    from .models import LogAuditoria
    LogAuditoria.objects.create(
        usuario=request.user,
        tipo_acao='EDICAO',
        modelo=obj.__class__.__name__,
        objeto_id=obj.pk,
        detalhes=f'Editado via admin: {diff_str}',
    )
    return diff