from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator

class Servidor(models.Model):
    TIPOS_FUNCIONARIO = [
        ('EFETIVO', 'Efetivo'),
        ('TEMPORARIO', 'Temporário'),
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
    veiculo = models.CharField(max_length=50, blank=True, null=True)
    setor = models.CharField(max_length=100, blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    
    def __str__(self):
        return str(self.nome)

class RegistroAcesso(models.Model):
    TIPOS_ACESSO = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    ]
    
    servidor = models.ForeignKey(Servidor, on_delete=models.PROTECT)
    data_hora = models.DateTimeField(auto_now_add=True)
    operador = models.ForeignKey(User, on_delete=models.PROTECT)
    observacao = models.TextField(blank=True)
    isv = models.BooleanField(default=False)
    tipo_acesso = models.CharField(max_length=7, choices=TIPOS_ACESSO, default='ENTRADA')
    saida_pendente = models.BooleanField(default=False)
    justificativa = models.TextField(blank=True)
    data_hora_manual = models.DateTimeField(null=True, blank=True)
    veiculo = models.CharField(max_length=50, blank=True, null=True)
    setor = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return str(f"{self.servidor.nome} - {self.get_tipo_acesso_display()} - {self.data_hora}")

class LogAuditoria(models.Model):
    TIPOS_ACAO = [
        ('CRIACAO', 'Criação'),
        ('EDICAO', 'Edição'),
        ('EXCLUSAO', 'Exclusão'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    data_hora = models.DateTimeField(auto_now_add=True)
    tipo_acao = models.CharField(max_length=8, choices=TIPOS_ACAO)
    modelo = models.CharField(max_length=50)
    objeto_id = models.IntegerField()
    detalhes = models.TextField()
    
    def __str__(self):
        return str(f"{self.get_tipo_acao_display()} de {self.modelo} por {self.usuario.username}")
