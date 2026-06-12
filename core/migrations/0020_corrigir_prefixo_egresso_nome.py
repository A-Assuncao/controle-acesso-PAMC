"""Restaura prefixo 'Egresso: ' em minúsculas nos nomes de saída definitiva."""

import unicodedata

from django.db import migrations

PREFIXO_EGRESSO = 'Egresso: '


def _normalizar_texto(texto):
    if not texto:
        return ''
    texto_sem_acento = unicodedata.normalize('NFD', str(texto))
    texto_sem_acento = ''.join(
        char for char in texto_sem_acento if unicodedata.category(char) != 'Mn'
    )
    return texto_sem_acento.lower()


def _caixa_alta_nome_servidor(valor):
    if not valor:
        return valor
    texto = str(valor).strip()
    if not texto:
        return valor

    if _normalizar_texto(texto).startswith('egresso:'):
        _, _, resto = texto.partition(':')
        resto = resto.strip()
        if resto:
            return f'{PREFIXO_EGRESSO}{resto.upper()}'
        return PREFIXO_EGRESSO.rstrip()

    return texto.upper()


def corrigir_prefixo_egresso(apps, schema_editor):
    for modelo_nome in ('Servidor', 'ServidorTreinamento'):
        Model = apps.get_model('core', modelo_nome)
        for registro in Model.objects.all().iterator():
            nome_atual = registro.nome
            if not nome_atual:
                continue
            nome_novo = _caixa_alta_nome_servidor(nome_atual)
            if nome_novo != nome_atual:
                registro.nome = nome_novo
                registro.save(update_fields=['nome'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_normalizar_nome_setor_maiusculas'),
    ]

    operations = [
        migrations.RunPython(corrigir_prefixo_egresso, migrations.RunPython.noop),
    ]
