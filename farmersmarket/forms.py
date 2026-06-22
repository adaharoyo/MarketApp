import re
from django import forms
from django.forms import ModelForm
from farmersmarket.models import (
    Farm, Farmer, Client, Product, Order, OrderItem, Payment, Notification
)


class FarmForm(ModelForm):
    class Meta:
        model = Farm
        fields = '__all__'


class FarmerForm(ModelForm):
    class Meta:
        model = Farmer
        exclude = ['user']


class ClientForm(ModelForm):
    class Meta:
        model = Client
        exclude = ['user']


class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = [
            'crop_name', 'category', 'unit',
            'quantity_available', 'price', 'currency',
            'harvest_date', 'description', 'image', 'is_available',
        ]
        widgets = {
            'harvest_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_crop_name(self):
        crop_name = self.cleaned_data['crop_name'].strip()

        if not re.match(r'^[A-Za-z\s]+$', crop_name):
            raise forms.ValidationError(
                "Product name should contain letters only."
            )

        return crop_name


class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = '__all__'


class OrderItemForm(ModelForm):
    class Meta:
        model = OrderItem
        fields = '__all__'


class PaymentForm(ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'


class NotificationForm(ModelForm):
    class Meta:
        model = Notification
        fields = '__all__'