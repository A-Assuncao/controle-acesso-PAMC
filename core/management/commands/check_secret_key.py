"""
Comando de gerenciamento para verificar informações sobre a SECRET_KEY.
"""

import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management.utils import get_random_secret_key


class Command(BaseCommand):
    help = 'Verifica informações sobre a SECRET_KEY configurada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--generate',
            action='store_true',
            help='Gera uma nova SECRET_KEY para uso em produção',
        )
        parser.add_argument(
            '--show-current',
            action='store_true',
            help='Mostra informações sobre a SECRET_KEY atual (não mostra a chave completa)',
        )

    def handle(self, *args, **options):
        if options['generate']:
            new_key = get_random_secret_key()
            self.stdout.write('\n' + '='*60)
            self.stdout.write(self.style.SUCCESS('🔑 NOVA SECRET_KEY GERADA:'))
            self.stdout.write('='*60)
            self.stdout.write(f'{new_key}')
            self.stdout.write('='*60)
            self.stdout.write('📋 Copie a chave acima e cole no seu arquivo .env:')
            self.stdout.write('   DJANGO_SECRET_KEY=' + new_key)
            self.stdout.write('='*60 + '\n')
            return

        if options['show_current']:
            current_key = settings.SECRET_KEY
            key_from_env = os.getenv('DJANGO_SECRET_KEY')
            
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('🔍 INFORMAÇÕES DA SECRET_KEY'))
            self.stdout.write('='*50)
            
            if key_from_env:
                self.stdout.write('📍 Origem: Arquivo .env (DJANGO_SECRET_KEY)')
                self.stdout.write(f'📏 Tamanho: {len(current_key)} caracteres')
                self.stdout.write(f'🔗 Primeiros 10 chars: {current_key[:10]}...')
                self.stdout.write('✅ STATUS: Chave fixa definida (recomendado para produção)')
            else:
                self.stdout.write('📍 Origem: Gerada automaticamente pelo Django')
                self.stdout.write(f'📏 Tamanho: {len(current_key)} caracteres')
                self.stdout.write(f'🔗 Primeiros 10 chars: {current_key[:10]}...')
                self.stdout.write('⚠️  STATUS: Chave temporária (muda a cada restart)')
                self.stdout.write('💡 DICA: Para produção, defina DJANGO_SECRET_KEY no .env')
            
            self.stdout.write('='*50 + '\n')
            return

        # Comportamento padrão - mostra resumo
        current_key = settings.SECRET_KEY
        key_from_env = os.getenv('DJANGO_SECRET_KEY')
        
        self.stdout.write('\n' + self.style.SUCCESS('🔑 STATUS DA SECRET_KEY'))
        self.stdout.write('-' * 30)
        
        if key_from_env:
            self.stdout.write('✅ Chave configurada no .env')
            self.stdout.write('✅ Pronta para produção')
        else:
            self.stdout.write('⚠️  Chave gerada automaticamente')
            self.stdout.write('💡 Para produção, configure no .env')
        
        self.stdout.write(f'📏 Tamanho: {len(current_key)} caracteres')
        self.stdout.write('')
        self.stdout.write('Opções disponíveis:')
        self.stdout.write('  --generate      Gera nova chave para produção')
        self.stdout.write('  --show-current  Mostra detalhes da chave atual')
        self.stdout.write('') 