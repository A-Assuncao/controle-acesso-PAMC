from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import RegistroAcesso, Servidor, LogAuditoria

class Command(BaseCommand):
    help = 'Cria o grupo de Administradores com as permissões necessárias'

    def handle(self, *args, **kwargs):
        # Criar ou obter o grupo Administradores
        admin_group, created = Group.objects.get_or_create(name='Administradores')
        
        # Obter os content types dos modelos
        registro_ct = ContentType.objects.get_for_model(RegistroAcesso)
        servidor_ct = ContentType.objects.get_for_model(Servidor)
        log_ct = ContentType.objects.get_for_model(LogAuditoria)
        
        # Definir as permissões para cada modelo
        permissions = [
            # Permissões para RegistroAcesso
            Permission.objects.get(content_type=registro_ct, codename='view_registroacesso'),
            Permission.objects.get(content_type=registro_ct, codename='add_registroacesso'),
            Permission.objects.get(content_type=registro_ct, codename='change_registroacesso'),
            
            # Permissões para Servidor
            Permission.objects.get(content_type=servidor_ct, codename='view_servidor'),
            Permission.objects.get(content_type=servidor_ct, codename='add_servidor'),
            Permission.objects.get(content_type=servidor_ct, codename='change_servidor'),
            
            # Permissões para LogAuditoria
            Permission.objects.get(content_type=log_ct, codename='view_logauditoria'),
        ]
        
        # Adicionar as permissões ao grupo
        admin_group.permissions.set(permissions)
        
        self.stdout.write(
            self.style.SUCCESS('Grupo de Administradores criado/atualizado com sucesso!')
        )
