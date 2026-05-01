from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Farmer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    address = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Farm(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Client(models.Model):
    GENDER_OPTIONS = [
        ("M", "Male"),
        ("F", "Female")
    ]
    ACCOUNT_STATUS = [("Active", "Active"),
                      ("Inactive", "Inactive")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    address = models.CharField(max_length=200, null=True, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER_OPTIONS)
    account_status = models.CharField(max_length=10, choices=ACCOUNT_STATUS, default="Active")

    def __str__(self):
        return self.name


class Product(models.Model):
    crop_name = models.CharField(max_length=100)
    quantity_available = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='products')
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.crop_name} - {self.farmer.name}"


class Order(models.Model):
    ORDER_STATUS = [
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Paid", "Paid"),
        ("Preparing", "Preparing"),
        ("Ready", "Ready for Pickup/Delivery"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled")
    ]
    DELIVERY_TYPE = [
        ("Pickup", "Pickup"),
        ("Delivery", "Delivery")
    ]
    order_date = models.DateTimeField(default=timezone.now)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=30, choices=ORDER_STATUS, default="Pending")
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_TYPE, default="Pickup")
    delivery_address = models.CharField(max_length=200, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.client.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product.crop_name}"


class Payment(models.Model):
    PAYMENT_OPTIONS = [
        ("Cash", "Cash"),
        ("Mobile Money", "Mobile Money"),
        ("Card", "Card")
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    time_paid = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_OPTIONS)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    is_successful = models.BooleanField(default=True)

    def __str__(self):
        return f"Payment for Order #{self.order.id}"


class Notification(models.Model):
    RECIPIENT_TYPE = [
        ("Farmer", "Farmer"),
        ("Client", "Client")
    ]
    NOTIFICATION_TYPE = [
        ("Order", "New Order"),
        ("Payment", "Payment"),
        ("Status", "Order Status Update"),
        ("Product", "Product Availability")
    ]
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPE)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    related_order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.notification_type} - {self.created_at}"
           