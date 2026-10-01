from django.shortcuts import redirect, render
from datetime import date
from datetime import datetime, timedelta

from .models import (
    Customer, Room, Packages, Event, Branch,
    Booking, Room_Item, Package_Item, Event_Item,
)

CART_SESSION_KEY = "cart"


def _get_cart(request):
    return request.session.setdefault(CART_SESSION_KEY, [])


def _cart_total(cart):
    return sum(item["price"] for item in cart)


def home(request):
    rooms = [
        {
            'name': 'Deluxe Room',
            'details': '2 Guests • King Bed',
            'price': '15,000',
            'image_path': 'images/deluxe.jpg'
        },
        {
            'name': 'Standard Room',
            'details': '2 Guests • Queen Bed',
            'price': '9,500',
            'image_path': 'images/standard.jpg'
        },
        {
            'name': 'Studio Room',
            'details': '2 Guests • King Bed • Terrace',
            'price': '12,500',
            'image_path': 'images/studio.jpg'
        },
        {
            'name': 'Executive Room',
            'details': '3 Guests • King Bed • Fire heating',
            'price': '18,000',
            'image_path': 'images/executive.jpg'
        },
    ]

    return render(request, "hotel/home.html", {"rooms": rooms})


def search_results(request):
    branch = request.GET.get('branch', '')
    check_in = request.GET.get('check_in', '')
    check_out = request.GET.get('check_out', '')
    guests = request.GET.get('guests', '')

    rooms = [
        {
            'name': 'Deluxe Room',
            'price': '15,000',
            'guests': 2,
            'features': ['King Bed', 'Free Wi-Fi', 'Breakfast Included'],
            'image_path': 'images/deluxe.jpg'
        },
        {
            'name': 'Executive Room',
            'price': '18,000',
            'guests': 2,
            'features': ['Queen Bed', 'Sea View', 'Breakfast Included'],
            'image_path': 'images/executive.jpg'
        },
        {
            'name': 'Family Suite',
            'price': '21,000',
            'guests': 4,
            'features': ['2 Double Beds', 'Sea View', 'Breakfast Included'],
            'image_path': 'images/family-thumb-1.jpg'
        },
    ]
    context = {
        'rooms': rooms,
        'branch': branch,
        'check_in': check_in,
        'check_out': check_out,
        'guests': guests,
    }
    return render(request, "hotel/search_results.html", context)


def room_details_deluxe(request):
    return render(request, "hotel/room_details_deluxe.html")


def room_details_executive(request):
    return render(request, "hotel/room_details_executive.html")


def room_details_family(request):
    return render(request, "hotel/room_details_family.html")


def login(request):
    return render(request, "hotel/login.html")


def register(request):
    return render(request, "hotel/register.html")


def customer_dashboard(request):
    # login is n0t built yet, so fall back to the first customer in
    # the DB for testing. Once login works, delete the fallback and rely
    # only on request.user.customer.

    customer = get_current_customer(request)

    if customer is None:
        return render(request, "hotel/customer_dashboard.html", {"no_customers": True})

    today = date.today()
    bookings = customer.bookings.select_related("branch").prefetch_related(
        "booking_items"
    ).order_by("-check_in")

    current_bookings = bookings.filter(check_out__gte=today)
    past_bookings = bookings.filter(check_out__lt=today)

    total_nights = sum((b.check_out - b.check_in).days for b in bookings)
    points = total_nights * 100

    context = {
        "customer": customer,
        "current_bookings": current_bookings,
        "past_bookings": past_bookings,
        "stays_count": bookings.count(),
        "points": points,
    }
    return render(request, "hotel/customer_dashboard.html", context)

def get_current_customer(request):
    """
    TEMP: login isn't built yet, so fall back to the first customer in the
    DB for testing. Once login works, delete the fallback and rely only on
    request.user.customer.
    """
    if request.user.is_authenticated:
        try:
            return request.user.customer
        except Customer.DoesNotExist:
            pass
    return Customer.objects.select_related("loyalty").first()

