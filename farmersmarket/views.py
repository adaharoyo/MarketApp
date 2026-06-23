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
    Order, OrderItem, Payment, Notification, Receipt,
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
        products = Product.objects.filter(farmer=farmer).order_by('-created_at')[:5]
        orders = (Order.objects.filter(items__product__farmer=farmer)
                    .distinct().order_by('-order_date'))[:4]
        notifs   = Notification.objects.filter(farmer=farmer, is_read=False).order_by('-created_at')[:5]

        today = timezone.now().date()
        today_orders = (Order.objects.filter(items__product__farmer=farmer, order_date__date=today)
                        .distinct())
        today_revenue = 0
        for order in today_orders:
            if order.status == 'Delivered':
                farmer_items = order.items.filter(product__farmer=farmer)
                today_revenue += sum(item.price_at_purchase * item.quantity for item in farmer_items)
        
        low_stock = Product.objects.filter(farmer=farmer, quantity_available__lte=5, is_available=True)
        currency = farmer.products.first().currency if farmer.products.exists() else 'UGX'

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
        products = Product.objects.filter(is_available=True).order_by('-created_at')[:4]
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
    return render(request, 'client_orders_list.html', {
        'client': client, 'orders': orders, 'is_paginated': orders.has_other_pages()
    })


# ─── MARKETPLACE ─────────────────────────────────────────────────────────────
def marketplace_view(request):
    q         = request.GET.get('q', '').strip()
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    farmer_id = request.GET.get('farmer', '')
    category  = request.GET.get('category', '')

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
    
    paginator = Paginator(products_qs, 16)
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

        order_ids = []
        for group in farmers_data:
            farmer = group['farmer']
            farmer_total = sum(item['subtotal'] for item in group['items'])
            
            order = Order.objects.create(
                client=client, 
                delivery_type=delivery_type,
                delivery_address=delivery_address,
                total_amount=farmer_total, 
                notes=notes, 
                status='Pending',
            )
            order_ids.append(order.id)
            
            for item in group['items']:
                product = item['product']
                OrderItem.objects.create(
                    order=order, 
                    product=product,
                    quantity=item['qty'], 
                    price_at_purchase=product.price,
                )
                product.quantity_available -= item['qty']
                if product.quantity_available <= 0:
                    product.is_available = False
                product.save()
            
            # Create the structural Payment model record containing the random 8-character verification code
            Payment.objects.create(
                order=order,
                amount=farmer_total,
                payment_method='Mobile Money',
                transaction_id=f'MOCK-{random.randint(10000, 99999)}',
                status='Pending',  # Kept pending until client submits the verification code
                confirmed_by_client=False,
            )

            Receipt.objects.create(order=order)

            _queue_notification(
                recipient_type='Client',
                client=client,
                notification_type='Payment',
                message=f'Order #{order.id} placed. Pay and use validation token upon arrival.',
                related_order=order,
            )

        _save_cart(request, {})
        messages.success(request, f'{len(order_ids)} order(s) successfully initialized!')
        return redirect('order_detail', order_id=order_ids[0] if order_ids else 1)

    return render(request, 'checkout.html', {
        'farmers_data': farmers_data, 
        'total': total, 
        'client': client,
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
        order.status = new_status
        order.save()
        messages.success(request, f"Order status updated to {new_status}.")
    else:
        messages.error(request, "Invalid status transition.")
        
    return redirect('order_detail', order_id=order.id)


# ─── CONFIRM RECEIVED (Client Handshake Verification View) ───────────────────
@require_POST
def confirm_received(request, order_id):
    if not request.user.is_authenticated:
        return redirect('login')
        
    order = get_object_or_404(Order, pk=order_id)
    entered_code = request.POST.get('payment_code', '').strip()
    
    # Grab the transaction payment model link
    payment = order.payments.first()
    
    # Match strings
    if payment and payment.payment_code == entered_code:
        payment.status = "Confirmed"
        payment.confirmed_by_client = True
        payment.time_paid = timezone.now()
        payment.confirmation_time = timezone.now()
        payment.save()
        
        # Advance state to Delivered
        order.status = "Delivered"
        order.delivered_at = timezone.now()
        order.save()
        
        # Queue notification back to farmer
        farmer_obj = order.items.first().product.farmer
        _queue_notification(
            recipient_type='Farmer',
            farmer=farmer_obj,
            notification_type='Payment',
            message=f"Order #{order.id} payment verified! Customer confirmed code match.",
            related_order=order
        )
        messages.success(request, "Product delivery & receipt verified successfully!")
    else:
        messages.error(request, "Incorrect validation code. Please ask the farmer for the proper matching code.")
        
    return redirect('order_detail', order_id=order.id)