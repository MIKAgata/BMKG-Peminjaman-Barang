from django.contrib import admin
from .models import Category, Location, Item, AssetUnit, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'item_type', 'stock_available', 'stock_loaned', 'minimum_stock', 'is_active')
    list_filter = ('item_type', 'category', 'is_active')
    search_fields = ('code', 'name', 'brand')


@admin.register(AssetUnit)
class AssetUnitAdmin(admin.ModelAdmin):
    list_display = ('asset_code', 'item', 'serial_number', 'condition', 'status', 'location')
    list_filter = ('condition', 'status')
    search_fields = ('asset_code', 'serial_number', 'item__name')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'item', 'movement_type', 'quantity', 'stock_available_after', 'reference_number', 'created_by')
    list_filter = ('movement_type',)
    search_fields = ('item__name', 'item__code', 'reference_number', 'reason')
    readonly_fields = ('item', 'movement_type', 'quantity', 'stock_available_before', 'stock_available_after', 'stock_loaned_before', 'stock_loaned_after', 'reference_number', 'created_by', 'reason', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
