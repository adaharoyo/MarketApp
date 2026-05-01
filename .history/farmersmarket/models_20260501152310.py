from django.db import models

# Create your models here.
class Farmer(models.Model):
    name = models.CharField(max_length=50)
    contact=models.CharField(max_length=10)
    address=models.CharField(max_length=20)

class Farm(models.Model):
    name =models.CharField(max_length=50)
    location=models.CharField(max_length=50)
    farmer=models.ForeignKey(Farmer,on_delete=models.CASCADE)



class Client(models.Model):
    GENDER_OPTIONS=[
        ("M","Male"),
        ("F","Female")
    ]
    ACCOUNT_STATUS=[("Active","Active"),
                    ("Inactive","Inactive")]
    name = models.CharField(max_length=50)
    contact=models.CharField(max_length=10)
    address=models.CharField(max_length=20,null=True)
    gender= models.CharField(max_length=2,choices=GENDER_OPTIONS) 
    account_status=models.CharField(max_length=10,choices=ACCOUNT_STATUS) 

class Product(models.Model): 
    crop_name=models.CharField(max_length=50)
    quantity_available=models.CharField(max_length=20)
    price=models.IntegerField()

class Order(models.Model):
    ORDER_STATUS=[("Pending","Pending"),
                  ("Paid","Paid")]
    order_date=models.DateField(auto_now=False)
    client_id=models.ForeignKey(Client,on_delete=models.CASCADE)  


class Payment(models.Model):
    PAYMENT_OPTIONS=[("Cash","Cash"),
                     ("Mobile Money","Mobile Money")]
    order_id=models.ForeignKey(Order,on_delete=models.CASCADE)
    time_paid=models.DateTimeField(auto_now=False)
    amount=models.IntegerField()
           