from django.urls import path
from . import views

urlpatterns = [

    path("",views.home, name="home"),
<<<<<<< HEAD
    
=======

>>>>>>> main
    path("search-results/", views.search_results, name="search_results"),

    path("room-details/", views.room_details, name="room_details"),

    path("login/", views.login, name="login"),

    path("register/", views.register, name="register"),

<<<<<<< HEAD
    path("customer-dashboard/", views.customer_dashboard, name="customer_dashboard"),

    path("booking/", views.booking, name="booking"),
=======

    path("customer-dashboard/", views.customer_dashboard, name="customer_dashboard"),

    path("profile/", views.customer_profile, name="customer_profile"),
    path("rewards/", views.customer_rewards, name="customer_rewards"),
    path("support/", views.customer_support, name="customer_support"),

   path("booking/", views.booking, name="booking"),
>>>>>>> main

    path("staff-dashboard/", views.staff_dashboard, name="staff_dashboard"),

    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    path("manage-rooms/", views.manage_rooms, name="manage_rooms"),
<<<<<<< HEAD

    path("reports/", views.reports, name="reports"),

]
=======
    path("rooms/create/", views.room_create, name="room_create"),

    path("reports/", views.reports, name="reports"),

    
 
    path("cart/review/", views.cart_review, name="cart_review"),
    path("cart/guest-details/", views.cart_guest_details, name="cart_guest_details"),
    path("cart/payment/", views.cart_payment, name="cart_payment"),
    path("booking-confirmation/", views.booking_confirmation, name="booking_confirmation"),
 



]
>>>>>>> main
