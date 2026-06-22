from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import JsonResponse
import datetime, random
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO

from django.core.paginator import Paginator
from farmersmarket.models import (
    Farmer, Client, Product, ProductRating,
    Order, OrderItem, Payment, Notification,
)
from farmersmarket.forms import (
    FarmForm, FarmerForm, ClientForm, ProductForm, PaymentForm, OrderForm,
)


# ─── HELPERS ────────────────────────────────────────────────────────────────
def _get_cart(request):
    return request.session.get('cart', {})

def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True

def _cart_grouped(request):
    """Return cart items grouped by farmer, plus grand total."""
    cart = _get_cart(request)
    farmers_map = {}
    grand_total = 0
    for pid, qty in cart.items():
        try:
            product = Product.objects.get(pk=pid)
            subtotal = product.price * qty
            grand_total += subtotal
            fname = product.farmer.name
            if fname not in farmers_map:
                farmers_map[fname] = {'farmer': product.farmer, 'items': []}
            farmers_map[fname]['items'].append({
                'product': product, 'qty': qty, 'subtotal': subtotal,
            })
        except Product.DoesNotExist:
            pass
    return list(farmers_map.values()), grand_total


def _queue_notification(recipient_type, notification_type, message, related_order=None, farmer=None, client=None):
    return Notification.objects.create(
        recipient_type=recipient_type,
        farmer=farmer,
        client=client,
        notification_type=notification_type,
        message=message,
        related_order=related_order,
    )


# ─── HOME ───────────────────────────────────────────────────────────────────
def home(request):
    products = Product.objects.filter(is_available=True).order_by('-created_at')[:4]
    return render(request, 'home.html', {'products': products})


# ─── AUTH ────────────────────────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def register_view(request):
    if request.method == 'POST':
        username  = request.POST.get('username')
        email     = request.POST.get('email')
        password  = request.POST.get('password')
        name      = request.POST.get('name')
        contact   = request.POST.get('contact')
        address   = request.POST.get('address')
        user_type = request.POST.get('user_type')
        gender    = request.POST.get('gender', 'M')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'register.html')

        user = User.objects.create_user(username=username, email=email, password=password)
        if user_type == 'farmer':
            Farmer.objects.create(user=user, name=name, contact=contact, address=address)
        else:
            Client.objects.create(
                user=user, name=name, contact=contact,
                address=address, gender=gender, account_status='Active',
            )
        login(request, user)
        return redirect('dashboard')
    return render(request, 'register.html')


def logout_view(request):
    request.session.pop('cart', None)
    logout(request)
    return redirect('home')


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    # Farmer
    try:
        farmer   = Farmer.objects.get(user=request.user)
        # Only latest 4 products for dashboard
        products = Product.objects.filter(farmer=farmer).order_by('-created_at')[:5]
        
        # Only latest 4 orders for dashboard
        orders = (Order.objects.filter(items__product__farmer=farmer)
                    .distinct().order_by('-order_date'))[:4]

        notifs   = Notification.objects.filter(farmer=farmer, is_read=False).order_by('-created_at')[:5]

        # Quick stats - calculate farmer's actual earnings, not full order amount
        today = timezone.now().date()
        today_orders = (Order.objects.filter(items__product__farmer=farmer, order_date__date=today)
                        .distinct())
        # Calculate farmer's earnings only from their items
        today_revenue = 0
        for order in today_orders:
            if order.status == 'Delivered':
                farmer_items = order.items.filter(product__farmer=farmer)
                today_revenue += sum(item.price_at_purchase * item.quantity for item in farmer_items)
        
        low_stock = Product.objects.filter(farmer=farmer, quantity_available__lte=5, is_available=True)
        currency = farmer.products.first().currency if farmer.products.exists() else 'UGX'

        # Prepare orders with earnings for display
        orders_with_earnings = []
        for order in orders:
            farmer_items = order.items.filter(product__farmer=farmer)
            farmer_earnings = sum(item.price_at_purchase * item.quantity for item in farmer_items)
            orders_with_earnings.append({
                'order': order,
                'farmer_earnings': farmer_earnings,
            })

        return render(request, 'farmer_dashboard.html', {
            'farmer': farmer, 'products': products, 'orders': orders,
            'orders_with_earnings': orders_with_earnings,
            'notifications': notifs, 'today_count': today_orders.count(),
            'today_revenue': today_revenue, 'low_stock': low_stock,
            'currency': currency,
        })
    except Farmer.DoesNotExist:
        pass

    # Client
    try:
        client   = Client.objects.get(user=request.user)
        # Only latest 4 products for summary
        products = Product.objects.filter(is_available=True).order_by('-created_at')[:4]
        
        # Only latest 4 orders for summary
        orders = Order.objects.filter(client=client).order_by('-order_date')[:4]

        notifs   = Notification.objects.filter(client=client, is_read=False).order_by('-created_at')[:5]
        return render(request, 'client_dashboard.html', {
            'client': client, 'products': products,
            'orders': orders, 'notifications': notifs,
        })
    except Client.DoesNotExist:
        pass

    return redirect('marketplace')


