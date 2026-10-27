from django.urls import path
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [

    path("",views.home, name="home"),
    path("search-results/", views.search_results, name="search_results"),
    path("room-details/standard/", views.room_details_standard, name="room_details_standard"),
    path("room-details/deluxe/", views.room_details_deluxe, name="room_details_deluxe"),
    path("room-details/executive/", views.room_details_executive, name="room_details_executive"),
    path("room-details/family-suite/", views.room_details_family, name="room_details_family"),
    path("packages/", views.Packages, name="packages"),
    path("activities/", views.activities, name="activities"),
    path("events/", views.events, name="events"),
    path("login/", views.login, name="login"),
    path("register/", views.register, name="register"),
    path("customer-dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path("booking/", views.booking, name="booking"),
    path("profile/", views.customer_profile, name="customer_profile"),
    path("rewards/", views.customer_rewards, name="customer_rewards"),
    path("support/", views.customer_support, name="customer_support"),
    path("staff-dashboard/", views.staff_dashboard, name="staff_dashboard"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-profile/", views.admin_profile, name="admin_profile"),
    path("admin-action/", views.admin_action, name="admin_action"),
    path("admin-action/staff/<int:user_id>/edit/", views.staff_edit, name="staff_edit"),
    path("admin-action/staff/<int:user_id>/delete/", views.staff_delete, name="staff_delete"),
    path("manage-rooms/", RedirectView.as_view(pattern_name="admin:hotel_manage_rooms"), name="manage_rooms"),
    path("reports/", RedirectView.as_view(pattern_name="admin:hotel_reports"), name="reports"),
    path("cart/review/", views.cart_review, name="cart_review"),
    path("cart/guest-details/", views.cart_guest_details, name="cart_guest_details"),
    path("cart/payment/", views.cart_payment, name="cart_payment"),
    path("booking-confirmation/", views.booking_confirmation, name="booking_confirmation"),
    path("booking/<int:booking_id>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("booking/<int:booking_id>/book-again/", views.book_again, name="book_again"),
    path("profile/edit/", views.customer_profile_edit, name="customer_profile_edit"),
]


#staff dashboard

path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
path('staff/profile/', views.staff_profile, name='staff_profile'),
path('staff/status/', views.staff_status, name='staff_status'),

