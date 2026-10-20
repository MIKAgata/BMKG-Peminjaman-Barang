from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser
from inventory.models import Category, Item
from loans.models import LoanRequest, LoanItem, LoanHandover, LoanHandoverItem, ReturnRecord, ReturnItem
from consumables.models import ConsumableHandover, ConsumableHandoverItem
from audit.models import InstitutionSetting


class ReportsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = CustomUser.objects.create_user(
            username='admin_rep',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )
        self.pegawai = CustomUser.objects.create_user(
            username='pegawai_rep',
            password='Password123!',
            role=CustomUser.Role.EMPLOYEE,
            first_name='Citra',
            department='Geofisika'
        )

        self.setting = InstitutionSetting.objects.create(
            institution_name='BMKG Pusat Jakarta',
            head_officer_name='Dr. Sutopo',
            head_officer_nip='197501012000031001'
        )

        self.cat = Category.objects.create(name='Peralatan')
        self.laptop = Item.objects.create(
            code='LPT-001',
            name='Laptop Dell XPS',
            category=self.cat,
            item_type=Item.ItemType.LOANABLE,
            unit='Unit',
            stock_available=5,
            minimum_stock=10
        )

        self.kertas = Item.objects.create(
            code='KRT-002',
            name='Kertas A4',
            category=self.cat,
            item_type=Item.ItemType.CONSUMABLE,
            unit='Rim',
            stock_available=40
        )

        self.loan = LoanRequest.objects.create(
            borrower=self.pegawai,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=1),
            purpose='Analisis Gempa',
            status=LoanRequest.Status.ACTIVE
        )
        self.l_item = LoanItem.objects.create(
            loan=self.loan,
            item=self.laptop,
            quantity_requested=1,
            quantity_handed_over=1
        )
        self.handover = LoanHandover.objects.create(
            loan=self.loan,
            handed_over_by=self.admin,
            recipient=self.pegawai
        )
        LoanHandoverItem.objects.create(
            handover=self.handover,
            loan_item=self.l_item,
            quantity=1
        )

    def test_admin_dashboard_stats(self):
        self.client.login(username='admin_rep', password='Password123!')
        response = self.client.get(reverse('reports:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Laptop Dell XPS")
        self.assertEqual(response.context['stats']['total_items'], 2)
        self.assertEqual(response.context['stats']['active_loans'], 1)

    def test_employee_dashboard(self):
        self.client.login(username='pegawai_rep', password='Password123!')
        response = self.client.get(reverse('reports:employee_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.loan.loan_number)

    def test_export_loans_csv(self):
        self.client.login(username='admin_rep', password='Password123!')
        response = self.client.get(reverse('reports:report_loans') + '?export=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn(self.loan.loan_number.encode(), response.content)

    def test_export_loans_excel(self):
        self.client.login(username='admin_rep', password='Password123!')
        response = self.client.get(reverse('reports:report_loans') + '?export=excel')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_export_loans_pdf(self):
        self.client.login(username='admin_rep', password='Password123!')
        response = self.client.get(reverse('reports:report_loans') + '?export=pdf')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_printable_slips(self):
        self.client.login(username='admin_rep', password='Password123!')
        # 1. Loan slip
        res1 = self.client.get(reverse('reports:print_loan_slip', args=[self.loan.pk]))
        self.assertEqual(res1.status_code, 200)
        self.assertContains(res1, "SURAT PERMOHONAN & BUKTI PEMINJAMAN BARANG")

        # 2. Handover slip
        res2 = self.client.get(reverse('reports:print_handover_slip', args=[self.handover.pk]))
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, "BERITA ACARA SERAH TERIMA FISIK BARANG PINJAMAN")