# ─── DEDICATED LIST PAGES ───────────────────────────────────────────────────

def farmer_products_view(request):
    if not request.user.is_authenticated: return redirect('login')
    farmer = get_object_or_404(Farmer, user=request.user)
    products_qs = Product.objects.filter(farmer=farmer).order_by('-created_at')
    paginator = Paginator(products_qs, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    currency = farmer.products.first().currency if farmer.products.exists() else 'UGX'
    return render(request, 'farmersmarket/farmer_products_list.html', {
        'farmer': farmer, 'products': products, 'currency': currency, 'is_paginated': products.has_other_pages()
    })

def farmer_orders_view(request):
    if not request.user.is_authenticated: return redirect('login')
    farmer = get_object_or_404(Farmer, user=request.user)
    orders_qs = Order.objects.filter(items__product__farmer=farmer).distinct().order_by('-order_date')
    paginator = Paginator(orders_qs, 15)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    # Calculate farmer's earnings for each order (not total order amount)
    orders_with_earnings = []
    for order in orders:
        farmer_items = order.items.filter(product__farmer=farmer)
        farmer_earnings = sum(item.price_at_purchase * item.quantity for item in farmer_items)
        orders_with_earnings.append({
            'order': order,
            'farmer_earnings': farmer_earnings,
        })
    
    currency = farmer.products.first().currency if farmer.products.exists() else 'UGX'
    return render(request, 'farmersmarket/farmer_orders_list.html', {
        'farmer': farmer, 'orders_with_earnings': orders_with_earnings, 'orders': orders, 'currency': currency, 'is_paginated': orders.has_other_pages()
    })

def client_orders_view(request):
    if not request.user.is_authenticated: return redirect('login')
    client = get_object_or_404(Client, user=request.user)
    orders_qs = Order.objects.filter(client=client).order_by('-order_date')
    paginator = Paginator(orders_qs, 15)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    return render(request, 'farmersmarket/client_orders_list.html', {
        'client': client, 'orders': orders, 'is_paginated': orders.has_other_pages()
    })

    return redirect('home')


# ─── MARKETPLACE ─────────────────────────────────────────────────────────────
def marketplace_view(request):
    q         = request.GET.get('q', '').strip()
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    farmer_id = request.GET.get('farmer', '')
    category  = request.GET.get('category', '')
    available_only = request.GET.get('available_only', '')

    products = Product.objects.filter(is_available=True)

    if q:
        products = products.filter(Q(crop_name__icontains=q) | Q(description__icontains=q))
    if min_price:
        try: products = products.filter(price__gte=float(min_price))
        except ValueError: pass
    if max_price:
        try: products = products.filter(price__lte=float(max_price))
        except ValueError: pass
    if farmer_id:
        products = products.filter(farmer_id=farmer_id)
    if category:
        products = products.filter(category=category)

    products_qs = products.order_by('-created_at')
    
    # Pagination for marketplace
    paginator = Paginator(products_qs, 16) # 16 products per page
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)

    farmers  = Farmer.objects.all()

    return render(request, 'marketplace.html', {
        'products': products, 'farmers': farmers,
        'q': q, 'min_price': min_price, 'max_price': max_price,
        'farmer_id': farmer_id, 'category': category,
        'category_choices': Product.CATEGORY_CHOICES,
        'is_paginated': products.has_other_pages(),
    })


