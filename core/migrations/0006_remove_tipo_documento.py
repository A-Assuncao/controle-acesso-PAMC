# Generated by Django 5.1.6 on 2025-03-30 17:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_remove_servidor_placa_veiculo_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='servidor',
            name='tipo_documento',
        ),
    ]
