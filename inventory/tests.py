from django.test import TestCase
from django.core.exceptions import ValidationError
from accounts.models import CustomUser
from inventory.models import Category, Location, Item, StockMovement
from inventory.services import InventoryService


class InventoryTestCase(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='admin_inv',
            password='Password123!',
            role=CustomUser.Role.ADMIN
        )
        self.cat_elektronik = Category.objects.create(name='Elektronik')
        self.cat_atk = Category.objects.create(name='ATK')
        self.loc_gudang = Location.objects.create(name='Gudang BMN Lt. 1')

        self.kamera = Item.objects.create(
            code='CAM-001',
            name='Kamera Sony A7 III',
            category=self.cat_elektronik,
            item_type=Item.ItemType.LOANABLE,
            unit='Unit',
            location=self.loc_gudang,
            stock_available=5,
            minimum_stock=2
        )

        self.kertas = Item.objects.create(
            code='KRT-001',
            name='Kertas HVS A4 80gr',
            category=self.cat_atk,
            item_type=Item.ItemType.CONSUMABLE,
            unit='Rim',
            location=self.loc_gudang,
            stock_available=50,
            minimum_stock=10
        )

    def test_item_properties(self):
        self.assertTrue(self.kamera.is_loanable)
        self.assertFalse(self.kamera.is_consumable)
        self.assertTrue(self.kertas.is_consumable)
        self.assertFalse(self.kertas.is_loanable)
        self.assertEqual(self.kamera.total_stock, 5)

    def test_consumable_cannot_have_loaned_stock(self):
        self.kertas.stock_loaned = 2
        with self.assertRaises(ValidationError):
            self.kertas.clean()

    def test_negative_stock_prevented(self):
        self.kamera.stock_available = -1
        with self.assertRaises(ValidationError):
            self.kamera.clean()

    def test_inventory_service_issue_loan(self):
        InventoryService.issue_loan(
            item_id=self.kamera.id,
            quantity=2,
            reference_number='SRH-TEST-001',
            user=self.admin,
            reason='Uji serah terima pinjaman'
        )
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 3)
        self.assertEqual(self.kamera.stock_loaned, 2)
        self.assertEqual(self.kamera.total_stock, 5)
        self.assertTrue(StockMovement.objects.filter(reference_number='SRH-TEST-001').exists())

    def test_inventory_service_insufficient_stock(self):
        with self.assertRaises(ValidationError):
            InventoryService.issue_loan(
                item_id=self.kamera.id,
                quantity=10,
                reference_number='SRH-FAIL',
                user=self.admin,
                reason='Melebihi ketersediaan'
            )

    def test_inventory_service_return_usable_and_damaged(self):
        # Initial handover of 3 cameras
        InventoryService.issue_loan(self.kamera.id, 3, 'SRH-01', self.admin, 'Serah')
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 2)
        self.assertEqual(self.kamera.stock_loaned, 3)

        # Return: 1 Usable, 1 Damaged, 0 Lost
        InventoryService.return_loan_items(
            item_id=self.kamera.id,
            qty_usable=1,
            qty_damaged=1,
            qty_lost=0,
            reference_number='KMB-01',
            user=self.admin,
            reason='Pengembalian sebagian'
        )
        self.kamera.refresh_from_db()
        # Available stock should only increase by usable (2 + 1 = 3)
        self.assertEqual(self.kamera.stock_available, 3)
        # Damaged stock increased by 1
        self.assertEqual(self.kamera.stock_damaged, 1)
        # Loaned stock decreased by 2 (3 - 2 = 1)
        self.assertEqual(self.kamera.stock_loaned, 1)
        # Total stock remains 5 (3 + 1 + 1)
        self.assertEqual(self.kamera.total_stock, 5)

    def test_inventory_service_issue_consumable(self):
        InventoryService.issue_consumable(
            item_id=self.kertas.id,
            quantity=15,
            reference_number='HPK-01',
            user=self.admin,
            reason='ATK Seksi Meteorologi'
        )
        self.kertas.refresh_from_db()
        self.assertEqual(self.kertas.stock_available, 35)
        self.assertEqual(self.kertas.stock_loaned, 0)
        self.assertTrue(StockMovement.objects.filter(reference_number='HPK-01').exists())

    def test_adjust_stock_service(self):
        InventoryService.adjust_stock(
            item_id=self.kamera.id,
            new_available=8,
            user=self.admin,
            reason='Stock Opname Bulanan'
        )
        self.kamera.refresh_from_db()
        self.assertEqual(self.kamera.stock_available, 8)
        self.assertTrue(StockMovement.objects.filter(reference_number='ADJ-CAM-001').exists())
