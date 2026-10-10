from decimal import Decimal, InvalidOperation
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.db import transaction

from django.db.models import CharField, IntegerField, Q, Value
from django.db.models.functions import Cast, Coalesce, NullIf
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .models import (
    Customer, Room, Packages, Event, Activity, Branch,
    Booking, Room_Item, Package_Item, Event_Item, Activity_Item,
)

from .models import (
    Customer, Room, Packages, Event, Branch,
    Booking, Room_Item, Package_Item, Event_Item,
)
from datetime import datetime

CART_SESSION_KEY = "cart"

# While developing, keep this False so you can click through the cart without
# filling in guest details. Set it to True before your demo / submission.
REQUIRE_GUEST_DETAILS = False

ROOM_IMAGES = {
    "Standard Room": "images/standard.jpg",
    "Deluxe Room": "images/deluxe.jpg",
    "Executive Room": "images/executive-thumb-1.jpg",
    "Family Suite": "images/family-thumb-1.jpg",
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

#BACKGROUND NEEDS TO BE CHANGED--CURRENTLY USING EVENT
ACTIVITY_FALLBACK = "images/Event-booking.jpg"
ACTIVITY_IMAGES = {
    "Spa & Wellness": "images/spa.jpg",
    "Golf Experience": "images/golf.jpg",
    "Tennis session": "images/tennis.jpg",
    "Swimming & Leisure": "images/swimming.jpg",
}
ACTIVITY_DESCRIPTIONS = {
    "Spa & Wellness": "Relax with one of our rejuvenating spa treatments.",
    "Golf Experience": "Enjoy a relaxing golf session within the hotel grounds.",
    "Tennis session": "Book a court and enjoy a fun tennis session.",
    "Swimming & Leisure": "Enjoy access to our pool and leisure facilities.",
}

def _cart_total(cart):
    return sum((Decimal(i["price"]) for i in cart), Decimal("0"))


def _parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _build_cart_item(item_type, item_id, checkin, checkout, guests, cart=()):
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

    if item_type == "activity":
        act = Activity.objects.filter(pk=item_id).first()
        if not act:
            return None, "That activity is no longer available."
        ci = _parse_date(checkin)
        if not ci:
            return None, "Choose the date you'd like to do this activity."
        if ci < date.today():
            return None, "The date cannot be in the past."
        if guests > act.capacity:
            return None, f"This activity holds a maximum of {act.capacity} guests."
        if any(i["kind"] == "event" for i in cart):
            return None, "Events are booked separately. Activities can be added to a room or package stay."
        stay = next((i for i in cart if i["kind"] == "stay"), None)
        if stay:
            s_in = date.fromisoformat(stay["check_in"])
            s_out = date.fromisoformat(stay["check_out"])
            if not (s_in <= ci <= s_out):
                return None, (f"Your stay runs from {s_in:%d %b} to {s_out:%d %b}, "
                              f"so choose a date in that range.")
        total = act.price_per_person * guests
        return {
            "kind": "activity", "item_type": "activity", "ref_id": act.pk,
            "name": act.act_name,
            "description": f"{act.act_name}, {act.location}",
            "image": ACTIVITY_IMAGES.get(act.act_name, ACTIVITY_FALLBACK),
            "price": str(total),
            "breakdown": ("Complimentary" if total == 0
                          else f"{guests} guest(s) × Rs {act.price_per_person:,.2f}"),
            "check_in": ci.isoformat(), "check_out": ci.isoformat(),
            "guests": guests, "nights": 0,
        }, None

    return None, "Unknown item."

    return None, "Unknown item."


def _add_item(cart, item):
    """Return (new_cart, notes). One stay-or-event; activities pile up."""
    notes = []

    if item["kind"] == "activity":
        # same activity on the same date updates that line; a different date adds a new one
        cart = [i for i in cart if not (i["kind"] == "activity"
                                        and i["ref_id"] == item["ref_id"]
                                        and i["check_in"] == item["check_in"])]
        return cart + [item], notes

    if item["kind"] == "event":
        if cart:
            notes.append("Events are booked separately, so your previous selection was replaced.")
        return [item], notes

    # a stay (room or package)
    old_stay = next((i for i in cart if i["kind"] == "stay"), None)
    if any(i["kind"] == "event" for i in cart):
        notes.append("Events are booked separately, so your event was replaced.")
    if old_stay and (old_stay["item_type"], old_stay["ref_id"]) != (item["item_type"], item["ref_id"]):
        notes.append("Your previous room or package was replaced.")

    activities = [i for i in cart if i["kind"] == "activity"]
    kept = [a for a in activities if item["check_in"] <= a["check_in"] <= item["check_out"]]
    if len(kept) < len(activities):
        notes.append("Some activities fell outside your new dates and were removed.")
    return [item] + kept, notes



def home(request):
    rooms = [
        {
            'name': 'Standard Room',
            'details': '2 Guests • Queen Bed',
            'price': '8,000',
            'image_path': 'images/standard.jpg',
            'url_name': 'room_details_deluxe'
        },
        {
            'name': 'Deluxe Room',
            'details': '2 Guests • King Bed',
            'price': '10,000',
            'image_path': 'images/deluxe.jpg',
            'url_name': 'room_details_deluxe'
        },
        {
            'name': 'Executive Room',
            'details': '3 Guests • King Bed • Pool Building',
            'price': '18,000',
            'image_path': 'images/executive-thumb-1.jpg',
            'url_name': 'room_details_executive'
        },
        {
            'name': 'Family Suite',
            'details': '4 Guests • 2 Double Beds',
            'price': '21,000',
            'image_path': 'images/family-thumb-1.jpg',
            'url_name': 'room_details_family'
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
            'name': 'Standard Room',
            'price': '8,000',
            'guests': 2,
            'features': ['Queen Bed', 'Free Wi-Fi', 'Air Conditioning'],
            'image_path': 'images/standard.jpg',
            'url_name': 'room_details_standard'
        },
        {
            'name': 'Deluxe Room',
            'price': '10,000',
            'guests': 2,
            'features': ['King Bed', 'Free Wi-Fi', 'Breakfast Included'],
            'image_path': 'images/deluxe.jpg',
            'url_name': 'room_details_deluxe'
        },
        {
            'name': 'Executive Room',
            'price': '18,000',
            'guests': 3,
            'features': ['King Bed', 'Sea View', 'Breakfast Included'],
            'image_path': 'images/executive-thumb-1.jpg',
            'url_name': 'room_details_executive'
        },
        {
            'name': 'Family Suite',
            'price': '21,000',
            'guests': 4,
            'features': ['2 Double Beds', 'Sea View', 'Breakfast Included'],
            'image_path': 'images/family-thumb-1.jpg',
            'url_name': 'room_details_family'
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

def room_details_standard(request):
    room = Room.objects.filter(
        room_type="Standard Room", room_status="available"
    ).order_by("room_id").first()
    return render(request, "hotel/room_details_standard.html", {"room": room})

def room_details_deluxe(request):
    room = Room.objects.filter(
        room_type="Deluxe Room", room_status="available"
    ).order_by("room_id").first()
    return render(request, "hotel/room_details_deluxe.html", {"room": room})


def room_details_executive(request):
    return render(request, "hotel/room_details_executive.html")


def room_details_family(request):
    room = Room.objects.filter(
        room_type="Family Suite", room_status="available"
    ).order_by("room_id").first()
    return render(request, "hotel/room_details_family.html", {"room": room})


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
        ).order_by("price", "room_id")
        seen_types = set()
        rooms = []
        for r in rooms_qs:
            if r.room_type not in seen_types:
                seen_types.add(r.room_type)
                rooms.append(r)

        # Room has no guests/bed-type fields in the model, so this just
        # mirrors the same spec text already shown on the home page cards.
        ROOM_SPECS = {
            "Standard Room": "2 Guests • Queen Bed",
            "Deluxe Room": "2 Guests • King Bed",
            "Executive Room": "3 Guests • King Bed • Fire heating",
            "Family Suite": "4 Guests • 2 Double Beds",
        }
        ROOM_DESCRIPTIONS = {
            "Standard Room": "A cozy, well-appointed room with a queen-size bed, air conditioning, free Wi-Fi and all the essentials for a comfortable stay.",
            "Deluxe Room": "Experience comfort and luxury in our Deluxe Room, featuring a king-size bed, complimentary breakfast, air conditioning, free Wi-Fi and panoramic garden views.",
            "Executive Room": "Designed for comfort and convenience, our Executive Room features a king-size bed, fire heating, a spacious seating area and ocean views.",
            "Family Suite": "Spacious and welcoming, our Family Suite is designed for comfort and convenience. Featuring two double beds, a seating area, complimentary high-speed Wi-Fi, air conditioning, a pull-out sofa bed and modern amenities, this suite is perfect for families or small groups looking for a relaxing getaway..",
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

        activity_cards = [
            {
                "activity": a,
                "image": ACTIVITY_IMAGES.get(a.act_name, ACTIVITY_FALLBACK),
                "description": ACTIVITY_DESCRIPTIONS.get(a.act_name, ""),
            }
            for a in Activity.objects.order_by("act_id")
        ]

        packages = Packages.objects.filter(is_active=True)
        events = Event.objects.all()

        
    
        if request.method == "POST":
            tab = request.POST.get("current_tab")
            if tab not in ("rooms", "packages", "events", "activities"):
                tab = "rooms"

            try:
                guests = int(request.POST.get("guests") or 1)
            except ValueError:
                guests = 1

            request.session["search"] = {
                "checkin": request.POST.get("checkin", ""),
                "checkout": request.POST.get("checkout", ""),
                "guests": guests,
            }

            cart = _get_cart(request)

            remove_value = request.POST.get("remove_item", "")
            if remove_value:
                r_type, _, r_id = remove_value.partition("-")
                if r_type == "activity":
                    try:
                        r_id = int(r_id)
                    except ValueError:
                        r_id = None
                    cart = [i for i in cart if not (i["kind"] == "activity" and i["ref_id"] == r_id)]
                else:
                    cart = [i for i in cart if not (i["kind"] in ("stay", "event") and i["item_type"] == r_type)]
                request.session[CART_SESSION_KEY] = cart
                request.session.modified = True
                return redirect(f"{reverse('booking')}?tab={tab}")

            item_type, _, item_id = request.POST.get("add_item", "").partition("-")
            item, error = _build_cart_item(
                item_type, item_id,
                request.POST.get("checkin"), request.POST.get("checkout"), guests, cart,
            )
            if error:
                messages.error(request, error)
            else:
                new_cart, notes = _add_item(cart, item)
                for n in notes:
                    messages.info(request, n)
                request.session[CART_SESSION_KEY] = new_cart
                request.session.modified = True
            return redirect(f"{reverse('booking')}?tab={tab}")

        cart = _get_cart(request)

        sel = next((i for i in cart if i["kind"] != "activity"), None)
        for c in room_cards:
            c["selected"] = bool(sel and sel["item_type"] == "room" and sel["name"] == c["room"].room_type)
        for c in package_cards:
            c["selected"] = bool(sel and sel["item_type"] == "package" and sel["ref_id"] == c["package"].pk)
        for c in event_cards:
            c["selected"] = bool(sel and sel["item_type"] == "event" and sel["ref_id"] == c["event"].pk)
            
        added_activity_ids = {i["ref_id"] for i in cart if i["kind"] == "activity"}
        for c in activity_cards:
            c["selected"] = c["activity"].pk in added_activity_ids
            
        for cards in (room_cards, package_cards, event_cards, activity_cards):
            cards.sort(key=lambda c: not c["selected"])   # selected first, others keep their order

        
        context = {
            "room_cards": room_cards,
            "package_cards": package_cards,
            "event_cards": event_cards,
            "cart": cart,
            "cart_total": _cart_total(cart),
            "search": request.session.get("search", {}),
            "activity_cards": activity_cards,
        }
        return render(request, "hotel/booking.html", context)

def staff_dashboard(request):
    return render(request, "hotel/staff_dashboard.html")


def admin_dashboard(request):
    return render(request, "hotel/admin_dashboard.html")


def render_admin_page(request, template_name, context=None):
    from .admin import hotel_admin_site

    page_context = hotel_admin_site.each_context(request)
    if context:
        page_context.update(context)
    return render(request, template_name, page_context)


def manage_rooms(request):
    room_sort_number = Cast(
        Coalesce(
            NullIf("room_number", Value("")),
            Cast("room_id", output_field=CharField()),
        ),
        output_field=IntegerField(),
    )
    rooms = Room.objects.select_related("branch").order_by(room_sort_number, "room_id")
    search_query = request.GET.get("search", "").strip()
    if search_query:
        rooms = rooms.filter(
            Q(room_number__icontains=search_query)
            | Q(room_type__icontains=search_query)
            | Q(room_status__icontains=search_query)
        )

    for room in rooms:
        if room.room_type in {"Suit Room", "Studio Room", "Executive Room"}:
            room.management_type = "Suit Room"
        else:
            room.management_type = "Deluxe"

    all_rooms = Room.objects.all()
    context = {
        "rooms": rooms,
        "search_query": search_query,
        "available_count": all_rooms.filter(room_status="available").count(),
        "occupied_count": all_rooms.filter(room_status="occupied").count(),
        "maintenance_count": all_rooms.filter(room_status="maintenance").count(),
    }
    context["title"] = "Manage Rooms"
    return render_admin_page(request, "hotel/manage_rooms.html", context)

def reports(request):
    return render_admin_page(request, "hotel/reports.html", {"title": "Reports & Analytics"})

def room_create(request):
    if request.method != "POST":
        return redirect("admin:hotel_manage_rooms")

    room_number = request.POST.get("room_number", "").strip()
    room_type = request.POST.get("room_type", "")
    status = request.POST.get("status", "")
    price_text = request.POST.get("price", "").strip()
    valid_room_types = {"Deluxe", "Suit Room"}
    valid_statuses = {"available", "occupied", "maintenance"}

    if not room_number.isdigit() or len(room_number) > 10:
        messages.error(request, "Enter a numeric room number with no more than 10 digits.")
        return redirect("admin:hotel_manage_rooms")
    if room_type not in valid_room_types or status not in valid_statuses:
        messages.error(request, "Choose a valid room type and status.")
        return redirect("admin:hotel_manage_rooms")

    try:
        price = Decimal(price_text)
        if price < 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        messages.error(request, "Enter a valid, non-negative room price.")
        return redirect("admin:hotel_manage_rooms")

    branch = Branch.objects.order_by("branch_id").first()
    if branch is None:
        messages.error(request, "Create a hotel branch before adding rooms.")
        return redirect("admin:hotel_manage_rooms")
    if Room.objects.filter(branch=branch, room_number=room_number).exists():
        messages.error(request, f"Room {room_number} already exists at {branch.branch_name}.")
        return redirect("admin:hotel_manage_rooms")

    Room.objects.create(
        room_number=room_number,
        room_type=room_type,
        room_status=status,
        price=price,
        branch=branch,
    )
    messages.success(request, f"Room {room_number} was added.")
    return redirect("admin:hotel_manage_rooms")


def room_update(request, room_id):
    room = get_object_or_404(Room, room_id=room_id)
    if request.method != "POST":
        return redirect("admin:hotel_manage_rooms")

    room_number = request.POST.get("room_number", "").strip()
    room_type = request.POST.get("room_type", "")
    status = request.POST.get("status", "")
    if not room_number.isdigit() or len(room_number) > 10:
        messages.error(request, "Enter a numeric room number with no more than 10 digits.")
    elif room_type not in {"Deluxe", "Suit Room"} or status not in {"available", "occupied", "maintenance"}:
        messages.error(request, "Choose a valid room type and status.")
    elif Room.objects.filter(branch=room.branch, room_number=room_number).exclude(room_id=room.room_id).exists():
        messages.error(request, f"Room {room_number} already exists at {room.branch.branch_name}.")
    else:
        room.room_number = room_number
        room.room_type = room_type
        room.room_status = status
        room.save(update_fields=["room_number", "room_type", "room_status"])
        messages.success(request, f"Room {room_number} was updated.")
    return redirect("admin:hotel_manage_rooms")


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
 
def _get_cart(request):
    cart = request.session.get(CART_SESSION_KEY, [])
    valid = (
        isinstance(cart, list)
        and all(isinstance(i, dict) and "kind" in i and "breakdown" in i for i in cart)
        and len([i for i in cart if i["kind"] != "activity"]) <= 1
        and not (any(i["kind"] == "event" for i in cart) and len(cart) > 1)
    )
    if not valid:
        cart = []
        request.session[CART_SESSION_KEY] = cart
        request.session.modified = True
    return cart

MAX_GUESTS = 6          # no capacity field on Room, so a global cap for now
TAX_RATE = Decimal("0") # set your real tax rate, e.g. Decimal("0.15")

TAX_RATE = Decimal("0") 

def cart_guest_details(request):
    cart = _get_cart(request)
    if not cart:
        return redirect("booking")

    # party size comes from the stay/event, never from this page
    main = next((i for i in cart if i["kind"] != "activity"), cart[0])
    guest_count = main["guests"]
    customer = get_current_customer(request)
    saved = request.session.get("guest_details", {}).get("people", [])

    people = []
    for n in range(guest_count):
        #Very important do not remove this comment-devloper skip + user view / to be edited
        if n < len(saved) and any(saved[n].values()):
            person = dict(saved[n])
        elif n == 0 and customer:
            person = {
                "first_name": customer.first_name, "last_name": customer.last_name,
                "phone": customer.phone, "email": customer.email,
            }
        else:
            person = {"first_name": "", "last_name": "", "phone": "", "email": ""}
        people.append(person)

    errors = []
    if request.method == "POST":
        people = []
        for n in range(guest_count):
            p = {k: request.POST.get(f"{k}_{n}", "").strip()
                 for k in ("first_name", "last_name", "phone", "email")}
            people.append(p)
            if REQUIRE_GUEST_DETAILS:
                label = "Primary guest" if n == 0 else f"Companion {n}"
                if not p["first_name"] or not p["last_name"]:
                    errors.append(f"{label}: first and last name are required.")
        if REQUIRE_GUEST_DETAILS and (not people[0]["phone"] or not people[0]["email"]):
            errors.append("Primary guest: phone and email are required.")

        if not errors:
            request.session["guest_details"] = {
                "guests": guest_count,
                **people[0],
                "people": people,
            }
            request.session.modified = True
            return redirect("cart_payment")

    context = {
        "cart": cart,
        "cart_total": _cart_total(cart),
        "guest_count": guest_count,
        "guests": [{"primary": n == 0, **p} for n, p in enumerate(people)],
        "errors": errors,
        "require": REQUIRE_GUEST_DETAILS,
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



            stay = next((i for i in cart if i["kind"] == "stay"), None)
            main = stay or cart[0]
            if main["item_type"] == "room":
                branch = get_object_or_404(Room, pk=main["ref_id"]).branch
            else:
                branch = Branch.objects.first()

            with transaction.atomic():
                booking_obj = Booking.objects.create(
                    booking_type=main["kind"],
                    no_of_guests=main["guests"],
                    check_in=date.fromisoformat(main["check_in"]),
                    check_out=date.fromisoformat(main["check_out"]),
                    bk_status="confirmed",
                    estimated_sum=_cart_total(cart),
                    customer=customer,
                    branch=branch,
                )
                for item in cart:
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
                    elif item["item_type"] == "event":
                        Event_Item.objects.create(
                            event=get_object_or_404(Event, pk=item["ref_id"]),
                            no_of_guests=item["guests"],
                            **common,
                        )
                    else:
                        Activity_Item.objects.create(
                            activity=get_object_or_404(Activity, pk=item["ref_id"]),
                            activity_date=date.fromisoformat(item["check_in"]),
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
