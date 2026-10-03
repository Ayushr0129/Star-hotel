from django.urls import path
from . import views

urlpatterns = [

    path("",views.home, name="home"),
    path("search-results/", views.search_results, name="search_results"),
    path("room-details/deluxe/", views.room_details_deluxe, name="room_details_deluxe"),
    path("room-details/executive/", views.room_details_executive, name="room_details_executive"),
    path("room-details/family-suite/", views.room_details_family, name="room_details_family"),
    path("login/", views.login, name="login"),
    path("register/", views.register, name="register"),
    path("customer-dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path("booking/", views.booking, name="booking"),
    path("profile/", views.customer_profile, name="customer_profile"),
    path("rewards/", views.customer_rewards, name="customer_rewards"),
    path("support/", views.customer_support, name="customer_support"),
    path("staff-dashboard/", views.staff_dashboard, name="staff_dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("manage-rooms/", views.manage_rooms, name="manage_rooms"),
    path("rooms/create/", views.room_create, name="room_create"),
    path("rooms/<int:room_id>/edit/", views.room_update, name="room_update"),
    path("reports/", views.reports, name="reports"),
    path("cart/review/", views.cart_review, name="cart_review"),
    path("cart/guest-details/", views.cart_guest_details, name="cart_guest_details"),
    path("cart/payment/", views.cart_payment, name="cart_payment"),
    path("booking-confirmation/", views.booking_confirmation, name="booking_confirmation"),
]
