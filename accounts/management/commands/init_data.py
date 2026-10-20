import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from accounts.models import CustomUser
from inventory.models import Category, Location, Item, StockMovement
from inventory.services import InventoryService
from loans.models import LoanRequest, LoanItem, LoanHandover, LoanHandoverItem, ReturnRecord, ReturnItem
from consumables.models import ConsumableHandover, ConsumableHandoverItem
from audit.models import AuditLog, InstitutionSetting
from audit.utils import log_action


class Command(BaseCommand):
    help = "Inisialisasi data awal / seed data demonstrasi untuk BMKG SIP3B"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Memulai inisialisasi data awal..."))

        # 1. Pengaturan Instansi
        inst_setting, created = InstitutionSetting.objects.get_or_create(
            id=1,
            defaults={
                'institution_name': 'Badan Meteorologi, Klimatologi, dan Geofisika (BMKG)',
                'unit_name': 'Bagian Umum dan Tata Usaha - Pengelola BMN',
                'address': 'Jl. Angkasa I No. 2, Kemayoran, Jakarta Pusat 10610',
                'phone': '(021) 4246321 / 6546316',
                'email': 'bmn@bmkg.go.id',
                'head_officer_name': 'Dr. Ir. Dwi Hartanto, M.Si.',
                'head_officer_nip': '19750315 199903 1 002',
                'warehouse_officer_name': 'Eko Prasetyo, S.Kom.',
                'warehouse_officer_nip': '19850512 201001 1 002',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("✓ Pengaturan instansi BMKG berhasil dibuat."))

        # 2. Akun Pengguna (Admin & Pegawai)
        users_data = [
            {
                'username': 'admin',
                'password': 'admin123',
                'role': CustomUser.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Administrator',
                'last_name': 'BMN',
                'employee_number': '19800101 200501 1 001',
                'department': 'Bagian Umum dan Tata Usaha',
                'phone_number': '081122334455'
            },
            {
                'username': 'petugas',
                'password': 'petugas123',
                'role': CustomUser.Role.ADMIN,
                'is_staff': True,
                'is_superuser': False,
                'first_name': 'Eko',
                'last_name': 'Prasetyo',
                'employee_number': '19850512 201001 1 002',
                'department': 'Pengelola Barang Milik Negara (BMN)',
                'phone_number': '081234567890'
            },
            {
                'username': 'pegawai_andi',
                'password': 'pegawai123',
                'role': CustomUser.Role.EMPLOYEE,
                'is_staff': False,
                'is_superuser': False,
                'first_name': 'Andi',
                'last_name': 'Kurniawan',
                'employee_number': '19900101 201501 1 002',
                'department': 'Pusat Meteorologi Penerbangan',
                'phone_number': '081398765432'
            },
            {
                'username': 'pegawai_budi',
                'password': 'pegawai123',
                'role': CustomUser.Role.EMPLOYEE,
                'is_staff': False,
                'is_superuser': False,
                'first_name': 'Budi',
                'last_name': 'Santoso',
                'employee_number': '19920202 201602 1 003',
                'department': 'Pusat Seismologi Teknik & Tsunami',
                'phone_number': '081387654321'
            },
            {
                'username': 'pegawai_citra',
                'password': 'pegawai123',
                'role': CustomUser.Role.EMPLOYEE,
                'is_staff': False,
                'is_superuser': False,
                'first_name': 'Citra',
                'last_name': 'Lestari',
                'employee_number': '19940303 201803 2 004',
                'department': 'Biro Hukum dan Organisasi',
                'phone_number': '081376543210'
            },
        ]

        created_users = {}
        for u in users_data:
            user, created = CustomUser.objects.get_or_create(
                username=u['username'],
                defaults={
                    'role': u['role'],
                    'is_staff': u['is_staff'],
                    'is_superuser': u['is_superuser'],
                    'first_name': u['first_name'],
                    'last_name': u['last_name'],
                    'employee_number': u['employee_number'],
                    'department': u['department'],
                    'phone_number': u['phone_number'],
                }
            )
            if created:
                user.set_password(u['password'])
                user.save()
            created_users[u['username']] = user

        admin_user = created_users['admin']
        petugas_user = created_users['petugas']
        andi_user = created_users['pegawai_andi']
        budi_user = created_users['pegawai_budi']
        citra_user = created_users['pegawai_citra']
        self.stdout.write(self.style.SUCCESS(f"✓ {len(created_users)} akun pengguna siap."))

        # 3. Kategori Master
        categories_data = [
            ("Peralatan Elektronik & IT", "Perangkat komputasi dan jaringan operasional"),
            ("Audio Visual & Dokumentasi", "Peralatan liputan, kamera, mikrofon, proyektor"),
            ("Alat Pengukuran Lapangan", "Peralatan survei geofisika dan observasi cuaca"),
            ("Alat Tulis Kantor (ATK)", "Barang persediaan habis pakai administrasi"),
            ("Perlengkapan Fasilitas Kantor", "Perlengkapan operasional ruang kerja"),
        ]
        cat_map = {}
        for name, desc in categories_data:
            cat, _ = Category.objects.get_or_create(name=name, defaults={'description': desc, 'is_active': True})
            cat_map[name] = cat

        # 4. Lokasi Penyimpanan
        locations_data = [
            ("Gudang Utama BMN Lt. 1", "Penyimpanan pusat inventaris dan BMN"),
            ("Ruang IT & Server Lt. 2", "Penyimpanan perangkat keras jaringan & laptop"),
            ("Lemari ATK Bagian Umum Lt. 1", "Penyimpanan persediaan habis pakai"),
            ("Ruang Arsip & Logistik Lt. 3", "Penyimpanan dokumen dan perlengkapan lama"),
        ]
        loc_map = {}
        for name, desc in locations_data:
            loc, _ = Location.objects.get_or_create(name=name, defaults={'description': desc, 'is_active': True})
            loc_map[name] = loc
        self.stdout.write(self.style.SUCCESS("✓ Kategori dan lokasi master siap."))

        # 5. Master Barang (LOANABLE & CONSUMABLE)
        items_data = [
            # LOANABLE
            {
                'code': 'LOAN-IT-001',
                'name': 'Laptop Dell Latitude 5430 (Core i7 / 16GB)',
                'category': cat_map["Peralatan Elektronik & IT"],
                'item_type': Item.ItemType.LOANABLE,
                'unit': 'Unit',
                'location': loc_map["Ruang IT & Server Lt. 2"],
                'stock_available': 6,
                'minimum_stock': 1,
                'description': 'Laptop dinas lapangan dan presentasi pimpinan'
            },
            {
                'code': 'LOAN-AV-001',
                'name': 'Kamera DSLR Canon EOS 90D Kit',
                'category': cat_map["Audio Visual & Dokumentasi"],
                'item_type': Item.ItemType.LOANABLE,
                'unit': 'Unit',
                'location': loc_map["Gudang Utama BMN Lt. 1"],
                'stock_available': 3,
                'minimum_stock': 1,
                'description': 'Kamera liputan rilis pers dan dokumentasi gempa bumi'
            },
            {
                'code': 'LOAN-AV-002',
                'name': 'Proyektor Epson EB-X500 3600 Lumens',
                'category': cat_map["Audio Visual & Dokumentasi"],
                'item_type': Item.ItemType.LOANABLE,
                'unit': 'Unit',
                'location': loc_map["Gudang Utama BMN Lt. 1"],
                'stock_available': 4,
                'minimum_stock': 1,
                'description': 'Proyektor HDMI untuk rapat koordinasi lintas bagian'
            },
            {
                'code': 'LOAN-IT-002',
                'name': 'Monitor Portable ASUS ZenScreen 15.6"',
                'category': cat_map["Peralatan Elektronik & IT"],
                'item_type': Item.ItemType.LOANABLE,
                'unit': 'Unit',
                'location': loc_map["Ruang IT & Server Lt. 2"],
                'stock_available': 5,
                'minimum_stock': 1,
                'description': 'Layar tambahan untuk posko pemantauan darurat'
            },
            {
                'code': 'LOAN-LAP-001',
                'name': 'Handy Talky Motorola CP1660 VHF',
                'category': cat_map["Alat Pengukuran Lapangan"],
                'item_type': Item.ItemType.LOANABLE,
                'unit': 'Unit',
                'location': loc_map["Gudang Utama BMN Lt. 1"],
                'stock_available': 8,
                'minimum_stock': 2,
                'description': 'Alat komunikasi radio tim tanggap bencana'
            },

            # CONSUMABLE
            {
                'code': 'CON-ATK-001',
                'name': 'Kertas HVS A4 80gr Sinar Dunia',
                'category': cat_map["Alat Tulis Kantor (ATK)"],
                'item_type': Item.ItemType.CONSUMABLE,
                'unit': 'Rim',
                'location': loc_map["Lemari ATK Bagian Umum Lt. 1"],
                'stock_available': 50,
                'minimum_stock': 10,
                'description': 'Kertas cetak laporan dinas dan naskah dinas resmi'
            },
            {
                'code': 'CON-ATK-002',
                'name': 'Pulpen Standard AE7 0.5 Hitam',
                'category': cat_map["Alat Tulis Kantor (ATK)"],
                'item_type': Item.ItemType.CONSUMABLE,
                'unit': 'Kotak',
                'location': loc_map["Lemari ATK Bagian Umum Lt. 1"],
                'stock_available': 100,
                'minimum_stock': 20,
                'description': 'Pulpen operasional harian kantor (1 kotak isi 12)'
            },
            {
                'code': 'CON-ATK-003',
                'name': 'Map Stopmap Folio Buffalo Biru',
                'category': cat_map["Alat Tulis Kantor (ATK)"],
                'item_type': Item.ItemType.CONSUMABLE,
                'unit': 'Buah',
                'location': loc_map["Lemari ATK Bagian Umum Lt. 1"],
                'stock_available': 80,
                'minimum_stock': 15,
                'description': 'Map berkas arsip dan nota dinas'
            },
            {
                'code': 'CON-ATK-004',
                'name': 'Tinta Botol HP GT53 Original Black',
                'category': cat_map["Alat Tulis Kantor (ATK)"],
                'item_type': Item.ItemType.CONSUMABLE,
                'unit': 'Botol',
                'location': loc_map["Lemari ATK Bagian Umum Lt. 1"],
                'stock_available': 20,
                'minimum_stock': 5,
                'description': 'Tinta printer tank operasional sekretariat'
            },
            {
                'code': 'CON-FAS-001',
                'name': 'Baterai AA Alkaline ABC (Isi 2)',
                'category': cat_map["Perlengkapan Fasilitas Kantor"],
                'item_type': Item.ItemType.CONSUMABLE,
                'unit': 'Pack',
                'location': loc_map["Lemari ATK Bagian Umum Lt. 1"],
                'stock_available': 40,
                'minimum_stock': 10,
                'description': 'Baterai perangkat radio HT, mouse, dan pointer laser'
            },
        ]

        item_map = {}
        for it in items_data:
            item, created = Item.objects.get_or_create(
                code=it['code'],
                defaults={
                    'name': it['name'],
                    'category': it['category'],
                    'item_type': it['item_type'],
                    'unit': it['unit'],
                    'location': it['location'],
                    'stock_available': it['stock_available'],
                    'minimum_stock': it['minimum_stock'],
                    'description': it['description'],
                    'is_active': True
                }
            )
            item_map[it['code']] = item
            if created:
                # Catat saldo awal di StockMovement
                StockMovement.objects.create(
                    item=item,
                    movement_type=StockMovement.MovementType.INITIAL,
                    quantity=it['stock_available'],
                    stock_available_before=0,
                    stock_available_after=it['stock_available'],
                    stock_loaned_before=0,
                    stock_loaned_after=0,
                    reference_number=f"INIT-{item.code}",
                    created_by=admin_user,
                    reason="Pencatatan Saldo Awal Inventaris BMKG"
                )

        self.stdout.write(self.style.SUCCESS(f"✓ {len(item_map)} master barang dan saldo awal siap."))

        # 6. Transaksi Sampel untuk Dashboard dan Laporan Real-time
        # A. Pengajuan Peminjaman Menunggu Persetujuan (PENDING)
        now = timezone.now()
        today = now.date()

        if not LoanRequest.objects.filter(purpose="Sosialisasi Sistem Peringatan Dini Cuaca Ekstrem").exists():
            loan_pending = LoanRequest.objects.create(
                borrower=citra_user,
                start_date=today + timezone.timedelta(days=1),
                due_date=today + timezone.timedelta(days=4),
                purpose="Sosialisasi Sistem Peringatan Dini Cuaca Ekstrem",
                status=LoanRequest.Status.PENDING
            )
            LoanItem.objects.create(
                loan=loan_pending,
                item=item_map['LOAN-IT-001'], # Laptop
                quantity_requested=1,
                notes="Siap pakai Office 365"
            )
            LoanItem.objects.create(
                loan=loan_pending,
                item=item_map['LOAN-AV-002'], # Proyektor
                quantity_requested=1,
                notes="Disertai kabel HDMI panjang"
            )
            log_action(citra_user, AuditLog.Action.CREATE, 'LoanRequest', loan_pending.id, {'no': loan_pending.loan_number})

        # B. Transaksi Peminjaman Aktif (ACTIVE) yang sudah diserahkan fisiknya
        if not LoanRequest.objects.filter(purpose="Peliputan Lapangan Pantauan Siklon Tropis").exists():
            loan_active = LoanRequest.objects.create(
                borrower=andi_user,
                start_date=today - timezone.timedelta(days=2),
                due_date=today + timezone.timedelta(days=3),
                purpose="Peliputan Lapangan Pantauan Siklon Tropis",
                status=LoanRequest.Status.ACTIVE,
                reviewed_by=petugas_user,
                reviewed_at=now - timezone.timedelta(days=2)
            )
            l_cam = LoanItem.objects.create(
                loan=loan_active,
                item=item_map['LOAN-AV-001'], # Kamera
                quantity_requested=1,
                quantity_handed_over=1,
                notes="Body + Lensa + Tas"
            )
            l_ht = LoanItem.objects.create(
                loan=loan_active,
                item=item_map['LOAN-LAP-001'], # HT
                quantity_requested=2,
                quantity_handed_over=2,
                notes="Saluran CH-01 BMKG Utama"
            )

            # Buat Dokumen Serah Terima
            handover_doc = LoanHandover.objects.create(
                loan=loan_active,
                recipient=andi_user,
                handover_date=now - timezone.timedelta(days=2),
                handed_over_by=petugas_user,
                notes="Serah terima fisik di Gudang BMN, barang dicek berfungsi baik."
            )
            LoanHandoverItem.objects.create(
                handover=handover_doc,
                loan_item=l_cam,
                quantity=1,
                initial_condition="Baik / Layak Pakai",
                notes="Baterai terisi penuh"
            )
            LoanHandoverItem.objects.create(
                handover=handover_doc,
                loan_item=l_ht,
                quantity=2,
                initial_condition="Baik / Layak Pakai",
                notes="Antena dan charger lengkap"
            )

            # Kurangi stok tersedia, tambah stok dipinjam via InventoryService
            InventoryService.issue_loan(item_map['LOAN-AV-001'].id, 1, handover_doc.handover_number, petugas_user, "Serah terima pinjaman Andi")
            InventoryService.issue_loan(item_map['LOAN-LAP-001'].id, 2, handover_doc.handover_number, petugas_user, "Serah terima pinjaman Andi")

        # C. Transaksi Peminjaman Selesai (COMPLETED) yang sudah dikembalikan
        if not LoanRequest.objects.filter(purpose="Monitoring Gempa Tektonik Wilayah Banten").exists():
            loan_done = LoanRequest.objects.create(
                borrower=budi_user,
                start_date=today - timezone.timedelta(days=10),
                due_date=today - timezone.timedelta(days=3),
                purpose="Monitoring Gempa Tektonik Wilayah Banten",
                status=LoanRequest.Status.COMPLETED,
                reviewed_by=petugas_user,
                reviewed_at=now - timezone.timedelta(days=10)
            )
            l_mon = LoanItem.objects.create(
                loan=loan_done,
                item=item_map['LOAN-IT-002'], # Monitor Portable
                quantity_requested=1,
                quantity_handed_over=1,
                quantity_returned_usable=1,
                notes="Untuk posko lapangan"
            )
            ret_doc = ReturnRecord.objects.create(
                loan=loan_done,
                return_date=now - timezone.timedelta(days=3),
                received_by=petugas_user,
                notes="Kembali lengkap beserta kabel Type-C dan smart cover."
            )
            ReturnItem.objects.create(
                return_record=ret_doc,
                loan_item=l_mon,
                quantity_usable=1,
                quantity_damaged=0,
                quantity_lost=0,
                damage_notes="Berfungsi normal tanpa goresan"
            )
            # Ledger peminjaman dan pengembalian
            StockMovement.objects.create(
                item=item_map['LOAN-IT-002'],
                movement_type=StockMovement.MovementType.RETURN_USABLE,
                quantity=1,
                stock_available_before=item_map['LOAN-IT-002'].stock_available,
                stock_available_after=item_map['LOAN-IT-002'].stock_available,
                stock_loaned_before=1,
                stock_loaned_after=0,
                reference_number=ret_doc.return_number,
                created_by=petugas_user,
                reason="Pengembalian selesai tepat waktu kondisi baik"
            )

        # D. Penyerahan Barang Habis Pakai (CONSUMABLE)
        if not ConsumableHandover.objects.filter(purpose="Dukungan Administrasi Naskah Dinas Seksi Observasi").exists():
            c_handover = ConsumableHandover.objects.create(
                recipient=andi_user,
                department=andi_user.department,
                handover_date=now - timezone.timedelta(days=1),
                purpose="Dukungan Administrasi Naskah Dinas Seksi Observasi",
                status=ConsumableHandover.Status.CONFIRMED,
                created_by=petugas_user,
                notes="Distribusi rutin ATK bulanan"
            )
            ConsumableHandoverItem.objects.create(
                handover=c_handover,
                item=item_map['CON-ATK-001'], # Kertas
                quantity=5,
                notes="5 Rim Kertas A4"
            )
            ConsumableHandoverItem.objects.create(
                handover=c_handover,
                item=item_map['CON-ATK-002'], # Pulpen
                quantity=2,
                notes="2 Kotak Pulpen AE7"
            )
            # Potong stok habis pakai via service
            InventoryService.issue_consumable(item_map['CON-ATK-001'].id, 5, c_handover.handover_number, petugas_user, "Distribusi ATK bulanan Seksi Observasi")
            InventoryService.issue_consumable(item_map['CON-ATK-002'].id, 2, c_handover.handover_number, petugas_user, "Distribusi ATK bulanan Seksi Observasi")

        self.stdout.write(self.style.SUCCESS("✓ Transaksi contoh peminjaman & habis pakai berhasil disimulasikan."))
        self.stdout.write(self.style.SUCCESS("=== Inisialisasi Data Selesai 100% ==="))
        self.stdout.write(self.style.NOTICE("Kredensial Login:"))
        self.stdout.write("  - Administrator: username='admin' | password='admin123'")
        self.stdout.write("  - Petugas Gudang: username='petugas' | password='petugas123'")
        self.stdout.write("  - Pegawai (Andi): username='pegawai_andi' | password='pegawai123'")
        self.stdout.write("  - Pegawai (Budi): username='pegawai_budi' | password='pegawai123'")
        self.stdout.write("  - Pegawai (Citra): username='pegawai_citra' | password='pegawai123'")