def customer_profile(request):
    customer = get_current_customer(request)

    if customer is None:
        return render(request, "hotel/customer_profile.html", {"no_customers": True})

    context = {"customer": customer}
    return render(request, "hotel/customer_profile.html", context)
 
 
def customer_rewards(request):
    customer = get_current_customer(request)

    if customer is None:
        return render(request, "hotel/customer_rewards.html", {"no_customers": True})

    bookings = customer.bookings.select_related("branch").prefetch_related(
        "booking_items"
    ).order_by("-check_in")

    # swap for a real formula one later.
    history = []
    total_points = 0
    for b in bookings:
        nights = (b.check_out - b.check_in).days
        pts = nights * 100
        total_points += pts
        history.append({"booking": b, "points": pts})

    context = {
        "customer": customer,
        "total_points": total_points,
        "history": history,
    }
    return render(request, "hotel/customer_rewards.html", context)
 
def customer_support(request):
   return render(request, "hotel/customer_support.html")


def booking(request):
        rooms = Room.objects.select_related("branch").filter(room_status="available")
        packages = Packages.objects.filter(is_active=True)
        events = Event.objects.all()
    
        if request.method == "POST":
            add_item = request.POST.get("add_item", "")
            checkin = request.POST.get("checkin")
            checkout = request.POST.get("checkout")
            try:
                guests = int(request.POST.get("guests") or 1)
            except ValueError:
                guests = 1
    
            item_type, _, item_id = add_item.partition("-")
            cart = _get_cart(request)
    
            if item_type == "room" and checkin and checkout:
                room = Room.objects.filter(pk=item_id).first()
                try:
                    ci = date.fromisoformat(checkin)
                    co = date.fromisoformat(checkout)
                except ValueError:
                    ci = co = None
                if room and ci and co and co > ci:
                    nights = (co - ci).days
                    cart.append({
                        "item_type": "room",
                        "ref_id": room.pk,
                        "name": f"{room.room_type} room",
                        "description": f"{room.room_type} room, {room.branch.branch_name}",
                        "price": float(room.price) * nights,
                        "check_in": checkin,
                        "check_out": checkout,
                        "guests": guests,
                        "nights": nights,
                    })
                    request.session.modified = True
    
            elif item_type == "package":
                package = Packages.objects.filter(pk=item_id).first()
                if package:
                    cart.append({
                        "item_type": "package",
                        "ref_id": package.pk,
                        "name": package.p_name,
                        "description": package.p_name,
                        "price": float(package.base_price) * guests,
                        "guests": guests,
                    })
                    request.session.modified = True
    
            elif item_type == "event":
                event = Event.objects.filter(pk=item_id).first()
                if event:
                    cart.append({
                        "item_type": "event",
                        "ref_id": event.pk,
                        "name": event.title,
                        "description": event.title,
                        "price": float(event.price_per_person) * guests,
                        "guests": guests,
                    })
                    request.session.modified = True
    
            return redirect("booking")
    
        cart = _get_cart(request)
        context = {
            "rooms": rooms,
            "packages": packages,
            "events": events,
            "cart": cart,
            "cart_total": _cart_total(cart),
        }
        return render(request, "hotel/booking.html", context)

def staff_dashboard(request):
    return render(request, "hotel/staff_dashboard.html")


def admin_dashboard(request):
    return render(request, "hotel/admin_dashboard.html")


def manage_rooms(request):
    return render(request, "hotel/manage_rooms.html")

def reports(request):
    return render(request, "hotel/reports.html")

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
    cart = _get_cart(request)

    if request.method == "POST":
        try:
            idx = int(request.POST.get("remove_index"))
            if 0 <= idx < len(cart):
                cart.pop(idx)
                request.session.modified = True
        except (TypeError, ValueError):
            pass
        return redirect("cart_review")

    context = {"cart": cart, "cart_total": _cart_total(cart)}
    return render(request, "hotel/cart_review.html", context)
 
 
