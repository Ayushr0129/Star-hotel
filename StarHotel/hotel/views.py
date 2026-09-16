from django.shortcuts import redirect, render

def home(request):
    return render(request, "hotel/home.html")

def search_results(request):
    return render(request, "hotel/search_results.html")


def room_details(request):
    return render(request, "hotel/room_details.html")


def login(request):
    return render(request, "hotel/login.html")


def register(request):
    return render(request, "hotel/register.html")


def customer_dashboard(request):
    return render(request, "hotel/customer_dashboard.html")


 
def customer_profile(request):
    return render(request, "hotel/customer_profile.html")
 
 
def customer_rewards(request):
    return render(request, "hotel/customer_rewards.html")
 
 
def customer_support(request):
    return render(request, "hotel/customer_support.html")


def booking(request):
    return render(request, "hotel/booking.html")


def staff_dashboard(request):
    return render(request, "hotel/staff_dashboard.html")


def admin_dashboard(request):
    return render(request, "hotel/admin_dashboard.html")


def manage_rooms(request):
    return render(request, "hotel/manage_rooms.html")

def room_create(request):
    if request.method == "POST":
        room_number = request.POST.get("room_number")
        room_type = request.POST.get("room_type")
        status = request.POST.get("status")

        # create room here

    return redirect("manage_rooms")


def reports(request):
    return render(request, "hotel/reports.html")
