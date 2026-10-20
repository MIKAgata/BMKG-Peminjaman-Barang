from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import CustomUser
from inventory.models import Category, Location, Item
from loans.models import LoanRequest, LoanItem, LoanHandover, LoanHandoverItem, ReturnRecord, ReturnItem


class LoansTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = CustomUser.objects.create_user(
            username='admin_loan',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )
        self.pegawai1 = CustomUser.objects.create_user(
            username='pegawai_andi',
            password='Password123!',
            role=CustomUser.Role.EMPLOYEE,
            first_name='Andi',
            department='Klimatologi'
        )
        self.pegawai2 = CustomUser.objects.create_user(
            username='pegawai_budi',
            password='Password123!',
            role=CustomUser.Role.EMPLOYEE,
            first_name='Budi',
            department='Geofisika'
        )

        self.cat = Category.objects.create(name='Peralatan Liputan')
        self.loc = Location.objects.create(name='Ruang BMN')

        self.kamera = Item.objects.create(
            code='CAM-101',
            name='Kamera Mirrorless',
            category=self.cat,
            item_type=Item.ItemType.LOANABLE,
            unit='Unit',
            stock_available=4,
            minimum_stock=1
        )

        self.kertas = Item.objects.create(
            code='KRT-101',
            name='Kertas HVS',
            category=self.cat,
            item_type=Item.ItemType.CONSUMABLE,
            unit='Rim',
            stock_available=20
        )

    def test_employee_apply_loan_does_not_deduct_stock(self):
        self.client.login(username='pegawai_andi', password='Password123!')
        start_date = timezone.now().date()
        due_date = start_date + timezone.timedelta(days=2)

        data = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'due_date': due_date.strftime('%Y-%m-%d'),
            'purpose': 'Dokumentasi kunjungan kerja BMKG',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-item': self.kamera.id,
            'items-0-quantity_requested': '2',
            'items-0-notes': 'Perlu baterai cadangan',
        }
        response = self.client.post(reverse('loans:loan_apply'), data)
        self.assertEqual(response.status_code, 302)

        loan = LoanRequest.objects.get(borrower=self.pegawai1)
        self.assertEqual(loan.status, LoanRequest.Status.PENDING)

        # Stock must NOT be deducted at application stage!
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 4)
        self.assertEqual(self.kamera.stock_loaned, 0)

    def test_admin_approval_does_not_deduct_stock(self):
        loan = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            purpose='Riset',
            status=LoanRequest.Status.PENDING
        )
        LoanItem.objects.create(loan=loan, item=self.kamera, quantity_requested=2)

        self.client.login(username='admin_loan', password='Password123!')
        response = self.client.post(reverse('loans:loan_review', args=[loan.pk]), {
            'action': 'APPROVE',
            'rejection_reason': '',
        })
        self.assertEqual(response.status_code, 302)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanRequest.Status.APPROVED)

        # Approval without physical handover does NOT deduct stock!
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 4)
        self.assertEqual(self.kamera.stock_loaned, 0)

    def test_handover_deducts_available_stock_and_activates_loan(self):
        loan = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            purpose='Tugas Lapangan',
            status=LoanRequest.Status.APPROVED
        )
        l_item = LoanItem.objects.create(loan=loan, item=self.kamera, quantity_requested=2)

        self.client.login(username='admin_loan', password='Password123!')
        response = self.client.post(reverse('loans:handover_create', args=[loan.pk]), {
            f'qty_{l_item.id}': '2',
            f'cond_{l_item.id}': 'Baik / Layak Pakai',
            'notes': 'Diserahkan dengan tas kamera',
        })
        self.assertEqual(response.status_code, 302)

        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanRequest.Status.ACTIVE)

        # Stock IS deducted now!
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 2)
        self.assertEqual(self.kamera.stock_loaned, 2)
        self.assertTrue(LoanHandover.objects.filter(loan=loan).exists())

    def test_partial_and_full_return_workflow(self):
        loan = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            purpose='Pengukuran',
            status=LoanRequest.Status.ACTIVE
        )
        l_item = LoanItem.objects.create(
            loan=loan,
            item=self.kamera,
            quantity_requested=3,
            quantity_handed_over=3
        )
        # Simulate inventory loaned
        self.kamera.stock_available = 1
        self.kamera.stock_loaned = 3
        self.kamera.save()

        self.client.login(username='admin_loan', password='Password123!')

        # 1. Partial Return: 1 Usable, 1 Damaged
        response = self.client.post(reverse('loans:return_create', args=[loan.pk]), {
            f'usable_{l_item.id}': '1',
            f'damaged_{l_item.id}': '1',
            f'lost_{l_item.id}': '0',
            f'notes_{l_item.id}': 'Satu unit lensa pecah',
            'notes': 'Pengembalian tahap satu',
        })
        self.assertEqual(response.status_code, 302)

        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanRequest.Status.PARTIALLY_RETURNED)

        self.kamera.refresh_from_db()
        # Available stock only increased by usable unit (1 + 1 = 2)
        self.assertEqual(self.kamera.stock_available, 2)
        # Damaged stock increased to 1
        self.assertEqual(self.kamera.stock_damaged, 1)
        # Loaned stock decreased to 1
        self.assertEqual(self.kamera.stock_loaned, 1)

        # 2. Complete Remaining Return: 1 Usable
        response2 = self.client.post(reverse('loans:return_create', args=[loan.pk]), {
            f'usable_{l_item.id}': '1',
            f'damaged_{l_item.id}': '0',
            f'lost_{l_item.id}': '0',
            f'notes_{l_item.id}': 'Kondisi baik',
            'notes': 'Pelunasan sisa pinjaman',
        })
        self.assertEqual(response2.status_code, 302)

        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanRequest.Status.COMPLETED)

        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 3)
        self.assertEqual(self.kamera.stock_loaned, 0)

    def test_over_return_rejected(self):
        loan = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            purpose='Uji kelebihan return',
            status=LoanRequest.Status.ACTIVE
        )
        l_item = LoanItem.objects.create(
            loan=loan,
            item=self.kamera,
            quantity_requested=2,
            quantity_handed_over=2
        )
        self.kamera.stock_available = 2
        self.kamera.stock_loaned = 2
        self.kamera.save()

        self.client.login(username='admin_loan', password='Password123!')
        # Try to return 5 units when only 2 were handed over
        response = self.client.post(reverse('loans:return_create', args=[loan.pk]), {
            f'usable_{l_item.id}': '5',
            f'damaged_{l_item.id}': '0',
            f'lost_{l_item.id}': '0',
        })
        self.assertEqual(response.status_code, 302)
        loan.refresh_from_db()
        # Status should still be ACTIVE, not returned!
        self.assertEqual(loan.status, LoanRequest.Status.ACTIVE)

    def test_user_cannot_view_another_users_loan(self):
        loan1 = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            purpose='Privat Pegawai 1',
            status=LoanRequest.Status.PENDING
        )

        # Login as Pegawai 2 and try to view Pegawai 1's loan
        self.client.login(username='pegawai_budi', password='Password123!')
        response = self.client.get(reverse('loans:loan_detail', args=[loan1.pk]))
        self.assertEqual(response.status_code, 403)