# ─── PRODUCT DETAIL ──────────────────────────────────────────────────────────
def product_detail_view(request, product_id):
    product    = get_object_or_404(Product, pk=product_id, is_available=True)
    ratings    = product.ratings.all().order_by('-created_at')
    user_rating = None
    if request.user.is_authenticated:
        try:
            client = Client.objects.get(user=request.user)
            user_rating = ProductRating.objects.filter(product=product, client=client).first()
        except Client.DoesNotExist:
            pass
    return render(request, 'product_detail.html', {
        'product': product, 'ratings': ratings, 'user_rating': user_rating,
    })


# ─── RATINGS ─────────────────────────────────────────────────────────────────
@require_POST
def rate_product(request, product_id):
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to rate.')
        return redirect('login')
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        messages.error(request, 'Only buyers can rate products.')
        return redirect('product_detail', product_id=product_id)

    product = get_object_or_404(Product, pk=product_id)
    stars   = int(request.POST.get('stars', 0))
    review  = request.POST.get('review', '').strip()

    if not 1 <= stars <= 5:
        messages.error(request, 'Please select 1–5 stars.')
        return redirect('product_detail', product_id=product_id)

    ProductRating.objects.update_or_create(
        product=product, client=client,
        defaults={'stars': stars, 'review': review},
    )
    messages.success(request, f'Thanks for rating {product.crop_name}!')
    return redirect('product_detail', product_id=product_id)


# ─── CART ─────────────────────────────────────────────────────────────────────
def cart_view(request):
    farmers_data, total = _cart_grouped(request)
    return render(request, 'cart.html', {
        'farmers_data': farmers_data, 'total': total,
    })


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_available=True)
    qty     = int(request.POST.get('quantity', 1))
    cart    = _get_cart(request)
    key     = str(product_id)
    new_qty = cart.get(key, 0) + qty

    if new_qty > product.quantity_available:
        messages.error(request, f'Only {product.quantity_available} {product.unit} available.')
    else:
        cart[key] = new_qty
        _save_cart(request, cart)
        messages.success(request, f'Added {qty} {product.unit} of {product.crop_name} to cart.')

    return redirect(request.POST.get('next', 'marketplace'))


@require_POST
def remove_from_cart(request, product_id):
    cart = _get_cart(request)
    cart.pop(str(product_id), None)
    _save_cart(request, cart)
    return redirect('cart')


@require_POST
def update_cart(request, product_id):
    qty  = int(request.POST.get('quantity', 1))
    cart = _get_cart(request)
    key  = str(product_id)
    if qty <= 0:
        cart.pop(key, None)
    else:
        product = get_object_or_404(Product, pk=product_id)
        if qty > product.quantity_available:
            messages.error(request, f'Only {product.quantity_available} available.')
            return redirect('cart')
        cart[key] = qty
    _save_cart(request, cart)
    return redirect('cart')


