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

class Room(models.Model):
    room_id = models.AutoField(primary_key=True)
    room_type = models.CharField(max_length=50)
    room_status = models.CharField(max_length=20, default='available')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='rooms'
    )

    def __str__(self):
        return f"{self.room_type} - {self.branch.branch_name}"

class Booking(models.Model):
    bk_id = models.AutoField(primary_key=True)
    no_of_guests = models.PositiveIntegerField()
    check_in = models.DateField()
    check_out = models.DateField()
    bk_date = models.DateField(auto_now_add=True)
    bk_status = models.CharField(max_length=20, default='pending')
    estimated_sum = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='bookings'
    )

    def __str__(self):
        return f"Booking #{self.bk_id} - {self.customer.username}"

class Booking_Item(models.Model):
    bi_type = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=30)
    purchase_date = models.DateField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='booking_items'
    )

    def __str__(self):
        return f"{self.bi_type} - {self.price}"