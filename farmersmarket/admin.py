from django.contrib import admin
from farmersmarket.models import Farmer, Farm, Client, Product, Order, OrderItem, Payment, Notification

@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact', 'address', 'user')

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'farmer')

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact', 'account_status', 'user')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('crop_name', 'price', 'quantity_available', 'farmer', 'is_available')
    list_filter = ('farmer', 'is_available')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'status', 'delivery_type', 'total_amount', 'order_date')
    list_filter = ('status', 'delivery_type', 'order_date')

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price_at_purchase')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'amount', 'payment_method', 'time_paid', 'is_successful')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('notification_type', 'recipient_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'recipient_type', 'is_read')
