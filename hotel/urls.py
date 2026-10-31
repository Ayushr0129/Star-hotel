from django.urls import path
from . import views
from . import authpages

urlpatterns = [
    path("",views.home, name="home"),
    
    path("search-results/", views.search_results, name="search_results"),

    path("room-details/", views.room_details, name="room_details"),

    path("login/", authpages.login_view, name="login"),
    path("logout/", authpages.logout_view, name="logout"),

    path("register/", authpages.register_view, name="register"),

    path("customer-dashboard/", views.customer_dashboard, name="customer_dashboard"),

    path("booking/", views.booking, name="booking"),

    path("staff-dashboard/", views.staff_dashboard, name="staff_dashboard"),

    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),

    path("admin-profile/", views.admin_profile, name="admin_profile"),

    path("admin-action/", views.admin_action, name="admin_action"),

    path("manage-rooms/", views.manage_rooms, name="manage_rooms"),

    path("reports/", views.reports, name="reports"),

]