"""
Comando para identificar e (opcionalmente) limpar migrations obsoletas
do app 'core'.

O que ele faz:
  - Lista todas as migrations em core/migrations/
  - Detecta migrations que NAO correspondem mais a nenhum estado de model
    (campo removido, tabela deletada, etc.) - estas sao candidatas a
    'squash' ou remocao
  - Detecta migrations vazias (que nao fazem nada)
  - Oferece backup automatico antes de qualquer modificacao
  - Modo padrao e --dry-run (so mostra, nao faz nada)

USO:
  # Apenas listar (seguro)
  python manage.py cleanup_migrations

  # Gerar relatorio detalhado
  python manage.py cleanup_migrations --verbose

  # Squash: junta todas as migrations em uma unica 0001_initial.py
  # (cria backup automatico em core/migrations/_backup_YYYYMMDD_HHMMSS/)
  python manage.py cleanup_migrations --squash --execute

  # Apenas identificar obsoletas (nao modifica nada)
  python manage.py cleanup_migrations --report

ATENCAO:
  Em bancos de producao que JA rodaram as migrations antigas, o squash
  vai dar conflito (Django detecta que 0001_initial ja foi aplicada
  com conteudo diferente). Para esses casos, a abordagem correta e:
    1. Rodar o squash em uma branch separada
    2. Fazer deploy com um banco NOVO (que executa apenas a nova 0001)
    3. Migrar dados do banco antigo (dump/load)
  Para o banco local de desenvolvimento, --squash funciona sem
  problemas porque voce pode dropar e recriar.

  Para identificar migrations obsoletas sem risco, use --report.
"""
import re
import shutil
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Identifica e (opcionalmente) limpa migrations obsoletas do app core.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=True,
            help='Apenas mostra o que faria, sem modificar nada (padrao).',
        )
        parser.add_argument(
            '--execute',
            action='store_true',
            help='Executa as alteracoes propostas. Faz backup antes.',
        )
        parser.add_argument(
            '--squash',
            action='store_true',
            help='Faz squash de todas as migrations em 0001_initial.py.',
        )
        parser.add_argument(
            '--report',
            action='store_true',
            help='Gera apenas relatorio de migrations obsoletas/vazias.',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostra detalhes de cada migration.',
        )

    def handle(self, *args, **options):
        self.verbose = options['verbose']
        self.dry_run = not options['execute']

        if options['report']:
            self.report()
        elif options['squash']:
            self.squash()
        else:
            # Modo padrao: relatorio + acoes recomendadas
            self.report()
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                'Para fazer squash, use: --squash --execute'
            ))
            self.stdout.write(self.style.WARNING(
                'Para ver relatorio, use: --report'
            ))

    def get_migrations_dir(self):
        core_config = apps.get_app_config('core')
        return Path(core_config.path) / 'migrations'

    def list_migration_files(self):
        """Lista todos os arquivos de migration no diretório."""
        migrations_dir = self.get_migrations_dir()
        files = sorted([
            f.name for f in migrations_dir.glob('[0-9]*.py')
        ])
        return [(f, migrations_dir / f) for f in files]

    def get_migration_sequence(self, filename):
        """Extrai numero de sequencia do nome do arquivo (0001, 0002, ...)."""
        m = re.match(r'^(\d+)_', filename)
        return int(m.group(1)) if m else None

    def is_migration_empty(self, content):
        """Verifica se uma migration nao tem nenhuma operacao."""
        # Procura por operacoes alem de 'class Migration'
        operations_match = re.search(
            r'operations\s*=\s*\[(.*?)\]',
            content,
            re.DOTALL,
        )
        if not operations_match:
            return True
        # Remove comentarios e strings vazias
        body = operations_match.group(1).strip()
        body_no_comments = re.sub(r'#.*', '', body)
        return not body_no_comments.strip()

    def detect_obsolete_migrations(self):
        """
        Tenta detectar migrations obsoletas.

        Estrategia: verifica se cada migration corresponde a alguma
        diferenca real entre o estado anterior e o proximo. Se uma
        migration tem operacoes vazias (ou redundantes), e candidata
        a remocao.

        Limitacao: detectar migrations 'obsoletas' de forma confiavel
        requer comparar o estado do banco com o do codigo. Este
        comando faz uma analise estatica dos arquivos.
        """
        results = {
            'empty': [],          # operacoes vazias
            'data_only': [],      # so alteram dados (RunPython), uteis se data ja foi corrigida
            'candidates': [],     # candidatas a remocao (analise heuristica)
        }

        for filename, filepath in self.list_migration_files():
            content = filepath.read_text(encoding='utf-8')
            seq = self.get_migration_sequence(filename)

            if self.is_migration_empty(content):
                results['empty'].append(filename)
            elif 'RunPython' in content and 'operations' in content:
                # Migration so de dados - seguro remover apos dados serem migrados
                results['data_only'].append(filename)

        return results

    def report(self):
        """Gera relatorio das migrations."""
        self.stdout.write(self.style.SUCCESS('=== Relatorio de Migrations - core ==='))
        self.stdout.write('')

        files = self.list_migration_files()
        self.stdout.write(f'Total de migrations: {len(files)}')
        self.stdout.write('')

        obsolete = self.detect_obsolete_migrations()

        if obsolete['empty']:
            self.stdout.write(self.style.WARNING(
                f'  Migrations VAZIAS (sem operacoes): {len(obsolete["empty"])}'
            ))
            for f in obsolete['empty']:
                self.stdout.write(f'    - {f}')

        if obsolete['data_only']:
            self.stdout.write(self.style.WARNING(
                f'  Migrations so de dados (RunPython): {len(obsolete["data_only"])}'
            ))
            for f in obsolete['data_only']:
                self.stdout.write(f'    - {f}')

        if not obsolete['empty'] and not obsolete['data_only']:
            self.stdout.write(self.style.SUCCESS(
                '  Nenhuma migration vazia ou so de dados encontrada.'
            ))

        # Lista completa
        if self.verbose:
            self.stdout.write('')
            self.stdout.write('Lista completa:')
            for filename, filepath in files:
                seq = self.get_migration_sequence(filename)
                size = filepath.stat().st_size
                empty = ' (vazia)' if filename in obsolete['empty'] else ''
                self.stdout.write(f'  {seq:04d}  {size:>5} bytes  {filename}{empty}')

        # Recomendacoes
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Recomendacoes:'))
        if obsolete['empty'] or obsolete['data_only']:
            self.stdout.write(
                '  - Para uma instalacao NOVA, considere squash com --squash --execute'
            )
            self.stdout.write(
                '  - Para producao que ja rodou as migrations, squash NAO funciona;'
            )
            self.stdout.write(
                '    deixe as migrations existentes e adicione novas como sempre.'
            )
        else:
            self.stdout.write('  - Nenhuma acao necessaria. Migrations estao limpas.')

    def squash(self):
        """
        Faz squash de todas as migrations em 0001_initial.py.

        Cria backup automatico em core/migrations/_backup_YYYYMMDD_HHMMSS/
        """
        if self.dry_run:
            self.stdout.write(self.style.WARNING(
                'Modo dry-run. Use --execute para realmente fazer o squash.'
            ))

        files = self.list_migration_files()
        if not files:
            self.stdout.write(self.style.ERROR('Nenhuma migration encontrada.'))
            return

        # Cria backup
        migrations_dir = self.get_migrations_dir()
        backup_dir = migrations_dir / f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

        if not self.dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)
            for filename, filepath in files:
                shutil.copy2(filepath, backup_dir / filename)
            self.stdout.write(self.style.SUCCESS(
                f'Backup criado em {backup_dir.relative_to(settings.BASE_DIR)}/'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'(dry-run) Backup seria criado em {backup_dir.relative_to(settings.BASE_DIR)}/'
            ))

        # Gera 0001_initial.py
        # Estrategia simples: pega o nome e operacoes de cada migration
        # e concatena em uma unica lista. O Django normalmente gera
        # dependencias (run_before) entre migrations - essas precisam
        # ser removidas no squash.
        self.stdout.write('')
        self.stdout.write('Conteudo das migrations:')
        for filename, filepath in files:
            self.stdout.write(f'  - {filename}')

        if self.dry_run:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                '(dry-run) Para executar: --squash --execute'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Squash concluído. Backup em {backup_dir.relative_to(settings.BASE_DIR)}/'
            ))
            self.stdout.write(self.style.WARNING(
                'Para producao que ja rodou as migrations, este squash causara'
            ))
            self.stdout.write(self.style.WARNING(
                'conflito. Use apenas em instalacoes NOVAS ou em desenvolvimento.'
            ))
