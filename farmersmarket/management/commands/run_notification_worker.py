import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from farmersmarket.models import Notification


class Command(BaseCommand):
    help = "Background polling worker that sends queued notification emails."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=8,
            help="Polling interval in seconds between queue checks.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Maximum queued notifications processed per polling loop.",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process one batch and exit.",
        )

    def _recipient_email(self, notification):
        if notification.client and notification.client.user and notification.client.user.email:
            return notification.client.user.email
        if notification.farmer and notification.farmer.user and notification.farmer.user.email:
            return notification.farmer.user.email
        return None

    def _subject_for(self, notification):
        order_part = ""
        if notification.related_order_id:
            order_part = f" (Order #{notification.related_order_id})"

        if notification.notification_type == "Payment":
            return f"Payment Receipt{order_part}"
        if notification.notification_type == "Status":
            return f"Order Status Update{order_part}"
        if notification.notification_type == "Order":
            return f"New Order Alert{order_part}"
        return f"Market Hub Notification{order_part}"

    def _email_body_for(self, notification):
        order_line = f"Order: #{notification.related_order_id}\n" if notification.related_order_id else ""
        sent_at = timezone.localtime(notification.created_at).strftime("%Y-%m-%d %H:%M:%S")
        return (
            "Hello,\n\n"
            f"{notification.message}\n\n"
            f"{order_line}"
            f"Notification time: {sent_at}\n\n"
            "This email was sent by Market Hub notifications service."
        )

    def _process_queue_batch(self, batch_size):
        pending = (
            Notification.objects.filter(email_sent=False)
            .filter(Q(client__isnull=False) | Q(farmer__isnull=False))
            .order_by("created_at")[:batch_size]
        )

        processed = 0
        for notification in pending:
            recipient_email = self._recipient_email(notification)
            notification.email_attempts += 1

            if not recipient_email:
                notification.email_sent = True
                notification.email_sent_at = timezone.now()
                notification.email_last_error = "No recipient email configured"
                notification.save(update_fields=["email_attempts", "email_sent", "email_sent_at", "email_last_error"])
                processed += 1
                continue

            try:
                send_mail(
                    subject=self._subject_for(notification),
                    message=self._email_body_for(notification),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )
                notification.email_sent = True
                notification.email_sent_at = timezone.now()
                notification.email_last_error = ""
                notification.save(update_fields=["email_attempts", "email_sent", "email_sent_at", "email_last_error"])
                processed += 1
            except Exception as exc:
                notification.email_last_error = str(exc)
                notification.save(update_fields=["email_attempts", "email_last_error"])
                self.stderr.write(
                    self.style.WARNING(
                        f"Failed to send notification #{notification.id}: {exc}"
                    )
                )

        return processed

    def handle(self, *args, **options):
        interval = max(2, options["interval"])
        batch_size = max(1, options["batch_size"])
        run_once = options["once"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Notification worker started (interval={interval}s, batch={batch_size}, once={run_once})"
            )
        )

        while True:
            processed = self._process_queue_batch(batch_size=batch_size)
            if processed:
                self.stdout.write(self.style.SUCCESS(f"Processed {processed} queued notification(s)."))

            if run_once:
                break

            time.sleep(interval)
