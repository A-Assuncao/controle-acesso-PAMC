from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Pessoa, RegistroAcesso
from datetime import datetime, timedelta

class ViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.pessoa = Pessoa.objects.create(
            nome='João Silva',
            tipo_documento='RG',
            numero_documento='123456789'
        )

    def test_home_view_anonimo(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/login/?next=/')

    def test_home_view_autenticado(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/home.html')

    def test_pessoa_list_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('pessoa_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/pessoa_list.html')
        self.assertIn('pessoas', response.context)

    def test_pessoa_list_view_paginacao(self):
        self.client.login(username='testuser', password='testpass123')
        # Criar mais de 10 pessoas para testar paginação
        for i in range(15):
            Pessoa.objects.create(
                nome=f'Pessoa {i}',
                tipo_documento='RG',
                numero_documento=f'98765432{i}',
                placa_veiculo=f'ABC{i}123'
            )
        response = self.client.get(reverse('pessoa_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['pessoas']), 10)

    def test_pessoa_list_view_busca(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('pessoa_list'), {'q': 'João'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('pessoas', response.context)
        self.assertEqual(len(response.context['pessoas']), 1)

    def test_pessoa_create_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('pessoa_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/pessoa_form.html')

    def test_pessoa_create_view_post(self):
        self.client.login(username='testuser', password='testpass123')
        data = {
            'nome': 'Maria Santos',
            'tipo_documento': 'RG',
            'numero_documento': '987654321',
            'placa_veiculo': 'XYZ5678',
            'tipo_funcionario': 'ADMINISTRATIVO'
        }
        response = self.client.post(reverse('pessoa_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('pessoa_list'))
        self.assertTrue(Pessoa.objects.filter(numero_documento='987654321').exists())

    def test_pessoa_create_view_post_plantonista(self):
        self.client.login(username='testuser', password='testpass123')
        data = {
            'nome': 'João Plantonista',
            'tipo_documento': 'RG',
            'numero_documento': '987654322',
            'placa_veiculo': 'XYZ5679',
            'tipo_funcionario': 'PLANTONISTA',
            'plantao': 'ALFA'
        }
        response = self.client.post(reverse('pessoa_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('pessoa_list'))
        self.assertTrue(Pessoa.objects.filter(numero_documento='987654322').exists())

    def test_registro_acesso_create_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('registro_acesso_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/registro_acesso_form.html')

    def test_registro_acesso_create_view_post(self):
        self.client.login(username='testuser', password='testpass123')
        data = {
            'pessoa': self.pessoa.id,
            'observacao': 'Teste de entrada'
        }
        response = self.client.post(reverse('registro_acesso_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))
        self.assertTrue(RegistroAcesso.objects.filter(pessoa=self.pessoa).exists())

    def test_registro_acesso_create_view_post_isv(self):
        self.client.login(username='testuser', password='testpass123')
        data = {
            'pessoa': self.pessoa.id,
            'observacao': 'Teste de entrada',
            'isv': True
        }
        response = self.client.post(reverse('registro_acesso_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))
        registro = RegistroAcesso.objects.get(pessoa=self.pessoa)
        self.assertTrue(registro.isv)

    def test_registro_acesso_list_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('registro_acesso_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/registro_acesso_list.html')
        self.assertIn('registros', response.context)

    def test_registro_acesso_list_view_filtro_data(self):
        self.client.login(username='testuser', password='testpass123')
        hoje = datetime.now().date()
        data_inicio = hoje - timedelta(days=7)
        data_fim = hoje
        
        response = self.client.get(
            reverse('registro_acesso_list'),
            {'data_inicio': data_inicio, 'data_fim': data_fim}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['data_inicio'], str(data_inicio))
        self.assertEqual(response.context['data_fim'], str(data_fim))

    def test_buscar_pessoa_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('buscar_pessoa'),
            {'q': 'João'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.json())
        self.assertTrue(len(response.json()['data']) > 0)

    def test_buscar_pessoa_view_sem_resultados(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('buscar_pessoa'),
            {'q': 'NaoExiste'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.json())
        self.assertEqual(len(response.json()['data']), 0)

    def test_buscar_pessoa_view_sem_query(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('buscar_pessoa'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.json())
        self.assertEqual(len(response.json()['data']), 0)

    def test_gerar_relatorio_view(self):
        self.client.login(username='testuser', password='testpass123')
        hoje = datetime.now().date()
        data_inicio = hoje - timedelta(days=7)
        data_fim = hoje
        
        response = self.client.get(
            reverse('gerar_relatorio'),
            {
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'formato': 'pdf'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('registro_acesso_list'))

    def test_gerar_relatorio_view_excel(self):
        self.client.login(username='testuser', password='testpass123')
        hoje = datetime.now().date()
        data_inicio = hoje - timedelta(days=7)
        data_fim = hoje
        
        response = self.client.get(
            reverse('gerar_relatorio'),
            {
                'data_inicio': data_inicio,
                'data_fim': data_fim,
                'formato': 'excel'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('registro_acesso_list')) 