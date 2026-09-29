from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    dob = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    join_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.username

class Loyalty(models.Model):
    loyalty_num = models.AutoField(primary_key=True)
    tier = models.CharField(max_length=50)
    discount_rate = models.FloatField(default=0.0)
    multiplier_rate = models.FloatField(default=1.0)

    def __str__(self):
        return self.tier

class Customer(User):
    nid = models.CharField(max_length=20, unique=True)
    loyalty = models.ForeignKey(
        Loyalty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customers'
    )

    def __str__(self):
        return f"{self.username} ({self.nid})"

class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_type = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.role_type

class Branch(models.Model):
    branch_id = models.AutoField(primary_key=True)
    branch_name = models.CharField(max_length=100)
    tel_no = models.CharField(max_length=20)
    street = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    zipcode = models.CharField(max_length=10)

    class Meta:
        verbose_name_plural = "branches"

    def __str__(self):
        return self.branch_name    
 
class Employee(User):
    job_title = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='employees'
    )
    branch = models.ForeignKey(
        'Branch',
        on_delete=models.PROTECT,
        null =True,
        blank = True,
        related_name='employees'
    )

    def __str__(self):
        return f"{self.username} ({self.job_title})"
    
class Administrator(Employee):
    def __str__(self):
        return f"{self.username} (Administrator)"
