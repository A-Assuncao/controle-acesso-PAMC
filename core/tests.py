from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import PerfilUsuario
from core.views.user_views import COURSE_STAFF_MANAGED_GROUP


@override_settings(COURSE_STAFF_TOGGLE_ENABLED=True)
class CourseStaffToggleTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser('admin', password='test-password')
        PerfilUsuario.objects.create(usuario=self.superuser, tipo_usuario='ADMIN')

        self.existing_staff = User.objects.create_user(
            'staff_original', password='test-password', is_staff=True
        )
        PerfilUsuario.objects.create(usuario=self.existing_staff, tipo_usuario='STAFF')

        self.operator = User.objects.create_user('operador', password='test-password')
        PerfilUsuario.objects.create(usuario=self.operator, tipo_usuario='OPERADOR')

        self.viewer = User.objects.create_user('visualizador', password='test-password')
        PerfilUsuario.objects.create(usuario=self.viewer, tipo_usuario='VISUALIZACAO')

    def test_superuser_can_activate_and_restore_original_permissions(self):
        self.client.force_login(self.superuser)
        url = reverse('toggle_course_staff')

        response = self.client.post(url)
        self.assertRedirects(response, reverse('user_list'))

        for user in (self.existing_staff, self.operator, self.viewer):
            user.refresh_from_db()
            user.perfil.refresh_from_db()
            self.assertTrue(user.is_staff)
            self.assertEqual(user.perfil.tipo_usuario, 'STAFF')
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_superuser)
        self.assertEqual(self.superuser.perfil.tipo_usuario, 'ADMIN')

        response = self.client.post(url)
        self.assertRedirects(response, reverse('user_list'))

        self.existing_staff.refresh_from_db()
        self.operator.refresh_from_db()
        self.viewer.refresh_from_db()
        self.assertTrue(self.existing_staff.is_staff)
        self.assertEqual(self.existing_staff.perfil.tipo_usuario, 'STAFF')
        self.assertFalse(self.operator.is_staff)
        self.assertEqual(self.operator.perfil.tipo_usuario, 'OPERADOR')
        self.assertFalse(self.viewer.is_staff)
        self.assertEqual(self.viewer.perfil.tipo_usuario, 'VISUALIZACAO')
        self.assertFalse(Group.objects.filter(name=COURSE_STAFF_MANAGED_GROUP).exists())

    def test_locked_user_query_does_not_join_nullable_profile(self):
        """Evita FOR UPDATE em LEFT JOIN, que o PostgreSQL não aceita."""
        query = (
            User.objects.select_for_update()
            .filter(is_superuser=False)
        )

        self.assertNotIn(' JOIN ', str(query.query).upper())

    def test_non_superuser_cannot_toggle_mode(self):
        self.client.force_login(self.existing_staff)

        response = self.client.post(reverse('toggle_course_staff'))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Group.objects.filter(name=COURSE_STAFF_MANAGED_GROUP).exists())

    def test_button_is_only_visible_to_superuser(self):
        self.client.force_login(self.existing_staff)
        response = self.client.get(reverse('user_list'))
        self.assertNotContains(response, 'Ativar Staff para o curso')

        self.client.force_login(self.superuser)
        response = self.client.get(reverse('user_list'))
        self.assertContains(response, 'Ativar Staff para o curso')

    @override_settings(COURSE_STAFF_TOGGLE_ENABLED=False)
    def test_feature_flag_hides_and_blocks_feature(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse('user_list'))
        self.assertNotContains(response, 'Ativar Staff para o curso')
        response = self.client.post(reverse('toggle_course_staff'))
        self.assertEqual(response.status_code, 404)


class AdminBannerVisibilityTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            'staff_sem_admin', password='test-password', is_staff=True
        )
        PerfilUsuario.objects.create(usuario=self.staff, tipo_usuario='STAFF')
        self.superuser = User.objects.create_superuser(
            'admin_banner', password='test-password'
        )
        PerfilUsuario.objects.create(usuario=self.superuser, tipo_usuario='ADMIN')

    def test_admin_banner_is_hidden_from_staff(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Administração do Sistema')
        self.assertNotContains(response, 'Abrir Painel Admin')

    def test_admin_banner_is_visible_to_superuser(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Administração do Sistema')
        self.assertContains(response, 'Abrir Painel Admin')
