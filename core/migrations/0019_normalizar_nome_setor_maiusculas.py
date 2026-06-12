"""Converte nomes e setores existentes para caixa alta."""

from django.db import migrations


def _caixa_alta(valor):
    if not valor:
        return valor
    texto = str(valor).strip()
    return texto.upper() if texto else valor


def normalizar_nomes_setores(apps, schema_editor):
    for modelo_nome, campos in (
        ('Servidor', ('nome', 'setor')),
        ('ServidorTreinamento', ('nome', 'setor')),
        ('RegistroAcesso', ('setor',)),
        ('RegistroDashboard', ('setor',)),
        ('RegistroAcessoTreinamento', ('setor',)),
    ):
        Model = apps.get_model('core', modelo_nome)
        for registro in Model.objects.all().iterator():
            alterado = False
            for campo in campos:
                valor_atual = getattr(registro, campo, None)
                if not valor_atual:
                    continue
                valor_novo = _caixa_alta(valor_atual)
                if valor_novo != valor_atual:
                    setattr(registro, campo, valor_novo)
                    alterado = True
            if alterado:
                registro.save(update_fields=list(campos))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_perfilusuario_foto_sgp2rr'),
    ]

    operations = [
        migrations.RunPython(normalizar_nomes_setores, migrations.RunPython.noop),
    ]
