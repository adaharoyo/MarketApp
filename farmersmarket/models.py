from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random
import string

def generate_payment_code():
    return ''.join(
        random.choices(
            string.ascii_uppercase + string.digits,
            k=8
        )
    )


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
    GENDER_OPTIONS = [("M", "Male"), ("F", "Female")]
    ACCOUNT_STATUS = [("Active", "Active"), ("Inactive", "Inactive")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    address = models.CharField(max_length=200, null=True, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER_OPTIONS)
    account_status = models.CharField(max_length=10, choices=ACCOUNT_STATUS, default="Active")

    def __str__(self):
        return self.name


class Product(models.Model):
    CURRENCY_CHOICES = [
        ('UGX', 'UGX - Ugandan Shilling'),
        ('KES', 'KES - Kenyan Shilling'),
        ('TZS', 'TZS - Tanzanian Shilling'),
        ('USD', 'USD - US Dollar'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - British Pound'),
    ]
    UNIT_CHOICES = [
        ('kg', 'kg'), ('g', 'g (grams)'), ('bunch', 'Bunch'),
        ('piece', 'Piece'), ('litre', 'Litre'),
        ('crate', 'Crate'), ('bag', 'Bag'), ('dozen', 'Dozen'),
    ]
    CATEGORY_CHOICES = [
        ('vegetables', '🥬 Vegetables'),
        ('fruits', '🍎 Fruits'),
        ('grains', '🌾 Grains & Cereals'),
        ('dairy', '🥛 Dairy & Eggs'),
        ('herbs', '🌿 Herbs & Spices'),
        ('legumes', '🫘 Legumes & Pulses'),
        ('roots', '🥕 Roots & Tubers'),
        ('other', '📦 Other'),
    ]

    crop_name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', blank=True)
    quantity_available = models.PositiveIntegerField()
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='kg')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='UGX')
    harvest_date = models.DateField(null=True, blank=True, help_text="When was this harvested?")
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='products')
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def freshness_label(self):
        if not self.harvest_date:
            return None
        today = timezone.now().date()
        days = (today - self.harvest_date).days
        if days == 0:
            return ('green', '🟢 Harvested today')
        elif days == 1:
            return ('yellow', '🟡 Yesterday')
        elif days <= 3:
            return ('yellow', f'🟡 {days} days ago')
        else:
            return ('red', f'🔴 {days} days ago')

    @property
    def avg_rating(self):
        ratings = self.ratings.all()
        if not ratings.exists():
            return None
        return round(sum(r.stars for r in ratings) / ratings.count(), 1)

    @property
    def rating_count(self):
        return self.ratings.count()

    def __str__(self):
        return f"{self.crop_name} - {self.farmer.name}"


class ProductRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='ratings')
    stars = models.PositiveSmallIntegerField()  # 1–5
    review = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'client')

    def __str__(self):
        return f"{self.stars}★ – {self.product.crop_name}"


class Courier(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50, blank=True, null=True, help_text="Bike, Car, Van, etc.")
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Courier: {self.name}"


class Order(models.Model):
    ORDER_STATUS = [
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Preparing", "Preparing"),
        ("Ready", "Ready for Pickup/Delivery"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
    ]
    DELIVERY_TYPE = [("Pickup", "Pickup"), ("Delivery", "Delivery")]
    order_date = models.DateTimeField(default=timezone.now)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='orders')
    status = models.CharField(max_length=30, choices=ORDER_STATUS, default="Pending")
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_TYPE, default="Pickup")
    delivery_address = models.CharField(max_length=200, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    courier = models.ForeignKey(Courier, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.id} – {self.client.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}× {self.product.crop_name}"


class Payment(models.Model):
    PAYMENT_OPTIONS = [
        ("Cash", "Cash"),
        ("Mobile Money", "Mobile Money"),
        ("Card", "Card"),
    ]

    PAYMENT_STATUS = [
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Failed", "Failed"),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    # Code farmer sends to client
    payment_code = models.CharField(
        max_length=8,
        unique=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_OPTIONS,
        blank=True,
        null=True
    )

    # Used for mobile money reference number
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="Pending"
    )

    # Message from client after payment
    client_message = models.TextField(
        blank=True,
        null=True
    )

    # Tracks client confirmation
    confirmed_by_client = models.BooleanField(
        default=False
    )

    # Payment code expiry
    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    time_created = models.DateTimeField(
        auto_now_add=True
    )

    time_paid = models.DateTimeField(
        null=True,
        blank=True
    )

    confirmation_time = models.DateTimeField(
        null=True,
        blank=True
    )


    def save(self, *args, **kwargs):
        # Generate unique payment code automatically
        if not self.payment_code:
            code = generate_payment_code()

            while Payment.objects.filter(payment_code=code).exists():
                code = generate_payment_code()

            self.payment_code = code

        super().save(*args, **kwargs)


    def confirm_payment(self):
        """
        Called when client confirms they have paid
        """

        if self.status != "Confirmed":
            self.status = "Confirmed"
            self.confirmed_by_client = True
            self.time_paid = timezone.now()
            self.confirmation_time = timezone.now()
            self.save()


    def is_expired(self):
        """
        Checks if payment code has expired
        """

        if self.expires_at:
            return timezone.now() > self.expires_at

        return False


    def __str__(self):
        return f"{self.payment_code} - Order #{self.order.id}"

class Receipt(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="receipt"
    )
    receipt_number = models.CharField(
        max_length=50,
        unique=True
    )
    issued_date = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"FD-{random.randint(100000,999999)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.receipt_number

class Notification(models.Model):
    RECIPIENT_TYPE = [("Farmer", "Farmer"), ("Client", "Client")]
    NOTIFICATION_TYPE = [
        ("Order", "New Order"),
        ("Payment", "Payment"),
        ("Status", "Order Status Update"),
        ("Product", "Product Availability"),
    ]
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPE)
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    related_order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    email_attempts = models.PositiveIntegerField(default=0)
    email_last_error = models.TextField(blank=True)

    def __str__(self):
        return f"{self.notification_type} – {self.created_at}"

