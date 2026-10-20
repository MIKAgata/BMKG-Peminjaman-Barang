from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from audit.models import AuditLog, InstitutionSetting
from audit.utils import log_action


class AuditTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = CustomUser.objects.create_user(
            username='admin_audit',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )
        self.pegawai = CustomUser.objects.create_user(
            username='pegawai_audit',
            password='Password123!',
            role=CustomUser.Role.EMPLOYEE
        )

    def test_log_action_utility(self):
        log_action(
            user=self.admin,
            action=AuditLog.Action.CREATE,
            entity_type='TestEntity',
            entity_id='100',
            details={'test_key': 'test_val'}
        )
        log = AuditLog.objects.filter(entity_type='TestEntity', entity_id='100').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, self.admin)
        self.assertEqual(log.details['test_key'], 'test_val')

    def test_admin_can_view_audit_logs(self):
        self.client.login(username='admin_audit', password='Password123!')
        response = self.client.get(reverse('audit:log_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Audit Log Aktivitas Sistem")

    def test_employee_cannot_view_audit_logs(self):
        self.client.login(username='pegawai_audit', password='Password123!')
        response = self.client.get(reverse('audit:log_list'))
        self.assertEqual(response.status_code, 403)

    def test_institution_setting_update(self):
        self.client.login(username='admin_audit', password='Password123!')
        response = self.client.post(reverse('audit:setting_view'), {
            'institution_name': 'BMKG Stasiun Klimatologi',
            'unit_name': 'Sub Bagian Tata Usaha',
            'address': 'Jl. Kemayoran No. 1',
            'phone': '021-123456',
            'email': 'staklim@bmkg.go.id',
            'head_officer_name': 'Kepala Stasiun',
            'head_officer_nip': '198001012005011001',
            'warehouse_officer_name': 'Bambang',
            'warehouse_officer_nip': '198501012010011002',
        })
        self.assertEqual(response.status_code, 302)
        setting = InstitutionSetting.objects.first()
        self.assertEqual(setting.institution_name, 'BMKG Stasiun Klimatologi')
