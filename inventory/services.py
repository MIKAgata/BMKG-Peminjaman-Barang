from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Item, StockMovement
from audit.utils import log_action
from audit.models import AuditLog


class InventoryService:
    @staticmethod
    @transaction.atomic
    def issue_loan(item_id, quantity, reference_number, user, reason):
        """
        Penyerahan fisik barang pinjaman (LOANABLE).
        Stok tersedia berkurang, stok sedang dipinjam bertambah.
        """
        item = Item.objects.select_for_update().get(pk=item_id)
        if item.item_type != Item.ItemType.LOANABLE:
            raise ValidationError(f"Barang '{item.name}' bukan barang pinjaman (LOANABLE).")
        if quantity <= 0:
            raise ValidationError("Jumlah serah terima harus lebih dari 0.")
        if item.stock_available < quantity:
            raise ValidationError(
                f"Stok tersedia '{item.name}' tidak mencukupi (Tersedia: {item.stock_available}, Diminta: {quantity})."
            )

        avail_before = item.stock_available
        loaned_before = item.stock_loaned

        item.stock_available -= quantity
        item.stock_loaned += quantity
        item.save()

        movement = StockMovement.objects.create(
            item=item,
            movement_type=StockMovement.MovementType.HANDOVER_LOAN,
            quantity=quantity,
            stock_available_before=avail_before,
            stock_available_after=item.stock_available,
            stock_loaned_before=loaned_before,
            stock_loaned_after=item.stock_loaned,
            reference_number=reference_number,
            created_by=user,
            reason=reason
        )

        log_action(
            user,
            AuditLog.Action.HANDOVER,
            'Item',
            item.id,
            {'ref': reference_number, 'qty': quantity, 'stock_after': item.stock_available}
        )
        return movement

    @staticmethod
    @transaction.atomic
    def return_loan_items(item_id, qty_usable, qty_damaged, qty_lost, reference_number, user, reason):
        """
        Pencatatan pengembalian barang pinjaman.
        Kondisi:
        - qty_usable: stok dipinjam berkurang, stok tersedia bertambah.
        - qty_damaged: stok dipinjam berkurang, stok rusak bertambah (tersedia TIDAK bertambah).
        - qty_lost: stok dipinjam berkurang, stok hilang bertambah (tersedia TIDAK bertambah).
        """
        total_returned = qty_usable + qty_damaged + qty_lost
        if total_returned <= 0:
            raise ValidationError("Total barang yang dikembalikan harus lebih dari 0.")

        item = Item.objects.select_for_update().get(pk=item_id)
        if total_returned > item.stock_loaned:
            raise ValidationError(
                f"Jumlah pengembalian ({total_returned}) melebihi saldo yang sedang dipinjam ({item.stock_loaned})."
            )

        avail_before = item.stock_available
        loaned_before = item.stock_loaned

        item.stock_loaned -= total_returned
        if qty_usable > 0:
            item.stock_available += qty_usable
        if qty_damaged > 0:
            item.stock_damaged += qty_damaged
        if qty_lost > 0:
            item.stock_lost += qty_lost

        item.save()

        # Record movements for each condition if applicable
        if qty_usable > 0:
            StockMovement.objects.create(
                item=item,
                movement_type=StockMovement.MovementType.RETURN_USABLE,
                quantity=qty_usable,
                stock_available_before=avail_before,
                stock_available_after=item.stock_available,
                stock_loaned_before=loaned_before,
                stock_loaned_after=item.stock_loaned,
                reference_number=reference_number,
                created_by=user,
                reason=f"Pengembalian kondisi layak: {reason}"
            )
        if qty_damaged > 0:
            StockMovement.objects.create(
                item=item,
                movement_type=StockMovement.MovementType.RETURN_DAMAGED,
                quantity=qty_damaged,
                stock_available_before=item.stock_available,
                stock_available_after=item.stock_available,
                stock_loaned_before=loaned_before,
                stock_loaned_after=item.stock_loaned,
                reference_number=reference_number,
                created_by=user,
                reason=f"Pengembalian kondisi rusak/perlu perbaikan: {reason}"
            )
        if qty_lost > 0:
            StockMovement.objects.create(
                item=item,
                movement_type=StockMovement.MovementType.RETURN_LOST,
                quantity=qty_lost,
                stock_available_before=item.stock_available,
                stock_available_after=item.stock_available,
                stock_loaned_before=loaned_before,
                stock_loaned_after=item.stock_loaned,
                reference_number=reference_number,
                created_by=user,
                reason=f"Pengembalian dilaporkan hilang: {reason}"
            )

        log_action(
            user,
            AuditLog.Action.RETURN,
            'Item',
            item.id,
            {
                'ref': reference_number,
                'usable': qty_usable,
                'damaged': qty_damaged,
                'lost': qty_lost
            }
        )

    @staticmethod
    @transaction.atomic
    def issue_consumable(item_id, quantity, reference_number, user, reason):
        """
        Penyerahan barang habis pakai (CONSUMABLE).
        Stok tersedia langsung berkurang. Tidak ada kewajiban pengembalian.
        """
        item = Item.objects.select_for_update().get(pk=item_id)
        if item.item_type != Item.ItemType.CONSUMABLE:
            raise ValidationError(f"Barang '{item.name}' bukan barang habis pakai (CONSUMABLE).")
        if quantity <= 0:
            raise ValidationError("Jumlah penyerahan harus lebih dari 0.")
        if item.stock_available < quantity:
            raise ValidationError(
                f"Stok '{item.name}' tidak mencukupi (Tersedia: {item.stock_available}, Diminta: {quantity})."
            )

        avail_before = item.stock_available
        item.stock_available -= quantity
        item.save()

        movement = StockMovement.objects.create(
            item=item,
            movement_type=StockMovement.MovementType.CONSUMABLE_ISSUE,
            quantity=quantity,
            stock_available_before=avail_before,
            stock_available_after=item.stock_available,
            stock_loaned_before=0,
            stock_loaned_after=0,
            reference_number=reference_number,
            created_by=user,
            reason=reason
        )

        log_action(
            user,
            AuditLog.Action.CONSUMABLE_ISSUE,
            'Item',
            item.id,
            {'ref': reference_number, 'qty': quantity, 'stock_after': item.stock_available}
        )
        return movement

    @staticmethod
    @transaction.atomic
    def adjust_stock(item_id, new_available, user, reason):
        """
        Penyesuaian stok manual oleh Administrator dengan alasan wajib.
        """
        if new_available < 0:
            raise ValidationError("Stok tidak boleh bernilai negatif.")
        if not reason or not reason.strip():
            raise ValidationError("Alasan penyesuaian stok wajib diisi.")

        item = Item.objects.select_for_update().get(pk=item_id)
        avail_before = item.stock_available
        delta = new_available - avail_before

        item.stock_available = new_available
        item.save()

        movement = StockMovement.objects.create(
            item=item,
            movement_type=StockMovement.MovementType.ADJUSTMENT,
            quantity=abs(delta),
            stock_available_before=avail_before,
            stock_available_after=item.stock_available,
            stock_loaned_before=item.stock_loaned,
            stock_loaned_after=item.stock_loaned,
            reference_number=f"ADJ-{item.code}",
            created_by=user,
            reason=f"Koreksi Saldo: {reason} (Perubahan: {delta:+d})"
        )

        log_action(
            user,
            AuditLog.Action.STOCK_ADJUSTMENT,
            'Item',
            item.id,
            {'before': avail_before, 'after': new_available, 'reason': reason}
        )
        return movement
