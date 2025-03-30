from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from ..models import Pessoa, RegistroAcesso, LogAuditoria

class PessoaModelTest(TestCase):
    def setUp(self):
        self.pessoa = Pessoa.objects.create(
            nome='João Silva',
            tipo_documento='RG',
            numero_documento='123456789',
            placa_veiculo='ABC1234'
        )

    def test_pessoa_str(self):
        self.assertEqual(str(self.pessoa), 'João Silva - RG: 123456789')

    def test_pessoa_documento_unico(self):
        with self.assertRaises(Exception):
            Pessoa.objects.create(
                nome='Maria Santos',
                tipo_documento='RG',
                numero_documento='123456789',
                placa_veiculo='XYZ5678'
            )

class RegistroAcessoModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.pessoa = Pessoa.objects.create(
            nome='João Silva',
            tipo_documento='RG',
            numero_documento='123456789',
            tipo_funcionario='ADMINISTRATIVO'
        )
        self.registro = RegistroAcesso.objects.create(
            pessoa=self.pessoa,
            operador=self.user,
            observacao='Teste de entrada',
            tipo_acesso='ENTRADA'
        )

    def test_registro_acesso_str(self):
        expected = f"{self.pessoa.nome} - Entrada - {self.registro.data_hora}"
        self.assertEqual(str(self.registro), expected)

    def test_registro_acesso_isv(self):
        self.assertFalse(self.registro.isv)
        self.registro.isv = True
        self.registro.save()
        self.assertTrue(self.registro.isv)

    def test_registro_acesso_tipo(self):
        self.assertEqual(self.registro.tipo_acesso, 'ENTRADA')
        self.assertEqual(self.registro.get_tipo_acesso_display(), 'Entrada')

    def test_registro_acesso_saida_pendente(self):
        self.assertFalse(self.registro.saida_pendente)
        self.registro.saida_pendente = True
        self.registro.save()
        self.assertTrue(self.registro.saida_pendente)

class LogAuditoriaModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.log = LogAuditoria.objects.create(
            usuario=self.user,
            tipo_acao='CRIACAO',
            modelo='Pessoa',
            objeto_id=1,
            detalhes='Teste de criação'
        )

    def test_log_auditoria_str(self):
        expected = f"CRIACAO - Pessoa - {self.log.data_hora}"
        self.assertEqual(str(self.log), expected)

    def test_log_auditoria_tipo_acao(self):
        self.assertEqual(self.log.tipo_acao, 'CRIACAO')

    def test_log_auditoria_modelo(self):
        self.assertEqual(self.log.modelo, 'Pessoa') 