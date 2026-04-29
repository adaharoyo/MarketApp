from django.shortcuts import render

from farmersmarket.forms import FarmForm,FarmerForm,ClientForm,ProductForm,PaymentForm,OrderForm
# Create your views here.
def add_farm_view(request):
    if request.method =="POST":
        farm_form = FarmForm(request.POST)

    if farm_form.is_valid():
        farm_form.save()

    else:
        farm_form=FarmForm()

    context={
        'form':farm_form,
        
    } 

    return render(request,"add_farm_html",context)  


def add_order_view(request):
    if request.method =="POST":
        order_form = OrderForm(request.POST)

    if order_form.is_valid():
        order_form.save()

    else:
        order_form=OrderForm()

    context={
        'form':order_form,
        
    } 

    return render(request,"add_order_html",context)    

def add_farmer_view(request):
    if request.method =="POST":
        farmer_form = FarmerForm(request.POST)

    if farmer_form.is_valid():
        farmer_form.save()

    else:
        farmer_form=FarmerForm()

    context={
        'form':farmer_form,
        
    } 

    return render(request,"add_farmer_html",context)       

def add_payment_view(request):
    if request.method =="POST":
        payment_form = PaymentForm(request.POST)

    if payment_form.is_valid():
        payment_form.save()

    else:
        payment_form=PaymentForm()

    context={
        'form':payment_form,
        
    } 

    return render(request,"add_payment_html",context)  

def add_product_view(request):
    if request.method =="POST":
        product_form = ProductForm(request.POST)

    if product_form.is_valid():
        product_form.save()

    else:
        product_form=ProductForm()

    context={
        'form':product_form,
        
    } 

    return render(request,"add_product_html",context)                               

def add_client_view(request):
    if request.method =="POST":
        client_form = ClientForm(request.POST)

    if client_form.is_valid():
        client_form.save()

    else:
        client_form=ClientForm()

    context={
        'form':client_form,
        
    } 

    return render(request,"add_client_html",context)           