from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from farmersmarket.views import (
    home, login_view, register_view, logout_view, dashboard_view,
    # marketplace
    marketplace_view, product_detail_view,
    # ratings
    rate_product,
    # cart
    cart_view, add_to_cart, remove_from_cart, update_cart,
    # checkout & orders
    checkout_view, order_detail_view, update_order_status,
    # OTP & earnings
    farmer_earnings_view, farmer_sales_history_view,
    # notifications
    mark_notifications_read,
    # product management
    add_product_view, edit_product_view,
    # order actions
    cancel_order_view,
    # dedicated list views
    farmer_products_view, farmer_orders_view, client_orders_view,
    # admin stubs
    add_client_view, add_farm_view, add_farmer_view,
    add_order_view, add_payment_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Public
    path('', home, name='home'),
    path('marketplace/', marketplace_view, name='marketplace'),
    path('marketplace/<int:product_id>/', product_detail_view, name='product_detail'),
    path('marketplace/<int:product_id>/rate/', rate_product, name='rate_product'),

    # Auth
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),

    # Dashboard & earnings
    path('dashboard/', dashboard_view, name='dashboard'),
    path('earnings/', farmer_earnings_view, name='farmer_earnings'),
    path('earnings/sales/', farmer_sales_history_view, name='farmer_sales_list'),

    # Cart
    path('cart/', cart_view, name='cart'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:product_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:product_id>/', update_cart, name='update_cart'),

    # Checkout & orders
    path('checkout/', checkout_view, name='checkout'),
    path('orders/<int:order_id>/', order_detail_view, name='order_detail'),
    path('orders/<int:order_id>/status/', update_order_status, name='update_order_status'),

    # Notifications
    path('notifications/read/', mark_notifications_read, name='mark_notifications_read'),

    # Farmer product management
    path('add_product/', add_product_view, name='add_product'),
    path('edit_product/<int:product_id>/', edit_product_view, name='edit_product'),

    # Order cancellation
    path('orders/<int:order_id>/cancel/', cancel_order_view, name='cancel_order'),

    # Dedicated dashboard lists
    path('dashboard/products/', farmer_products_view, name='farmer_products_list'),
    path('dashboard/orders/', farmer_orders_view, name='farmer_orders_list'),
    path('dashboard/my-orders/', client_orders_view, name='client_orders_list'),

    # Admin stubs
    path('add_client/', add_client_view, name='add_client'),
    path('add_order/', add_order_view, name='add_order'),
    path('add_farm/', add_farm_view, name='add_farm'),
    path('add_payment/', add_payment_view, name='add_payment'),
    path('add_farmer/', add_farmer_view, name='add_farmer'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
