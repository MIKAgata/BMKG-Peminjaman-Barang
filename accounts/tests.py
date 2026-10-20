from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from audit.models import AuditLog


class AccountsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = CustomUser.objects.create_user(
            username='admin_test',
            password='Password123!',
            first_name='Admin',
            last_name='BMKG',
            role=CustomUser.Role.ADMIN,
            employee_number='NIP001',
            department='Pengelola BMN'
        )
        self.employee_user = CustomUser.objects.create_user(
            username='pegawai_test',
            password='Password123!',
            first_name='Budi',
            last_name='Santoso',
            role=CustomUser.Role.EMPLOYEE,
            employee_number='NIP002',
            department='Operasional Meteorologi'
        )

    def test_custom_user_roles_and_properties(self):
        self.assertTrue(self.admin_user.is_admin_role)
        self.assertFalse(self.admin_user.is_employee_role)
        self.assertFalse(self.employee_user.is_admin_role)
        self.assertTrue(self.employee_user.is_employee_role)
        self.assertEqual(self.admin_user.display_name, "Admin BMKG")

    def test_login_successful(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'pegawai_test',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        # Check audit log recorded login
        self.assertTrue(AuditLog.objects.filter(user=self.employee_user, action=AuditLog.Action.LOGIN).exists())

    def test_login_invalid_password(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'pegawai_test',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tidak valid")

    def test_inactive_user_cannot_login(self):
        self.employee_user.is_active = False
        self.employee_user.save()
        response = self.client.post(reverse('accounts:login'), {
            'username': 'pegawai_test',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dinonaktifkan")

    def test_employee_cannot_access_user_management(self):
        self.client.login(username='pegawai_test', password='Password123!')
        response = self.client.get(reverse('accounts:user_list'))
        # PermissionDenied raises 403
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_user_management(self):
        self.client.login(username='admin_test', password='Password123!')
        response = self.client.get(reverse('accounts:user_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manajemen Pengguna & Pegawai")

    def test_admin_create_new_user(self):
        self.client.login(username='admin_test', password='Password123!')
        response = self.client.post(reverse('accounts:user_create'), {
            'username': 'user_baru',
            'employee_number': 'NIP003',
            'first_name': 'Siti',
            'last_name': 'Aminah',
            'email': 'siti@bmkg.go.id',
            'role': CustomUser.Role.EMPLOYEE,
            'department': 'Geofisika',
            'phone_number': '081234567890',
            'password': 'PasswordBaru123!',
            'confirm_password': 'PasswordBaru123!',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(username='user_baru').exists())
        self.assertTrue(AuditLog.objects.filter(entity_type='CustomUser', action=AuditLog.Action.CREATE).exists())

    def test_admin_toggle_active_status(self):
        self.client.login(username='admin_test', password='Password123!')
        response = self.client.get(reverse('accounts:user_toggle_active', args=[self.employee_user.pk]))
        self.assertEqual(response.status_code, 302)
        self.employee_user.refresh_from_db()
        self.assertFalse(self.employee_user.is_active)
