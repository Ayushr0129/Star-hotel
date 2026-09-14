from django.urls import path
from . import views

urlpatterns = [
    path("",views.home, name="home"),

    path("search-results/", views.search_results, name="search_results"),

    path("room-details/", views.room_details, name="room_details"),

    path("login/", views.login, name="login"),

    path("register/", views.register, name="register"),

    path("customer-dashboard/", views.customer_dashboard, name="customer_dashboard"),

    path("booking/", views.booking, name="booking"),

    path("staff-dashboard/", views.staff_dashboard, name="staff_dashboard"),

    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    path("manage-rooms/", views.manage_rooms, name="manage_rooms"),

    path("reports/", views.reports, name="reports"),

]
