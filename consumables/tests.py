from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import CustomUser
from inventory.models import Category, Location, Item, StockMovement
from consumables.models import ConsumableHandover, ConsumableHandoverItem


class ConsumablesTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = CustomUser.objects.create_user(
            username='admin_cs',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )
        self.pegawai = CustomUser.objects.create_user(
            username='pegawai_cs',
            password='Password123!',
            role=CustomUser.Role.EMPLOYEE,
            first_name='Rahmat',
            department='Tata Usaha'
        )

        self.cat_atk = Category.objects.create(name='Alat Tulis Kantor')
        self.cat_elek = Category.objects.create(name='Elektronik')

        self.pulpen = Item.objects.create(
            code='ATK-001',
            name='Pulpen Gel Hitam',
            category=self.cat_atk,
            item_type=Item.ItemType.CONSUMABLE,
            unit='Kotak',
            stock_available=30,
            minimum_stock=5
        )

        self.proyektor = Item.objects.create(
            code='PRJ-001',
            name='Proyektor Epson',
            category=self.cat_elek,
            item_type=Item.ItemType.LOANABLE,
            unit='Unit',
            stock_available=3
        )

    def test_admin_create_consumable_handover(self):
        self.client.login(username='admin_cs', password='Password123!')
        data = {
            'recipient': self.pegawai.id,
            'department': 'Tata Usaha',
            'purpose': 'Kebutuhan administrasi bulanan',
            'notes': 'Diserahkan langsung',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '1',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-item': self.pulpen.id,
            'items-0-quantity': '10',
            'items-0-notes': 'Box baru',
        }
        response = self.client.post(reverse('consumables:handover_create'), data)
        self.assertEqual(response.status_code, 302)

        handover = ConsumableHandover.objects.get(recipient=self.pegawai)
        self.assertEqual(handover.status, ConsumableHandover.Status.CONFIRMED)

        # Stock available is directly deducted
        self.pulpen.refresh_from_db()
        self.assertEqual(self.pulpen.stock_available, 20)
        self.assertEqual(self.pulpen.stock_loaned, 0)
        self.assertTrue(StockMovement.objects.filter(reference_number=handover.handover_number).exists())

    def test_employee_cannot_access_consumable_create(self):
        self.client.login(username='pegawai_cs', password='Password123!')
        response = self.client.get(reverse('consumables:handover_create'))
        self.assertEqual(response.status_code, 403)

    def test_cancel_consumable_handover_restores_stock(self):
        self.client.login(username='admin_cs', password='Password123!')
        # Initial handover of 5 boxes
        handover = ConsumableHandover.objects.create(
            recipient=self.pegawai,
            department='TU',
            purpose='Rapat',
            status=ConsumableHandover.Status.CONFIRMED,
            created_by=self.admin
        )
        ConsumableHandoverItem.objects.create(
            handover=handover,
            item=self.pulpen,
            quantity=5
        )
        self.pulpen.stock_available = 25
        self.pulpen.save()

        # Cancel the handover
        response = self.client.post(reverse('consumables:handover_cancel', args=[handover.pk]), {
            'reason': 'Acara rapat dibatalkan, barang dikembalikan ke gudang'
        })
        self.assertEqual(response.status_code, 302)

        handover.refresh_from_db()
        self.assertEqual(handover.status, ConsumableHandover.Status.CANCELLED)

        # Stock is restored
        self.pulpen.refresh_from_db()
        self.assertEqual(self.pulpen.stock_available, 30)
        self.assertTrue(StockMovement.objects.filter(reference_number=f"BATAL-{handover.handover_number}").exists())
