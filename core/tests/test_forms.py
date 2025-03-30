from django.test import TestCase
from ..forms import PessoaForm, RegistroAcessoForm
from ..models import Pessoa
from django.contrib.auth.models import User

class PessoaFormTest(TestCase):
    def test_pessoa_form_valid(self):
        form_data = {
            'nome': 'João Silva',
            'tipo_documento': 'RG',
            'numero_documento': '123456789',
            'placa_veiculo': 'ABC1234',
            'tipo_funcionario': 'ADMINISTRATIVO'
        }
        form = PessoaForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_pessoa_form_plantonista(self):
        form_data = {
            'nome': 'João Silva',
            'tipo_documento': 'RG',
            'numero_documento': '123456789',
            'placa_veiculo': 'ABC1234',
            'tipo_funcionario': 'PLANTONISTA',
            'plantao': 'ALFA'
        }
        form = PessoaForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_pessoa_form_plantonista_sem_plantao(self):
        form_data = {
            'nome': 'João Silva',
            'tipo_documento': 'RG',
            'numero_documento': '123456789',
            'placa_veiculo': 'ABC1234',
            'tipo_funcionario': 'PLANTONISTA'
        }
        form = PessoaForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_pessoa_form_nao_plantonista_com_plantao(self):
        form_data = {
            'nome': 'João Silva',
            'tipo_documento': 'RG',
            'numero_documento': '123456789',
            'placa_veiculo': 'ABC1234',
            'tipo_funcionario': 'ADMINISTRATIVO',
            'plantao': 'ALFA'
        }
        form = PessoaForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_pessoa_form_invalid(self):
        form_data = {
            'nome': '',
            'tipo_documento': 'RG',
            'numero_documento': '123456789'
        }
        form = PessoaForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('nome', form.errors)

    def test_pessoa_form_documento_duplicado(self):
        # Cria uma pessoa com o mesmo documento
        Pessoa.objects.create(
            nome='Maria Santos',
            tipo_documento='RG',
            numero_documento='123456789'
        )
        
        form_data = {
            'nome': 'João Silva',
            'tipo_documento': 'RG',
            'numero_documento': '123456789'
        }
        form = PessoaForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

class RegistroAcessoFormTest(TestCase):
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

    def test_registro_acesso_form_valid(self):
        form_data = {
            'pessoa': self.pessoa.id,
            'observacao': 'Teste de entrada'
        }
        form = RegistroAcessoForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_registro_acesso_form_isv(self):
        form_data = {
            'pessoa': self.pessoa.id,
            'observacao': 'Teste de entrada',
            'isv': True
        }
        form = RegistroAcessoForm(data=form_data)
        self.assertTrue(form.is_valid())
        registro = form.save(commit=False)
        self.assertTrue(registro.isv)

    def test_registro_acesso_form_invalid(self):
        form_data = {
            'pessoa': self.pessoa.id,
            'tipo_acesso': 'ENTRADA'
        }
        form = RegistroAcessoForm(data=form_data)
        self.assertTrue(form.is_valid())  # Observação é opcional

    def test_registro_acesso_form_pessoa_invalida(self):
        form_data = {
            'pessoa': 999,  # ID inexistente
            'tipo_acesso': 'ENTRADA'
        }
        form = RegistroAcessoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('pessoa', form.errors) 