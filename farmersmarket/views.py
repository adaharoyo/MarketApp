from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
import datetime
import random
from io import BytesIO
from reportlab.pdfgen import canvas

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








def order_status_poll(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        return JsonResponse({
            "status": order.status
        })
    except Order.DoesNotExist:
        return JsonResponse({
            "error": "Order not found"
        }, status=404)
    







def farmer_report_view(request):
    return HttpResponse("Farmer report page")

def farmer_report_pdf(request):
    return HttpResponse("Farmer report PDF")