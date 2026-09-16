from django.shortcuts import redirect, render

def home(request):
<<<<<<< HEAD
    rooms = [
        {
            'name': 'Deluxe Room',
            'details': '2 Guests • King Bed',
            'price': '10,000',
            'image_path': 'images/rooms/deluxe.jpg'
        },
        {
            'name': 'Standard Room',
            'details': '2 Guests • Queen Bed',
            'price': '8,000',
            'image_path': 'images/rooms/standard.jpg'
        },
        {
            'name': 'Studio Room',
            'details': '2 Guests • King Bed • Terrace',
            'price': '12,000',
            'image_path': 'images/rooms/studio.jpg'
        },
        {
            'name': 'Executive Room',
            'details': '3 Guests • King Bed • Pool Building',
            'price': '18,000',
            'image_path': 'images/rooms/executive.jpg'
        },
    ]
    return render(request, 'home.html', {'rooms': rooms})
    
=======
    return render(request, "hotel/home.html")
>>>>>>> main

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


<<<<<<< HEAD
=======
 
def customer_profile(request):
    return render(request, "hotel/customer_profile.html")
 
 
def customer_rewards(request):
    return render(request, "hotel/customer_rewards.html")
 
 
def customer_support(request):
    return render(request, "hotel/customer_support.html")


>>>>>>> main
def booking(request):
    return render(request, "hotel/booking.html")


def staff_dashboard(request):
    return render(request, "hotel/staff_dashboard.html")


def admin_dashboard(request):
    return render(request, "hotel/admin_dashboard.html")


def manage_rooms(request):
    return render(request, "hotel/manage_rooms.html")

<<<<<<< HEAD

def reports(request):
    return render(request, "hotel/reports.html")
=======
def room_create(request):
    if request.method == "POST":
        room_number = request.POST.get("room_number")
        room_type = request.POST.get("room_type")
        status = request.POST.get("status")

        # create room here

    return redirect("manage_rooms")


def reports(request):
    return render(request, "hotel/reports.html")


def cart_review(request):
    return render(request, "hotel/cart_review.html")
 
 
def cart_guest_details(request):
    return render(request, "hotel/cart_guest_details.html")
 
 
def cart_payment(request):
    return render(request, "hotel/cart_payment.html")
 
 
def booking_confirmation(request):
    return render(request, "hotel/booking_confirmation.html")
 
>>>>>>> main
