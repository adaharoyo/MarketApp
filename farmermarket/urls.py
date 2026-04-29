"""
URL configuration for farmermarket project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from farmersmarket.views import add_client_view,add_farm_view,add_farmer_view,add_order_view,add_payment_view,add_product_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('add_client/',add_client_view,name="Client_page"),
    path('add_order/',add_order_view,name="Order_page"),
    path('add_farm/',add_farm_view,name="Farm_page"),
    path('add_payment/',add_payment_view,name="Payment_page"),
    path('add_product/',add_product_view,name="Product_page"),
    path('add_farmer/',add_farmer_view,name="Farmer_page"),
]
