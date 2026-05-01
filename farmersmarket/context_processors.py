from django.conf import settings


def theme_config(request):
    ctx = {'THEME_CONFIG': settings.THEME_CONFIG}

    # ── Cart count (item qty total) ──────────────────────────────
    cart = request.session.get('cart', {})
    ctx['cart_count'] = sum(cart.values()) if cart else 0

    # ── Notifications (navbar bell) ──────────────────────────────
    ctx['unread_notif_count'] = 0
    ctx['latest_notifs'] = []

    if request.user.is_authenticated:
        from farmersmarket.models import Notification, Farmer, Client
        try:
            farmer = Farmer.objects.get(user=request.user)
            ctx['unread_notif_count'] = Notification.objects.filter(
                farmer=farmer, is_read=False
            ).count()
            ctx['latest_notifs'] = list(
                Notification.objects.filter(farmer=farmer)
                .order_by('-created_at')[:5]
            )
        except Farmer.DoesNotExist:
            try:
                client = Client.objects.get(user=request.user)
                ctx['unread_notif_count'] = Notification.objects.filter(
                    client=client, is_read=False
                ).count()
                ctx['latest_notifs'] = list(
                    Notification.objects.filter(client=client)
                    .order_by('-created_at')[:5]
                )
            except Client.DoesNotExist:
                pass

    return ctx
