from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from core.models import RegistroAcesso, Pessoa, LogAuditoria

class Command(BaseCommand):
    help = 'Cria o grupo de Administradores com as permissões necessárias'

    def handle(self, *args, **kwargs):
        # Criar ou obter o grupo Administradores
        admin_group, created = Group.objects.get_or_create(name='Administradores')
        
        # Obter os content types dos modelos
        registro_ct = ContentType.objects.get_for_model(RegistroAcesso)
        pessoa_ct = ContentType.objects.get_for_model(Pessoa)
        log_ct = ContentType.objects.get_for_model(LogAuditoria)
        
        # Definir as permissões para cada modelo
        permissions = [
            # Permissões para RegistroAcesso
            Permission.objects.get(content_type=registro_ct, codename='view_registroacesso'),
            Permission.objects.get(content_type=registro_ct, codename='add_registroacesso'),
            Permission.objects.get(content_type=registro_ct, codename='change_registroacesso'),
            
            # Permissões para Pessoa
            Permission.objects.get(content_type=pessoa_ct, codename='view_pessoa'),
            Permission.objects.get(content_type=pessoa_ct, codename='add_pessoa'),
            Permission.objects.get(content_type=pessoa_ct, codename='change_pessoa'),
            
            # Permissões para LogAuditoria
            Permission.objects.get(content_type=log_ct, codename='view_logauditoria'),
        ]
        
        # Adicionar as permissões ao grupo
        admin_group.permissions.set(permissions)
        
        self.stdout.write(
            self.style.SUCCESS('Grupo de Administradores criado/atualizado com sucesso!')
        ) 