# ─── CHECKOUT ─────────────────────────────────────────────────────────────────
def checkout_view(request):
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to checkout.')
        return redirect('login')
    try:
        client = Client.objects.get(user=request.user)
    except Client.DoesNotExist:
        messages.error(request, 'Only buyers can place orders.')
        return redirect('dashboard')

    cart = _get_cart(request)
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('marketplace')

    farmers_data, total = _cart_grouped(request)

    if request.method == 'POST':
        delivery_type    = request.POST.get('delivery_type', 'Pickup')
        delivery_address = request.POST.get('delivery_address', '')
        notes            = request.POST.get('notes', '')

        # Create ONE ORDER PER FARMER to ensure tenant isolation
        # Each farmer can independently accept/decline their items
        order_ids = []
        for group in farmers_data:
            farmer = group['farmer']
            farmer_total = sum(item['subtotal'] for item in group['items'])
            
            # Create separate order for this farmer
            order = Order.objects.create(
                client=client, delivery_type=delivery_type,
                delivery_address=delivery_address,
                total_amount=farmer_total, notes=notes, status='Pending',
            )
            order_ids.append(order.id)
            
            for item in group['items']:
                product = item['product']
                OrderItem.objects.create(
                    order=order, product=product,
                    quantity=item['qty'], price_at_purchase=product.price,
                )
                product.quantity_available -= item['qty']
                if product.quantity_available <= 0:
                    product.is_available = False
                product.save()
            
            # Create mock payment for this order
            Payment.objects.create(
                order=order,
                amount=farmer_total,
                payment_method='Mobile Money', # Mock default
                transaction_id=f'MOCK-{random.randint(10000, 99999)}',
                is_successful=True
            )

            # Queue a client receipt notification (processed by background email worker)
            _queue_notification(
                recipient_type='Client',
                client=client,
                notification_type='Payment',
                message=(
                    f'Payment receipt for order #{order.id}: '
                    f'{order.total_amount} via Mobile Money '
                    f'(Ref: {order.payments.latest("time_paid").transaction_id}).'
                ),
                related_order=order,
            )
            
            # Notify farmer
            _queue_notification(
                recipient_type='Farmer',
                farmer=farmer,
                notification_type='Order',
                message=f'New order #{order.id}: {len(group["items"])} item(s) from {client.name}.',
                related_order=order,
            )

        _save_cart(request, {})
        messages.success(request, f'{len(order_ids)} order(s) placed and paid via Mock Payment!')
        # Redirect to first order (can update to show all orders)
        return redirect('order_detail', order_id=order_ids[0] if order_ids else 1)

    return render(request, 'checkout.html', {
        'farmers_data': farmers_data, 'total': total, 'client': client,
    })


# ─── ORDER DETAIL ─────────────────────────────────────────────────────────────
def order_detail_view(request, order_id):
    if not request.user.is_authenticated:
        return redirect('login')
    order = get_object_or_404(Order, pk=order_id)

    is_client = (
        hasattr(request.user, 'client') and
        order.client.user == request.user
    )
    is_farmer = order.items.filter(product__farmer__user=request.user).exists()

    if not (is_client or is_farmer):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # For farmers: filter items to only show their own products
    farmer_items = order.items.all()
    if is_farmer and not is_client:
        try:
            farmer = Farmer.objects.get(user=request.user)
            farmer_items = order.items.filter(product__farmer=farmer)
        except Farmer.DoesNotExist:
            pass

    return render(request, 'order_detail.html', {
        'order': order,
        'farmer_items': farmer_items,
        'is_client': is_client,
        'is_farmer': is_farmer,
    })


# ─── ORDER STATUS (Farmers) ───────────────────────────────────────────────────
VALID_TRANSITIONS = {
    'Pending':   ['Confirmed', 'Cancelled'],
    'Confirmed': ['Preparing', 'Cancelled'],
    'Preparing': ['Ready'],
    'Ready':     ['Delivered'],
}

