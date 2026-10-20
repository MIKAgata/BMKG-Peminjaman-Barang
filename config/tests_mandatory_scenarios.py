from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError

from accounts.models import CustomUser
from inventory.models import Category, Location, Item, StockMovement
from inventory.services import InventoryService
from loans.models import LoanRequest, LoanItem, LoanHandover, LoanHandoverItem, ReturnRecord, ReturnItem
from consumables.models import ConsumableHandover, ConsumableHandoverItem
from audit.models import AuditLog, InstitutionSetting


class MandatoryScenariosTestCase(TestCase):
    """
    Rangkaian Pengujian Wajib untuk memverifikasi 20 Kriteria Penerimaan PRD:
    1. Admin dapat login dan mengelola barang.
    2. Pegawai dapat login dan melihat katalog.
    3. Pegawai tidak dapat mengakses halaman admin tanpa izin.
    4. Pegawai tidak dapat melihat transaksi pegawai lain.
    5. Barang CONSUMABLE tidak dapat dipinjam.
    6. Barang LOANABLE tidak dapat diproses melalui penyerahan habis pakai.
    7. Pengajuan peminjaman tidak mengurangi stok sebelum serah terima.
    8. Persetujuan tanpa serah terima tidak dianggap sebagai barang keluar.
    9. Stok berkurang ketika barang benar-benar diserahkan.
    10. Pengembalian sebagian memperbarui saldo dengan benar.
    11. Pengembalian melebihi jumlah yang dipinjam ditolak.
    12. Barang rusak tidak langsung menjadi stok tersedia.
    13. Penyerahan habis pakai mengurangi stok satu kali.
    14. Stok tidak boleh negatif.
    15. Pemrosesan ganda tidak menggandakan perubahan stok.
    16. Pembatalan transaksi memiliki jejak audit.
    17. Nomor transaksi tidak duplikat.
    18. Laporan sesuai dengan data transaksi.
    19. Pengguna tidak dapat memalsukan identitas peminjam melalui request.
    20. Dokumen transaksi dapat dibuat dari data yang benar.
    """

    def setUp(self):
        self.client = Client()
        self.admin = CustomUser.objects.create_user(
            username='admin_bmn',
            password='Password123!',
            role=CustomUser.Role.ADMIN,
            first_name='Admin',
            last_name='Gudang',
            employee_number='198001012005011001'
        )
        self.pegawai1 = CustomUser.objects.create_user(
            username='pegawai_andi',
            password='Password123!',
            role=CustomUser.Role.EMPLOYEE,
            first_name='Andi',
            employee_number='199001012015011002',
            department='Seksi Observasi'
        )
        self.pegawai2 = CustomUser.objects.create_user(
            username='pegawai_budi',
            password='Password123!',
            role=CustomUser.Role.EMPLOYEE,
            first_name='Budi',
            employee_number='199202022016021003',
            department='Seksi Data & Analisis'
        )

        self.cat_elektronik = Category.objects.create(name='Peralatan Elektronik')
        self.cat_atk = Category.objects.create(name='ATK & Perlengkapan')
        self.loc_gudang = Location.objects.create(name='Gudang Utama BMN')

        self.kamera = Item.objects.create(
            code='CAM-SONY-01',
            name='Kamera Sony A7 IV',
            category=self.cat_elektronik,
            item_type=Item.ItemType.LOANABLE,
            unit='Unit',
            location=self.loc_gudang,
            stock_available=5,
            minimum_stock=1
        )

        self.kertas = Item.objects.create(
            code='KRT-A4-01',
            name='Kertas HVS A4 80gr',
            category=self.cat_atk,
            item_type=Item.ItemType.CONSUMABLE,
            unit='Rim',
            location=self.loc_gudang,
            stock_available=40,
            minimum_stock=5
        )

        self.inst_setting = InstitutionSetting.objects.create(
            institution_name='Badan Meteorologi, Klimatologi, dan Geofisika',
            unit_name='Bagian Umum',
            head_officer_name='Dr. Sutopo',
            head_officer_nip='197501012000031001'
        )

    # 1. Admin dapat login dan mengelola barang
    def test_scenario_01_admin_login_and_manage_items(self):
        login_success = self.client.login(username='admin_bmn', password='Password123!')
        self.assertTrue(login_success)
        response = self.client.get(reverse('inventory:item_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kamera Sony A7 IV')

    # 2. Pegawai dapat login dan melihat katalog
    def test_scenario_02_employee_login_and_view_catalog(self):
        login_success = self.client.login(username='pegawai_andi', password='Password123!')
        self.assertTrue(login_success)
        response = self.client.get(reverse('loans:catalog'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kamera Sony A7 IV')
        # Consumable items MUST NOT appear in loan catalog
        self.assertNotContains(response, 'Kertas HVS A4 80gr')

    # 3. Pegawai tidak dapat mengakses halaman admin tanpa izin
    def test_scenario_03_employee_cannot_access_admin_views(self):
        self.client.login(username='pegawai_andi', password='Password123!')
        # Coba buka menu master barang yang khusus admin
        res1 = self.client.get(reverse('inventory:item_create'))
        self.assertEqual(res1.status_code, 403)
        # Coba buka penyerahan habis pakai
        res2 = self.client.get(reverse('consumables:handover_create'))
        self.assertEqual(res2.status_code, 403)
        # Coba buka audit log
        res3 = self.client.get(reverse('audit:log_list'))
        self.assertEqual(res3.status_code, 403)

    # 4. Pegawai tidak dapat melihat transaksi pegawai lain
    def test_scenario_04_employee_cannot_view_others_transactions(self):
        loan_andi = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=1),
            purpose='Keperluan Khusus Andi',
            status=LoanRequest.Status.PENDING
        )
        # Login sebagai Budi dan coba buka URL detail pinjaman Andi
        self.client.login(username='pegawai_budi', password='Password123!')
        response = self.client.get(reverse('loans:loan_detail', args=[loan_andi.pk]))
        self.assertEqual(response.status_code, 403)

    # 5. Barang CONSUMABLE tidak dapat dipinjam
    def test_scenario_05_consumable_cannot_be_loaned(self):
        loan = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=1),
            purpose='Uji coba pinjam ATK',
            status=LoanRequest.Status.PENDING
        )
        l_item = LoanItem(loan=loan, item=self.kertas, quantity_requested=2)
        with self.assertRaises(ValidationError):
            l_item.clean()

    # 6. Barang LOANABLE tidak dapat diproses melalui penyerahan habis pakai
    def test_scenario_06_loanable_cannot_be_issued_as_consumable(self):
        handover = ConsumableHandover.objects.create(
            recipient=self.pegawai1,
            department='Observasi',
            purpose='Uji serah proyektor',
            created_by=self.admin
        )
        c_item = ConsumableHandoverItem(handover=handover, item=self.kamera, quantity=1)
        with self.assertRaises(ValidationError):
            c_item.clean()

    # 7. Pengajuan peminjaman tidak mengurangi stok sebelum serah terima
    def test_scenario_07_loan_application_does_not_deduct_stock(self):
        self.client.login(username='pegawai_andi', password='Password123!')
        self.client.post(reverse('loans:loan_apply'), {
            'start_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': (timezone.now().date() + timezone.timedelta(days=2)).strftime('%Y-%m-%d'),
            'purpose': 'Liputan BMKG',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-item': self.kamera.id,
            'items-0-quantity_requested': '3',
            'items-0-notes': 'Kamera utama',
        })
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 5)
        self.assertEqual(self.kamera.stock_loaned, 0)

    # 8. Persetujuan tanpa serah terima tidak dianggap sebagai barang keluar
    def test_scenario_08_approval_does_not_deduct_stock(self):
        loan = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            purpose='Uji approval',
            status=LoanRequest.Status.PENDING
        )
        LoanItem.objects.create(loan=loan, item=self.kamera, quantity_requested=2)

        self.client.login(username='admin_bmn', password='Password123!')
        self.client.post(reverse('loans:loan_review', args=[loan.pk]), {
            'action': 'APPROVE',
            'rejection_reason': '',
        })
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanRequest.Status.APPROVED)

        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 5)
        self.assertEqual(self.kamera.stock_loaned, 0)

    # 9. Stok berkurang ketika barang benar-benar diserahkan
    def test_scenario_09_stock_deducted_upon_physical_handover(self):
        loan = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            purpose='Serah terima fisik',
            status=LoanRequest.Status.APPROVED
        )
        l_item = LoanItem.objects.create(loan=loan, item=self.kamera, quantity_requested=2)

        self.client.login(username='admin_bmn', password='Password123!')
        self.client.post(reverse('loans:handover_create', args=[loan.pk]), {
            f'qty_{l_item.id}': '2',
            f'cond_{l_item.id}': 'Baik / Layak Pakai',
        })
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 3)
        self.assertEqual(self.kamera.stock_loaned, 2)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanRequest.Status.ACTIVE)

    # 10. Pengembalian sebagian memperbarui saldo dengan benar
    def test_scenario_10_partial_return_updates_balances_correctly(self):
        InventoryService.issue_loan(self.kamera.id, 4, 'SRH-PARTIAL', self.admin, 'Serah 4 kamera')
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 1)
        self.assertEqual(self.kamera.stock_loaned, 4)

        # Kembalikan 2 unit dalam kondisi baik
        InventoryService.return_loan_items(
            item_id=self.kamera.id,
            qty_usable=2,
            qty_damaged=0,
            qty_lost=0,
            reference_number='KMB-PARTIAL',
            user=self.admin,
            reason='Kembali sebagian'
        )
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 3)
        self.assertEqual(self.kamera.stock_loaned, 2)

    # 11. Pengembalian melebihi jumlah yang dipinjam ditolak
    def test_scenario_11_over_return_rejected(self):
        InventoryService.issue_loan(self.kamera.id, 2, 'SRH-OVER', self.admin, 'Serah 2 kamera')
        with self.assertRaises(ValidationError):
            InventoryService.return_loan_items(
                item_id=self.kamera.id,
                qty_usable=5,
                qty_damaged=0,
                qty_lost=0,
                reference_number='KMB-OVER',
                user=self.admin,
                reason='Kelebihan pengembalian'
            )

    # 12. Barang rusak tidak langsung menjadi stok tersedia
    def test_scenario_12_damaged_return_does_not_increment_available_stock(self):
        InventoryService.issue_loan(self.kamera.id, 2, 'SRH-DMG', self.admin, 'Serah 2')
        self.kamera.refresh_from_db()
        # Saldo awal: tersedia 3, dipinjam 2
        self.assertEqual(self.kamera.stock_available, 3)
        self.assertEqual(self.kamera.stock_loaned, 2)

        # Kembalikan 1 rusak, 0 layak
        InventoryService.return_loan_items(
            item_id=self.kamera.id,
            qty_usable=0,
            qty_damaged=1,
            qty_lost=0,
            reference_number='KMB-DMG',
            user=self.admin,
            reason='Kembali rusak'
        )
        self.kamera.refresh_from_db()
        # Stok tersedia TETAP 3 (tidak boleh bertambah!)
        self.assertEqual(self.kamera.stock_available, 3)
        # Stok rusak menjadi 1
        self.assertEqual(self.kamera.stock_damaged, 1)
        # Stok dipinjam berkurang jadi 1
        self.assertEqual(self.kamera.stock_loaned, 1)

    # 13. Penyerahan habis pakai mengurangi stok satu kali
    def test_scenario_13_consumable_issue_reduces_stock_once(self):
        InventoryService.issue_consumable(self.kertas.id, 10, 'HPK-TEST', self.admin, 'Kertas TU')
        self.kertas.refresh_from_db()
        self.assertEqual(self.kertas.stock_available, 30)
        self.assertEqual(self.kertas.stock_loaned, 0)

    # 14. Stok tidak boleh negatif
    def test_scenario_14_stock_cannot_be_negative(self):
        with self.assertRaises(ValidationError):
            InventoryService.issue_consumable(self.kertas.id, 100, 'HPK-MINUS', self.admin, 'Melebihi saldo')

    # 15. Pemrosesan ganda tidak menggandakan perubahan stok
    def test_scenario_15_double_processing_prevented(self):
        loan = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=1),
            purpose='Uji pemrosesan ganda',
            status=LoanRequest.Status.PENDING
        )
        LoanItem.objects.create(loan=loan, item=self.kamera, quantity_requested=1)

        self.client.login(username='admin_bmn', password='Password123!')
        # First review
        self.client.post(reverse('loans:loan_review', args=[loan.pk]), {'action': 'APPROVE'})
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanRequest.Status.APPROVED)

        # Second review attempt: should be rejected/ignored
        res = self.client.post(reverse('loans:loan_review', args=[loan.pk]), {'action': 'REJECT'})
        self.assertEqual(res.status_code, 302)
        loan.refresh_from_db()
        # Status remains APPROVED
        self.assertEqual(loan.status, LoanRequest.Status.APPROVED)

    # 16. Pembatalan transaksi memiliki jejak audit
    def test_scenario_16_cancellation_has_audit_trail(self):
        self.client.login(username='admin_bmn', password='Password123!')
        handover = ConsumableHandover.objects.create(
            recipient=self.pegawai1,
            department='TU',
            purpose='Acara Rapat',
            status=ConsumableHandover.Status.CONFIRMED,
            created_by=self.admin
        )
        ConsumableHandoverItem.objects.create(handover=handover, item=self.kertas, quantity=5)
        self.kertas.stock_available -= 5
        self.kertas.save()

        # Batalkan
        self.client.post(reverse('consumables:handover_cancel', args=[handover.pk]), {
            'reason': 'Rapat dibatalkan panitia'
        })
        self.assertTrue(AuditLog.objects.filter(entity_type='ConsumableHandover', action=AuditLog.Action.CANCEL).exists())

    # 17. Nomor transaksi tidak duplikat
    def test_scenario_17_unique_transaction_numbers(self):
        loan1 = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=1),
            purpose='Peminjaman 1'
        )
        loan2 = LoanRequest.objects.create(
            borrower=self.pegawai2,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=1),
            purpose='Peminjaman 2'
        )
        self.assertNotEqual(loan1.loan_number, loan2.loan_number)

    # 18. Laporan sesuai dengan data transaksi
    def test_scenario_18_report_matches_actual_transactions(self):
        self.client.login(username='admin_bmn', password='Password123!')
        response = self.client.get(reverse('reports:admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        # Total items should match count
        self.assertEqual(response.context['stats']['total_items'], 2)

    # 19. Pengguna tidak dapat memalsukan identitas peminjam melalui request
    def test_scenario_19_cannot_spoof_borrower_identity(self):
        self.client.login(username='pegawai_andi', password='Password123!')
        # Post request trying to pass borrower=pegawai_budi
        self.client.post(reverse('loans:loan_apply'), {
            'borrower': self.pegawai2.id,
            'start_date': timezone.now().date().strftime('%Y-%m-%d'),
            'due_date': (timezone.now().date() + timezone.timedelta(days=1)).strftime('%Y-%m-%d'),
            'purpose': 'Coba palsukan identitas peminjam',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-item': self.kamera.id,
            'items-0-quantity_requested': '1',
        })
        created_loan = LoanRequest.objects.filter(purpose='Coba palsukan identitas peminjam').first()
        self.assertIsNotNone(created_loan)
        # Server must enforce that borrower is request.user (Andi), NOT Budi!
        self.assertEqual(created_loan.borrower, self.pegawai1)

    # 20. Dokumen transaksi dapat dibuat dari data yang benar
    def test_scenario_20_printable_documents_rendered_accurately(self):
        loan = LoanRequest.objects.create(
            borrower=self.pegawai1,
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=2),
            purpose='Verifikasi Slip Cetak',
            status=LoanRequest.Status.APPROVED
        )
        LoanItem.objects.create(loan=loan, item=self.kamera, quantity_requested=1)

        self.client.login(username='admin_bmn', password='Password123!')
        response = self.client.get(reverse('reports:print_loan_slip', args=[loan.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, loan.loan_number)
        self.assertContains(response, self.pegawai1.display_name)
        self.assertContains(response, self.kamera.name)
        self.assertContains(response, self.inst_setting.head_officer_name)