def cart_guest_details(request):
    cart = _get_cart(request)
    if not cart:
        return redirect("booking")

    if request.method == "POST":
        request.session["guest_details"] = {
            "guests": request.POST.get("guests"),
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "phone": request.POST.get("phone"),
            "email": request.POST.get("email"),
        }
        request.session.modified = True
        return redirect("cart_payment")

    room_items = [i for i in cart if i["item_type"] == "room"]
    default_guests = room_items[0]["guests"] if room_items else 2

    context = {
        "cart": cart,
        "cart_total": _cart_total(cart),
        "default_guests": default_guests,
    }
    return render(request, "hotel/cart_guest_details.html", context)
 
 
def cart_payment(request):
    cart = _get_cart(request)
    if not cart:
        return redirect("booking")

    error = None

    if request.method == "POST":
        card_number = request.POST.get("card_number", "").strip()
        agree = request.POST.get("agree")

        if not card_number or not agree:
            error = "Please fill in your card details and agree to the cancellation policy."
        else:
            customer = get_current_customer(request)
            if customer is None:
                return redirect("login")

            room_items = [i for i in cart if i["item_type"] == "room"]
            if room_items:
                first_room = Room.objects.filter(pk=room_items[0]["ref_id"]).first()
                branch = first_room.branch if first_room else Branch.objects.first()
                check_in = date.fromisoformat(room_items[0]["check_in"])
                check_out = date.fromisoformat(room_items[0]["check_out"])
                total_guests = room_items[0]["guests"]
            else:
                branch = Branch.objects.first()
                check_in = date.today()
                check_out = date.today() + timedelta(days=1)
                total_guests = 1

            booking_obj = Booking.objects.create(
                no_of_guests=total_guests,
                check_in=check_in,
                check_out=check_out,
                bk_status="confirmed",
                estimated_sum=_cart_total(cart),
                customer=customer,
                branch=branch,
            )

            for item in cart:
                if item["item_type"] == "room":
                    room = Room.objects.filter(pk=item["ref_id"]).first()
                    if room:
                        Room_Item.objects.create(
                            bi_type="room", price=item["price"],
                            payment_method="credit_card", description=item["description"],
                            booking=booking_obj, room=room,
                            check_in=date.fromisoformat(item["check_in"]),
                            check_out=date.fromisoformat(item["check_out"]),
                        )
                elif item["item_type"] == "package":
                    package = Packages.objects.filter(pk=item["ref_id"]).first()
                    if package:
                        Package_Item.objects.create(
                            bi_type="package", price=item["price"],
                            payment_method="credit_card", description=item["description"],
                            booking=booking_obj, package=package, no_of_guests=item["guests"],
                        )
                elif item["item_type"] == "event":
                    event = Event.objects.filter(pk=item["ref_id"]).first()
                    if event:
                        Event_Item.objects.create(
                            bi_type="event", price=item["price"],
                            payment_method="credit_card", description=item["description"],
                            booking=booking_obj, event=event, no_of_guests=item["guests"],
                        )

            request.session["last_booking_id"] = booking_obj.pk
            request.session[CART_SESSION_KEY] = []
            request.session.pop("guest_details", None)
            request.session.modified = True
            return redirect("booking_confirmation")

    context = {"cart": cart, "cart_total": _cart_total(cart), "error": error}
    return render(request, "hotel/cart_payment.html", context)
 

def booking_confirmation(request):
    booking_id = request.session.get("last_booking_id")
    booking_obj = None
    if booking_id:
        booking_obj = Booking.objects.filter(pk=booking_id).select_related(
            "customer"
        ).prefetch_related("booking_items").first()

    return render(request, "hotel/booking_confirmation.html", {"booking": booking_obj}) 