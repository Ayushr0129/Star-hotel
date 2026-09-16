from django.shortcuts import render

def home(request):
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


def booking(request):
    return render(request, "hotel/booking.html")


def staff_dashboard(request):
    return render(request, "hotel/staff_dashboard.html")


def admin_dashboard(request):
    return render(request, "hotel/admin_dashboard.html")


def manage_rooms(request):
    return render(request, "hotel/manage_rooms.html")


def reports(request):
    return render(request, "hotel/reports.html")