@require_POST
def update_order_status(request, order_id):
    if not request.user.is_authenticated:
        return redirect('login')
    order  = get_object_or_404(Order, pk=order_id)
    farmer = get_object_or_404(Farmer, user=request.user)

    if not order.items.filter(product__farmer=farmer).exists():
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    new_status = request.POST.get('status')
    allowed    = VALID_TRANSITIONS.get(order.status, [])

    if new_status in allowed:
        if new_status == 'Cancelled':
            for item in order.items.all():
                item.product.quantity_available += item.quantity
                if item.product.quantity_available > 0:
                    item.product.is_available = True
                item.product.save()

        order.status = new_status
        if new_status == 'Delivered':
            order.delivered_at = timezone.now()
        order.save()

        if new_status == 'Ready':
            status_message = f'Seller is delivering your order #{order.id}. It is now ready for dispatch.'
        elif new_status == 'Delivered':
            status_message = f'Your order #{order.id} has been delivered. Enjoy your produce!'
        else:
            status_message = f'Your order #{order.id} is now: {new_status}.'

        _queue_notification(
            recipient_type='Client',
            client=order.client,
            notification_type='Status',
            message=status_message,
            related_order=order,
        )
        messages.success(request, f'Order #{order.id} → {new_status}.')
    else:
        messages.error(request, f'Cannot change from {order.status} to {new_status}.')

    return redirect('dashboard')


# ─── FARMER EARNINGS ─────────────────────────────────────────────────────────
def farmer_earnings_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    farmer = get_object_or_404(Farmer, user=request.user)

    today      = timezone.now().date()
    week_start = today - datetime.timedelta(days=7)
    month_start= today - datetime.timedelta(days=30)

    def revenue_for(qs):
        """Calculate farmer's revenue (not total order amount)"""
        total = 0
        for order in qs:
            if order.status == 'Delivered':
                farmer_items = order.items.filter(product__farmer=farmer)
                total += sum(item.price_at_purchase * item.quantity for item in farmer_items)
        return total

    all_orders   = Order.objects.filter(items__product__farmer=farmer).distinct()
    week_orders  = all_orders.filter(order_date__date__gte=week_start)
    month_orders = all_orders.filter(order_date__date__gte=month_start)
    today_orders = all_orders.filter(order_date__date=today)

    best_products = (
        OrderItem.objects.filter(product__farmer=farmer, order__status='Delivered')
        .values('product__crop_name', 'product__currency')
        .annotate(total_qty=Sum('quantity'), total_rev=Sum('price_at_purchase'))
        .order_by('-total_qty')[:6]
    )
    # Only latest 5 delivered orders (Real Sales)
    recent_orders = all_orders.filter(status='Delivered').order_by('-order_date')[:5]
    farmer_currency = farmer.products.first().currency if farmer.products.exists() else 'UGX'

    return render(request, 'farmer_earnings.html', {
        'farmer':         farmer,
        'total_revenue':  revenue_for(all_orders),
        'month_revenue':  revenue_for(month_orders),
        'week_revenue':   revenue_for(week_orders),
        'today_revenue':  revenue_for(today_orders),
        'today_count':    today_orders.filter(status='Delivered').count(),
        'week_count':     week_orders.filter(status='Delivered').count(),
        'total_orders':   all_orders.filter(status='Delivered').count(),
        'best_products':  best_products,
        'recent_orders':  recent_orders,
        'currency':       farmer_currency,
        'revenue_rows': [
            ('All Time Revenue',  revenue_for(all_orders)),
            ('This Month',        revenue_for(month_orders)),
            ('This Week',         revenue_for(week_orders)),
            ('Today',             revenue_for(today_orders)),
        ],
    })


def farmer_sales_history_view(request):
    if not request.user.is_authenticated: return redirect('login')
    farmer = get_object_or_404(Farmer, user=request.user)
    sales_qs = Order.objects.filter(items__product__farmer=farmer, status='Delivered').distinct().order_by('-order_date')
    paginator = Paginator(sales_qs, 20)
    page = request.GET.get('page')
    sales = paginator.get_page(page)
    currency = farmer.products.first().currency if farmer.products.exists() else 'UGX'
    return render(request, 'farmersmarket/farmer_sales_list.html', {
        'farmer': farmer, 'sales': sales, 'currency': currency, 'is_paginated': sales.has_other_pages()
    })


# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────
@require_POST
def mark_notifications_read(request):
    if not request.user.is_authenticated:
        return redirect('login')
    try:
        farmer = Farmer.objects.get(user=request.user)
        Notification.objects.filter(farmer=farmer, is_read=False).update(is_read=True)
    except Farmer.DoesNotExist:
        try:
            client = Client.objects.get(user=request.user)
            Notification.objects.filter(client=client, is_read=False).update(is_read=True)
        except Client.DoesNotExist:
            pass
    return redirect('dashboard')


def notifications_poll(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Unauthorized'}, status=401)

    notif_qs = Notification.objects.none()
    try:
        farmer = Farmer.objects.get(user=request.user)
        notif_qs = Notification.objects.filter(farmer=farmer)
    except Farmer.DoesNotExist:
        try:
            client = Client.objects.get(user=request.user)
            notif_qs = Notification.objects.filter(client=client)
        except Client.DoesNotExist:
            pass

    unread_count = notif_qs.filter(is_read=False).count()
    latest = notif_qs.order_by('-created_at')[:5]
    payload = []
    for n in latest:
        payload.append({
            'id': n.id,
            'type': n.notification_type,
            'message': n.message,
            'is_read': n.is_read,
            'created_at': timezone.localtime(n.created_at).isoformat(),
            'order_id': n.related_order_id,
        })

    return JsonResponse({
        'unread_count': unread_count,
        'notifications': payload,
    })


def order_status_poll(request, order_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Unauthorized'}, status=401)

    order = get_object_or_404(Order, pk=order_id)
    is_client = (
        hasattr(request.user, 'client') and
        order.client.user == request.user
    )
    is_farmer = order.items.filter(product__farmer__user=request.user).exists()

    if not (is_client or is_farmer):
        return JsonResponse({'detail': 'Forbidden'}, status=403)

    return JsonResponse({
        'order_id': order.id,
        'status': order.status,
        'delivered_at': timezone.localtime(order.delivered_at).isoformat() if order.delivered_at else None,
    })


# ─── ADD PRODUCT (FARMER) ─────────────────────────────────────────────────────
def add_product_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    farmer = get_object_or_404(Farmer, user=request.user)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product        = form.save(commit=False)
            product.farmer = farmer
            product.save()
            messages.success(request, f'{product.crop_name} added.')
            return redirect('dashboard')
    else:
        form = ProductForm()
    return render(request, 'generic_form.html', {'form': form, 'title': 'Add Product'})



# ─── EDIT PRODUCT (FARMER) ────────────────────────────────────────────────────
def edit_product_view(request, product_id):
    if not request.user.is_authenticated:
        return redirect('login')
    farmer = get_object_or_404(Farmer, user=request.user)
    product = get_object_or_404(Product, pk=product_id, farmer=farmer)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'{product.crop_name} updated.')
            return redirect('dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'generic_form.html', {'form': form, 'title': f'Edit {product.crop_name}'})


# ─── DELETE PRODUCT (FARMER) ──────────────────────────────────────────────────
@require_POST
def delete_product_view(request, product_id):
    if not request.user.is_authenticated:
        return redirect('login')
    farmer = get_object_or_404(Farmer, user=request.user)
    product = get_object_or_404(Product, pk=product_id, farmer=farmer)
    name = product.crop_name
    product.delete()
    messages.success(request, f'{name} has been deleted.')
    return redirect('dashboard')

# ─── CANCEL ORDER (CLIENT) ────────────────────────────────────────────────────
@require_POST
def cancel_order_view(request, order_id):
    if not request.user.is_authenticated:
        return redirect('login')
    client = get_object_or_404(Client, user=request.user)
    order  = get_object_or_404(Order, pk=order_id, client=client)

    if order.status == 'Pending':
        # Restore stock for THIS ORDER ONLY (not other orders from other farms)
        for item in order.items.all():
            item.product.quantity_available += item.quantity
            if item.product.quantity_available > 0:
                item.product.is_available = True
            item.product.save()

        order.status = 'Cancelled'
        order.save()

        # Notify ONLY the farmer(s) for THIS order
        farmer = order.items.first().product.farmer
        Notification.objects.create(
            recipient_type='Farmer', farmer=farmer,
            notification_type='Status',
            message=f'Order #{order.id} was cancelled by the buyer.',
            related_order=order,
        )

        messages.success(request, f'Order #{order.id} cancelled successfully.')
    else:
        messages.error(request, f'Order #{order.id} cannot be cancelled in its current state.')

    return redirect('dashboard')


# ─── ADMIN CRUD STUBS ─────────────────────────────────────────────────────────
def _simple_form_view(request, FormClass, title):
    form = FormClass(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('dashboard')
    return render(request, 'generic_form.html', {'form': form, 'title': title})

def add_farm_view(request):    return _simple_form_view(request, FarmForm, 'Add Farm')
def add_order_view(request):   return _simple_form_view(request, OrderForm, 'Add Order')
def add_farmer_view(request):  return _simple_form_view(request, FarmerForm, 'Add Farmer')
def add_payment_view(request): return _simple_form_view(request, PaymentForm, 'Add Payment')
def add_client_view(request):  return _simple_form_view(request, ClientForm, 'Add Client')

# ─── FARMER REPORT ─────────────────────────────────────────────

def farmer_report_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    farmer = get_object_or_404(Farmer, user=request.user)

    orders = Order.objects.filter(
        items__product__farmer=farmer
    ).distinct().order_by('-order_date')


    delivered_orders = orders.filter(status="Delivered")

    total_earnings = 0
    sales = []   # <-- ADD THIS


    for order in delivered_orders:

        farmer_items = order.items.filter(
            product__farmer=farmer
        )

        for item in farmer_items:

            subtotal = item.price_at_purchase * item.quantity

            total_earnings += subtotal

            sales.append({
                'order': order,
                'product': item.product,
                'quantity': item.quantity,
                'subtotal': subtotal,
            })


    customers = Client.objects.filter(
        orders__items__product__farmer=farmer
    ).distinct()


    return render(request, 'farmersmarket/farmer_report.html', {
        'farmer': farmer,
        'sales': sales,   # <-- ADD THIS
        'total_earnings': total_earnings,
        'customers': customers,
        'customer_count': customers.count(),
    })


def farmer_report_pdf(request):

    if not request.user.is_authenticated:
        return redirect('login')

    farmer = get_object_or_404(Farmer, user=request.user)

    orders = Order.objects.filter(
        items__product__farmer=farmer
    ).distinct()


    delivered_orders = orders.filter(status="Delivered")

    earnings = 0

    for order in delivered_orders:

        items = order.items.filter(
            product__farmer=farmer
        )

        earnings += sum(
            item.price_at_purchase * item.quantity
            for item in items
        )


    buffer = BytesIO()

    pdf = canvas.Canvas(buffer)


    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(
        50,
        800,
        "Farmer Sales Report"
    )


    pdf.setFont("Helvetica", 12)

    pdf.drawString(
        50,
        770,
        f"Farmer: {farmer.name}"
    )

    pdf.drawString(
        50,
        750,
        f"Total Orders: {orders.count()}"
    )

    pdf.drawString(
        50,
        730,
        f"Delivered Orders: {delivered_orders.count()}"
    )

    pdf.drawString(
        50,
        710,
        f"Total Earnings: {earnings}"
    )


    y = 670

    pdf.setFont("Helvetica-Bold", 12)

    pdf.drawString(50,y,"Order ID")
    pdf.drawString(130,y,"Customer")
    pdf.drawString(250,y,"Status")


    y -= 20

    pdf.setFont("Helvetica",10)


    for order in orders:

        pdf.drawString(
            50,
            y,
            str(order.id)
        )

        pdf.drawString(
            130,
            y,
            order.client.name[:15]
        )

        pdf.drawString(
            250,
            y,
            order.status
        )

        y -= 20

        if y < 50:
            pdf.showPage()
            y = 800


    pdf.save()


    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        'attachment; filename="farmer_report.pdf"'
    )


    return response