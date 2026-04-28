from django.forms import ModelForm
from farmersmarket.models import Farm,Farmer,Client,Product,Order,Payment

class FarmForm(ModelForm):
    class Meta:
        model=Farm
        fields= '__all__'

class FarmerForm(ModelForm):
    class Meta:
        model=Farmer
        fields= '__all__'        

class ClientForm(ModelForm):
    class Meta:
        model=Client
        fields= '__all__'  

class ProductForm(ModelForm):
    class Meta:
        model=Product
        fields= '__all__'              

class OrderForm(ModelForm):
    class Meta:
        model=Order
        fields= '__all__'        


class PaymentForm(ModelForm):
    class Meta:
        model=Payment
        fields= '__all__'        