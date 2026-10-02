from decimal import Decimal
from datetime import date, timedelta

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import (
    Customer, Room, Packages, Event, Branch,
    Booking, Room_Item, Package_Item, Event_Item,
)
from datetime import datetime

CART_SESSION_KEY = "cart"

ROOM_IMAGES = {
    "Deluxe Room": "images/deluxe.jpg",
    "Standard Room": "images/standard.jpg",
    "Studio Room": "images/studio.jpg",
    "Executive Room": "images/executive.jpg",
}
PACKAGE_IMAGES = {
    "Weekend Getaway": "images/Weekend.jpg",
    "Romantic Escape": "images/romantic.jpg",
    "Family Fun Package": "images/package-family.jpg",
}
EVENT_IMAGES = {
    "Garden Wedding Package": "images/wedding.webp",
    "Birthday Celebration Package": "images/birthday.png",
    "Corporate Retreat Package": "images/worker.jpg",
}


def _get_cart(request):
    return request.session.setdefault(CART_SESSION_KEY, [])


def _cart_total(cart):
    return sum((Decimal(i["price"]) for i in cart), Decimal("0"))


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _build_cart_item(item_type, item_id, checkin, checkout, guests):
    """Return (item, error). Exactly one of the two is None."""
    if guests < 1:
        return None, "Please enter at least 1 guest."

    if item_type == "room":
        room = Room.objects.select_related("branch").filter(pk=item_id).first()
        if not room:
            return None, "That room is no longer available."
        ci, co = _parse_date(checkin), _parse_date(checkout)
        if not ci or not co:
            return None, "Choose your check-in and check-out dates first."
        if ci < date.today():
            return None, "Check-in cannot be in the past."
        if co <= ci:
            return None, "Check-out must be after check-in."
        nights = (co - ci).days
        return {
            "kind": "stay", "item_type": "room", "ref_id": room.pk,
            "name": room.room_type,
            "description": f"{room.room_type}, {room.branch.branch_name}",
            "image": ROOM_IMAGES.get(room.room_type, "images/deluxe.jpg"),
            "price": str(room.price * nights),
            "breakdown": f"{nights} night(s) × Rs {room.price:,.2f}",
            "check_in": ci.isoformat(), "check_out": co.isoformat(),
            "guests": guests, "nights": nights,
        }, None

    if item_type == "package":
        package = Packages.objects.filter(pk=item_id, is_active=True).first()
        if not package:
            return None, "That package is no longer available."
        ci = _parse_date(checkin)
        if not ci:
            return None, "Choose your check-in date first."
        if ci < date.today():
            return None, "Check-in cannot be in the past."
        co = ci + timedelta(days=package.nights)
        if not (package.valid_from <= ci and co <= package.valid_to):
            return None, (f"{package.p_name} is only valid between "
                          f"{package.valid_from:%d %b %Y} and {package.valid_to:%d %b %Y}.")
        return {
            "kind": "stay", "item_type": "package", "ref_id": package.pk,
            "name": package.p_name, "description": package.p_name,
            "image": PACKAGE_IMAGES.get(package.p_name, "images/Weekend.jpg"),
            "price": str(package.base_price * guests),
            "breakdown": f"{guests} guest(s) × Rs {package.base_price:,.2f}",
            "check_in": ci.isoformat(), "check_out": co.isoformat(),
            "guests": guests, "nights": package.nights,
        }, None

    if item_type == "event":
        event = Event.objects.filter(pk=item_id).first()
        if not event:
            return None, "That event is no longer available."
        if event.eventdate < date.today():
            return None, "That event has already taken place."
        if guests > event.max_attendees:
            return None, f"This event holds a maximum of {event.max_attendees} guests."
        return {
            "kind": "event", "item_type": "event", "ref_id": event.pk,
            "name": event.title, "description": event.title,
            "image": EVENT_IMAGES.get(event.title, "images/wedding.webp"),
            "price": str(event.price_per_person * guests),
            "breakdown": f"{guests} guest(s) × Rs {event.price_per_person:,.2f}",
            "check_in": event.eventdate.isoformat(),
            "check_out": event.eventdate.isoformat(),
            "guests": guests, "nights": 0,
        }, None

    return None, "Unknown item."


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
    check_in_raw = request.GET.get('check_in', '')
    check_out_raw = request.GET.get('check_out', '')
    guests = request.GET.get('guests', '')

    check_in = ''
    check_out = ''
    if check_in_raw:
        check_in = datetime.strptime(check_in_raw, '%Y-%m-%d')
    if check_out_raw:
        check_out = datetime.strptime(check_out_raw, '%Y-%m-%d')

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
        rooms_qs = Room.objects.select_related("branch").filter(
            room_status="available"
        ).order_by("room_id")
        seen_types = set()
        rooms = []
        for r in rooms_qs:
            if r.room_type not in seen_types:
                seen_types.add(r.room_type)
                rooms.append(r)

        # Room has no guests/bed-type fields in the model, so this just
        # mirrors the same spec text already shown on the home page cards.
                ROOM_SPECS = {
            "Deluxe Room": "2 Guests • King Bed",
            "Standard Room": "2 Guests • Queen Bed",
            "Studio Room": "2 Guests • King Bed • Terrace",
            "Executive Room": "3 Guests • King Bed • Fire heating",
        }
        ROOM_IMAGES = {
            "Deluxe Room": "images/deluxe.jpg",
            "Standard Room": "images/standard.jpg",
            "Studio Room": "images/studio.jpg",
            "Executive Room": "images/executive.jpg",
        }
        ROOM_DESCRIPTIONS = {
            "Deluxe Room": "Experience comfort and luxury in our Deluxe Room, featuring a king-size bed, complimentary breakfast, air conditioning, free Wi-Fi and panoramic garden views.",
            "Standard Room": "A cozy, well-appointed room with a queen-size bed, air conditioning, free Wi-Fi and all the essentials for a comfortable stay.",
            "Studio Room": "Enjoy extra space in our Studio Room, featuring a king-size bed, private terrace, air conditioning and complimentary Wi-Fi.",
            "Executive Room": "Designed for comfort and convenience, our Executive Room features a king-size bed, fire heating, a spacious seating area and ocean views.",
        }
        room_cards = [
            {
                "room": r,
                "specs": ROOM_SPECS.get(r.room_type, ""),
                "image": ROOM_IMAGES.get(r.room_type, "images/deluxe.jpg"),
                "description": ROOM_DESCRIPTIONS.get(r.room_type, ""),
            }
            for r in rooms
        ]

        PACKAGE_IMAGES = {
            "Weekend Getaway": "images/Weekend.jpg",
            "Romantic Escape": "images/romantic.jpg",
            "Family Fun Package": "images/package-family.jpg",
        }
        PACKAGE_DESCRIPTIONS = {
            "Weekend Getaway": "Relax with a two-night stay, complimentary breakfast and selected activities.",
            "Romantic Escape": "Enjoy a romantic stay with breakfast, spa access and a special dinner.",
            "Family Fun Package": "Perfect for families with breakfast, children's activities and late checkout.",
        }
        package_cards = [
            {
                "package": p,
                "image": PACKAGE_IMAGES.get(p.p_name, "images/Weekend.jpg"),
                "description": PACKAGE_DESCRIPTIONS.get(p.p_name, ""),
            }
            for p in Packages.objects.filter(is_active=True)
        ]

        EVENT_IMAGES = {
            "Garden Wedding Package": "images/wedding.webp",
            "Birthday Celebration Package": "images/birthday.png",
            "Corporate Retreat Package": "images/worker.jpg",
        }
        EVENT_DESCRIPTIONS = {
            "Garden Wedding Package": "A full wedding venue set among landscaped gardens with ocean views, including ceremony and reception setup, floral arch, seating for guests, a dedicated event coordinator, and a private bridal suite for preparation.",
            "Birthday Celebration Package": "A private poolside or garden setup for milestone birthdays, with decor, a dessert table, and background music/DJ setup included.",
            "Corporate Retreat Package": "Full-day private venue booking for team offsites, workshops, or strategy sessions. Includes a conference hall with AV equipment, a dedicated coordinator, and a working lunch for the group.",
        }
        event_cards = [
            {
                "event": e,
                "image": EVENT_IMAGES.get(e.title, "images/wedding.webp"),
                "description": EVENT_DESCRIPTIONS.get(e.title, ""),
            }
            for e in Event.objects.all()
        ]

        packages = Packages.objects.filter(is_active=True)
        events = Event.objects.all()

        
    
        if request.method == "POST":
            item_type, _, item_id = request.POST.get("add_item", "").partition("-")
            try:
                guests = int(request.POST.get("guests") or 1)
            except ValueError:
                guests = 1

            request.session["search"] = {
                "checkin": request.POST.get("checkin", ""),
                "checkout": request.POST.get("checkout", ""),
                "guests": guests,
            }
            tab = request.POST.get("current_tab")
            if tab not in ("rooms", "packages", "events"):
                tab = "rooms"

            item, error = _build_cart_item(
                item_type, item_id,
                request.POST.get("checkin"), request.POST.get("checkout"), guests,
            )
            if error:
                messages.error(request, error)
            else:
                cart = _get_cart(request)
                if cart:
                    if cart[0]["kind"] != item["kind"]:
                        messages.info(request, "Stays and events are booked separately, "
                                               "so your previous selection was replaced.")
                    elif cart[0]["item_type"] != item["item_type"]:
                        messages.info(request, "A package already includes your stay, "
                                               "so your previous selection was replaced.")
                request.session[CART_SESSION_KEY] = [item]
                request.session.modified = True
            return redirect(f"{reverse('booking')}?tab={tab}")

        
    
        cart = _get_cart(request)
        context = {
            "room_cards": room_cards,
            "package_cards": package_cards,
            "event_cards": event_cards,
            "cart": cart,
            "cart_total": _cart_total(cart),
            "search": request.session.get("search", {}),
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

    default_guests = cart[0]["guests"]

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

            item = cart[0]
            if item["item_type"] == "room":
                branch = get_object_or_404(Room, pk=item["ref_id"]).branch
            else:
                branch = Branch.objects.first()

            with transaction.atomic():
                booking_obj = Booking.objects.create(
                    booking_type=item["kind"],
                    no_of_guests=item["guests"],
                    check_in=date.fromisoformat(item["check_in"]),
                    check_out=date.fromisoformat(item["check_out"]),
                    bk_status="confirmed",
                    estimated_sum=_cart_total(cart),
                    customer=customer,
                    branch=branch,
                )
                common = dict(
                    bi_type=item["item_type"],
                    price=item["price"],
                    payment_method="credit_card",
                    description=item["description"],
                    booking=booking_obj,
                )

                if item["item_type"] == "room":
                    Room_Item.objects.create(
                        room=get_object_or_404(Room, pk=item["ref_id"]),
                        check_in=booking_obj.check_in,
                        check_out=booking_obj.check_out,
                        **common,
                    )
                elif item["item_type"] == "package":
                    Package_Item.objects.create(
                        package=get_object_or_404(Packages, pk=item["ref_id"]),
                        no_of_guests=item["guests"],
                        **common,
                    )
                else:
                    Event_Item.objects.create(
                        event=get_object_or_404(Event, pk=item["ref_id"]),
                        no_of_guests=item["guests"],
                        **common,
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