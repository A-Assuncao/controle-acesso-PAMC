from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator

class Servidor(models.Model):
    TIPO_FUNCIONARIO_CHOICES = [
        ('PLANTONISTA', 'Plantonista'),
        ('EXPEDIENTE', 'Expediente'),
        ('VISITANTE', 'Visitante'),
        ('TERCEIRIZADO', 'Terceirizado'),
    ]
    
    PLANTAO_CHOICES = [
        ('ALFA', 'ALFA'),
        ('BRAVO', 'BRAVO'),
        ('CHARLIE', 'CHARLIE'),
        ('DELTA', 'DELTA'),
    ]
    
    nome = models.CharField(max_length=100)
    numero_documento = models.CharField(max_length=20)
    tipo_funcionario = models.CharField(max_length=20, choices=TIPO_FUNCIONARIO_CHOICES, default='VISITANTE')
    plantao = models.CharField(max_length=10, choices=PLANTAO_CHOICES, null=True, blank=True)
    setor = models.CharField(max_length=100)
    veiculo = models.CharField(
        max_length=7, 
        null=True, 
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{3}[0-9][0-9A-Z][0-9]{2}$',
                message='Placa inválida. Use o formato AAA0A00 ou AAA0000.',
                code='placa_invalida'
            )
        ]
    )
    ativo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nome} ({self.numero_documento})"
    
    class Meta:
        verbose_name = 'Servidor'
        verbose_name_plural = 'Servidores'
        ordering = ['nome']

class RegistroAcesso(models.Model):
    TIPO_ACESSO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    ]
    
    STATUS_ALTERACAO_CHOICES = [
        ('ORIGINAL', 'Original'),
        ('EDITADO', 'Editado'),
        ('EXCLUIDO', 'Excluído'),
    ]
    
    servidor = models.ForeignKey(Servidor, on_delete=models.PROTECT)
    operador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='registros_criados')
    tipo_acesso = models.CharField(max_length=10, choices=TIPO_ACESSO_CHOICES)
    data_hora = models.DateTimeField()
    observacao = models.TextField(null=True, blank=True)
    isv = models.BooleanField(default=False)
    veiculo = models.CharField(max_length=50, null=True, blank=True)
    setor = models.CharField(max_length=100, null=True, blank=True)
    data_hora_saida = models.DateTimeField(null=True, blank=True)
    operador_saida = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='registros_saida')
    observacao_saida = models.TextField(null=True, blank=True)
    saida_pendente = models.BooleanField(default=True)
    status_alteracao = models.CharField(max_length=10, choices=STATUS_ALTERACAO_CHOICES, null=True, blank=True)
    data_hora_alteracao = models.DateTimeField(null=True, blank=True)
    justificativa = models.TextField(null=True, blank=True)
    registro_original = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.servidor.nome} - {self.get_tipo_acesso_display()} em {self.data_hora}"
    
    def save(self, *args, **kwargs):
        if not self.data_hora:
            self.data_hora = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Histórico'
        verbose_name_plural = 'Histórico'
        ordering = ['-data_hora']

class RegistroDashboard(models.Model):
    """
    Modelo para registros ativos no dashboard.
    Este modelo é uma cópia simplificada do RegistroAcesso, contendo apenas
    os campos necessários para o dashboard do plantão atual.
    """
    TIPO_ACESSO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    ]
    
    servidor = models.ForeignKey(Servidor, on_delete=models.PROTECT)
    operador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='dashboard_registros_criados')
    tipo_acesso = models.CharField(max_length=10, choices=TIPO_ACESSO_CHOICES)
    data_hora = models.DateTimeField()
    isv = models.BooleanField(default=False)
    veiculo = models.CharField(max_length=50, null=True, blank=True)
    setor = models.CharField(max_length=100, null=True, blank=True)
    data_hora_saida = models.DateTimeField(null=True, blank=True)
    operador_saida = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='dashboard_registros_saida')
    saida_pendente = models.BooleanField(default=True)
    registro_historico = models.ForeignKey(RegistroAcesso, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.servidor.nome} - {self.get_tipo_acesso_display()} em {self.data_hora}"
    
    def save(self, *args, **kwargs):
        if not self.data_hora:
            self.data_hora = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Dashboard'
        verbose_name_plural = 'Dashboard'
        ordering = ['-data_hora']

class LogAuditoria(models.Model):
    TIPO_ACAO_CHOICES = [
        ('CRIACAO', 'Criação'),
        ('EDICAO', 'Edição'),
        ('EXCLUSAO', 'Exclusão'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    tipo_acao = models.CharField(max_length=10, choices=TIPO_ACAO_CHOICES)
    modelo = models.CharField(max_length=50)
    objeto_id = models.IntegerField(null=True, blank=True)
    detalhes = models.TextField()
    data_hora = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_tipo_acao_display()} por {self.usuario.username} em {self.data_hora}"
    
    class Meta:
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'
        ordering = ['-data_hora']
