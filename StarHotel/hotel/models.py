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