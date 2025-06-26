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

class ServidorTreinamento(models.Model):
    """
    Versão de treinamento do modelo Servidor para ambiente de aprendizagem
    """
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
        verbose_name = 'Servidor (Treinamento)'
        verbose_name_plural = 'Servidores (Treinamento)'
        ordering = ['nome']

class RegistroAcessoTreinamento(models.Model):
    """
    Versão de treinamento do modelo RegistroAcesso para ambiente de aprendizagem
    """
    TIPO_ACESSO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    ]
    
    servidor = models.ForeignKey(ServidorTreinamento, on_delete=models.PROTECT)
    operador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='registros_treinamento')
    tipo_acesso = models.CharField(max_length=10, choices=TIPO_ACESSO_CHOICES)
    data_hora = models.DateTimeField()
    observacao = models.TextField(null=True, blank=True)
    isv = models.BooleanField(default=False)
    veiculo = models.CharField(max_length=50, null=True, blank=True)
    setor = models.CharField(max_length=100, null=True, blank=True)
    data_hora_saida = models.DateTimeField(null=True, blank=True)
    operador_saida = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='registros_saida_treinamento')
    observacao_saida = models.TextField(null=True, blank=True)
    saida_pendente = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.servidor.nome} - {self.get_tipo_acesso_display()} em {self.data_hora}"
    
    def save(self, *args, **kwargs):
        if not self.data_hora:
            self.data_hora = timezone.now()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Registro (Treinamento)'
        verbose_name_plural = 'Registros (Treinamento)'
        ordering = ['-data_hora']

class VideoTutorial(models.Model):
    """Modelo para armazenar tutoriais em vídeo do sistema."""
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    url_youtube = models.URLField(
        help_text="URL do vídeo no YouTube",
        default="https://www.youtube.com/watch?v=placeholder"
    )
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição do vídeo")
    categoria = models.CharField(max_length=50, choices=[
        ('ENTRADA', 'Registro de Entrada'),
        ('SAIDA', 'Registro de Saída'),
        ('EDICAO', 'Edição de Registros'),
        ('EXCLUSAO', 'Exclusão de Registros'),
        ('PLANILHA', 'Gerenciamento da Planilha'),
        ('GERAL', 'Funcionalidades Gerais')
    ])
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Vídeo Tutorial'
        verbose_name_plural = 'Vídeos Tutoriais'
        ordering = ['ordem', 'titulo']

    def __str__(self):
        return self.titulo

    def get_embed_url(self):
        """Retorna a URL de incorporação do YouTube."""
        # Extrai o ID do vídeo da URL do YouTube
        video_id = None
        if 'youtube.com/watch?v=' in self.url_youtube:
            video_id = self.url_youtube.split('watch?v=')[1].split('&')[0]
        elif 'youtu.be/' in self.url_youtube:
            video_id = self.url_youtube.split('youtu.be/')[1]
        
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"
        return None

class PerfilUsuario(models.Model):
    """
    Modelo para armazenar informações adicionais de usuários.
    """
    TIPO_USUARIO_CHOICES = [
        ('OPERADOR', 'Operador'),
        ('VISUALIZACAO', 'Visualização'),
        ('STAFF', 'Staff'),
        ('ADMIN', 'Administrador'),
    ]
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    precisa_trocar_senha = models.BooleanField(default=False)
    senha_temporaria = models.CharField(max_length=50, blank=True, null=True)
    tipo_usuario = models.CharField(max_length=15, choices=TIPO_USUARIO_CHOICES, default='OPERADOR')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Perfil de {self.usuario.username} ({self.get_tipo_usuario_display()})"
    
    def pode_registrar_acesso(self):
        """Verifica se o usuário pode registrar acessos no ambiente de produção."""
        return self.tipo_usuario in ['OPERADOR', 'STAFF', 'ADMIN']
    
    def pode_excluir_registros(self):
        """Verifica se o usuário pode excluir registros."""
        return self.tipo_usuario in ['STAFF', 'ADMIN']
    
    def pode_gerenciar_servidores(self):
        """Verifica se o usuário pode gerenciar servidores."""
        return self.tipo_usuario in ['STAFF', 'ADMIN']
    
    def pode_limpar_dashboard(self):
        """Verifica se o usuário pode limpar o dashboard."""
        return self.tipo_usuario in ['STAFF', 'ADMIN']
    
    def pode_saida_definitiva(self):
        """Verifica se o usuário pode registrar saída definitiva."""
        return self.tipo_usuario in ['OPERADOR', 'STAFF', 'ADMIN']
    
    class Meta:
        verbose_name = 'Perfil de Usuário'
        verbose_name_plural = 'Perfis de Usuários'
