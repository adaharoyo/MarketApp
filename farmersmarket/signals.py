from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Payment, Receipt, Notification


@receiver(post_save, sender=Payment)
def handle_payment(sender, instance, created, **kwargs):
    if not created or not instance.is_successful:
        return

    order = instance.order

    # create receipt if not exists
    if not hasattr(order, "receipt"):
        Receipt.objects.create(order=order)

    # update order
    order.status = "Paid"
    order.completed_at = timezone.now()
    order.save()

    farmer = order.items.first().product.farmer

    # notify farmer
    Notification.objects.create(
        recipient_type="Farmer",
        farmer=farmer,
        notification_type="Payment",
        message=f"Payment received for Order #{order.id}. Receipt generated.",
        related_order=order
    )
