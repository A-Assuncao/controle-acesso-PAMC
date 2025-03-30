from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Servidor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100)),
                ('tipo_documento', models.CharField(choices=[('RG', 'RG'), ('CPF', 'CPF'), ('CNH', 'CNH')], max_length=3)),
                ('numero_documento', models.CharField(max_length=20)),
                ('placa_veiculo', models.CharField(blank=True, max_length=8, null=True)),
                ('tipo_funcionario', models.CharField(choices=[('EFETIVO', 'Efetivo'), ('TEMPORARIO', 'Temporário'), ('TERCEIRIZADO', 'Terceirizado')], max_length=20)),
                ('plantao', models.CharField(blank=True, choices=[('MANHA', 'Manhã - 07:30 às 13:30'), ('TARDE', 'Tarde - 13:30 às 19:30'), ('NOITE', 'Noite - 19:30 às 07:30')], max_length=10, null=True)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('ativo', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='RegistroAcesso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_hora', models.DateTimeField(auto_now_add=True)),
                ('observacao', models.TextField(blank=True)),
                ('isv', models.BooleanField(default=False)),
                ('tipo_acesso', models.CharField(choices=[('ENTRADA', 'Entrada'), ('SAIDA', 'Saída')], default='ENTRADA', max_length=7)),
                ('saida_pendente', models.BooleanField(default=False)),
                ('justificativa', models.TextField(blank=True)),
                ('data_hora_manual', models.DateTimeField(blank=True, null=True)),
                ('operador', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('servidor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='core.servidor')),
            ],
        ),
        migrations.CreateModel(
            name='LogAuditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_hora', models.DateTimeField(auto_now_add=True)),
                ('tipo_acao', models.CharField(choices=[('CRIACAO', 'Criação'), ('EDICAO', 'Edição'), ('EXCLUSAO', 'Exclusão')], max_length=8)),
                ('modelo', models.CharField(max_length=50)),
                ('objeto_id', models.IntegerField()),
                ('detalhes', models.TextField()),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ] 