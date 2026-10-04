from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.urls import path

from .models import Branch, Room


class StarHotelAdminSite(admin.AdminSite):
    site_header = "STAR HOTEL Administration"
    site_title = "STAR HOTEL Admin"
    index_title = "Hotel management"

    def get_urls(self):
        from . import views

        custom_urls = [
            path(
                "manage-rooms/",
                self.admin_view(views.manage_rooms),
                name="hotel_manage_rooms",
            ),
            path(
                "manage-rooms/create/",
                self.admin_view(views.room_create),
                name="hotel_room_create",
            ),
            path(
                "manage-rooms/<int:room_id>/edit/",
                self.admin_view(views.room_update),
                name="hotel_room_update",
            ),
            path(
                "reports/",
                self.admin_view(views.reports),
                name="hotel_reports",
            ),
        ]
        return custom_urls + super().get_urls()


class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_number", "room_type", "room_status", "price", "branch")
    list_filter = ("room_type", "room_status", "branch")
    search_fields = ("room_number", "room_type", "branch__branch_name")


hotel_admin_site = StarHotelAdminSite(name="admin")
hotel_admin_site.register(get_user_model(), UserAdmin)
hotel_admin_site.register(Group)
hotel_admin_site.register(Branch)
hotel_admin_site.register(Room, RoomAdmin)
