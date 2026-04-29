from django.shortcuts import render

from farmersmarket.forms import FarmForm,FarmerForm,ClientForm,ProductForm,PaymentForm,OrderForm
from farmersmarket.models import Farm,Farmer,Client,Product,Order,Payment
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

#EDITING

def edit_farm_view(request, farm_id):
    
    farm = Farm.objects.get(id=farm_id) 

    if request.method == "POST":
        
        farm_form = FarmForm(request.POST, instance=farm)
        
        if farm_form.is_valid():
            farm_form.save()
           
    else:
        
        farm_form = FarmForm(instance=farm)
        
    context = {'form': farm_form}
    return render(request, "edit_farm.html", context)

def edit_farmer_view(request, farmer_id):
    
    farmer = Farmer.objects.get(id=farmer_id) 

    if request.method == "POST":
        
        farmer_form = FarmerForm(request.POST, instance=farmer)
        
        if farmer_form.is_valid():
            farmer_form.save()
           
    else:
        
        farmer_form = FarmerForm(instance=farmer)
        
    context = {'form': farmer_form}
    return render(request, "edit_farmer.html", context)

def edit_payment_view(request, payment_id):
    
    payment = Payment.objects.get(id=payment_id) 

    if request.method == "POST":
        
        payment_form = PaymentForm(request.POST, instance=payment)
        
        if payment_form.is_valid():
            payment_form.save()
           
    else:
        
        payment_form = PaymentForm(instance=payment)
        
    context = {'form': payment_form}
    return render(request, "edit_payment.html", context)

def edit_product_view(request, product_id):
    
    product = Product.objects.get(id=product_id) 

    if request.method == "POST":
        
        product_form = ProductForm(request.POST, instance=product)
        
        if product_form.is_valid():
            product_form.save()
           
    else:
        
        product_form = ProductForm(instance=product)
        
    context = {'form': product_form}
    return render(request, "edit_product.html", context)

def edit_client_view(request, client_id):
    
    client = client.objects.get(id=client_id) 

    if request.method == "POST":
        
        client_form = ClientForm(request.POST, instance=client)
        
        if client_form.is_valid():
            client_form.save()
           
    else:
        
        client_form = ClientForm(instance=client)
        
    context = {'form': client_form}
    return render(request, "edit_client.html", context)

def edit_order_view(request, order_id):
    
    order = order.objects.get(id=order_id) 

    if request.method == "POST":
        
        order_form = OrderForm(request.POST, instance=order)
        
        if order_form.is_valid():
            order_form.save()
           
    else:
        
        order_form = OrderForm(instance=order)
        
    context = {'form': order_form}
    return render(request, "edit_order.html", context)

         