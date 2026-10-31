from django.contrib.auth import logout as auth_logout
from django.views.decorators.http import require_POST
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta 
import calendar
from django.conf import settings
from django.contrib import messages
from django.db import transaction
 
from django.db.models import Avg, CharField, Count, IntegerField, Q, Sum, Value
from django.db.models.functions import Cast, Coalesce, NullIf
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .models import (
    Customer, Room, Packages, Event, Activity, Branch,
    Booking, Room_Item, Package_Item, Event_Item, Activity_Item,Loyalty, Support_Ticket,
)
from .models import (
    Customer, Room, Packages, Event, Branch,
    Booking, Room_Item, Package_Item, Event_Item,
)
from datetime import datetime
from datetime import time as dtime
 
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone

import re
from django.core.validators import validate_email

CART_SESSION_KEY = "cart"
 
# Customers can cancel a booking only if check-in is at least this many hours away.
CANCEL_WINDOW_HOURS = 48
 
# While developing, keep this False so you can click through the cart without
# filling in guest details. Set it to True before your demo / submission.
REQUIRE_GUEST_DETAILS = False

POINT_UNIT = Decimal("100")          # Rs spent per base point
TIERS = [                            # (tier name, lifetime points needed), lowest first
    ("Bronze", 0),
    ("Silver", 500),
    ("Gold", 1500),
    ("Platinum", 3000),
]
 
ROOM_IMAGES = {
    "Standard Room": "images/standard-thumb-1.jpg",
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
 
EVENT_DESCRIPTIONS = {
    "Garden Wedding Package": "A full wedding venue set among landscaped gardens with ocean views, including ceremony and reception setup, floral arch, seating for guests, a dedicated event coordinator, and a private bridal suite for preparation.",
    "Birthday Celebration Package": "A private poolside or garden setup for milestone birthdays, with decor, a dessert table, and background music/DJ setup included.",
    "Corporate Retreat Package": "Full-day private venue booking for team offsites, workshops, or strategy sessions. Includes a conference hall with AV equipment, a dedicated coordinator, and a working lunch for the group.",
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
 
PACKAGE_SLUGS = {
    "Weekend Getaway": "weekend-getaway",
    "Romantic Escape": "romantic-escape",
    "Family Fun Package": "family-fun",
}
PACKAGE_DESCRIPTIONS = {
    "Weekend Getaway": "Relax with a two-night stay, complimentary breakfast and selected activities.",
    "Romantic Escape": "Enjoy a romantic stay with breakfast, spa access and a special dinner.",
    "Family Fun Package": "Perfect for families with breakfast, children's activities and late checkout.",
}
PACKAGE_INCLUDES = {
    "Weekend Getaway": ['2-night stay', 'Complimentary breakfast', 'Selected activities'],
    "Romantic Escape": ['2-night stay', 'Breakfast', 'Spa access', 'Special dinner'],
    "Family Fun Package": ['2-night stay', 'Breakfast', "Children's activities", 'Late checkout'],
}

# Room has no capacity/bed/amenity fields, so this holds them by room type.
ROOM_INFO = {
    "Standard Room": {
        "guests": 2,
        "features": ["Queen Bed", "Free Wi-Fi", "Air Conditioning"],
        "amenities": ["wifi"],
        "url_name": "room_details_standard",
    },
    "Deluxe Room": {
        "guests": 2,
        "features": ["King Bed", "Free Wi-Fi", "Breakfast Included"],
        "amenities": ["wifi", "breakfast"],
        "url_name": "room_details_deluxe",
    },
    "Executive Room": {
        "guests": 3,
        "features": ["King Bed", "Sea View", "Breakfast Included"],
        "amenities": ["breakfast", "sea_view"],
        "url_name": "room_details_executive",
    },
    "Family Suite": {
        "guests": 4,
        "features": ["2 Double Beds", "Sea View", "Breakfast Included"],
        "amenities": ["breakfast", "sea_view"],
        "url_name": "room_details_family",
    },
}
# Dev switch: False lets you click Pay without card details or the policy tick.
# Set to True before your demo / submission.
REQUIRE_PAYMENT_DETAILS = False



def _parse_guests(value):
    """'2' or '2 Guests' -> 2. Anything unusable -> None."""
    digits = ''.join(ch for ch in (value or '') if ch.isdigit())
    if not digits:
        return None
    n = int(digits)
    return n if 1 <= n <= 20 else None


def _parse_price_range(value):
    """'10000-15000' -> (10000, 15000). Anything unusable -> None."""
    try:
        low, high = (value or '').split('-')
        low, high = int(low), int(high)
    except ValueError:
        return None
    return (low, high) if 0 <= low <= high else None

def packages(request):
    cards = [
        {
            'slug': PACKAGE_SLUGS.get(p.p_name, f"package-{p.p_id}"),
            'id': p.p_id,
            'name': p.p_name,
            'description': PACKAGE_DESCRIPTIONS.get(p.p_name, ""),
            'includes': PACKAGE_INCLUDES.get(p.p_name, []),
            'nights': p.nights,
            'price': p.base_price,
            'valid_from': p.valid_from,
            'valid_to': p.valid_to,
            'image_path': PACKAGE_IMAGES.get(p.p_name, "images/Weekend.jpg"),
        }
        for p in Packages.objects.filter(is_active=True).order_by("base_price")
    ]
    return render(request, "hotel/packages.html", {"packages": cards})
 
def activities(request):
    cards = [
        {
            'id': a.act_id,
            'name': a.act_name,
            'description': ACTIVITY_DESCRIPTIONS.get(a.act_name, ""),
            'image_path': ACTIVITY_IMAGES.get(a.act_name, ACTIVITY_FALLBACK),
            'duration': a.duration,
            'location': a.location,
            'capacity': a.capacity,
            'price': a.price_per_person,
        }
        for a in Activity.objects.order_by("act_id")
    ]
    return render(request, "hotel/activities.html", {"activities": cards})
 
def events(request):
    cards = [
        {
            'id': e.event_id,
            'title': e.title,
            'description': EVENT_DESCRIPTIONS.get(e.title, ""),
            'image_path': EVENT_IMAGES.get(e.title, "images/wedding.webp"),
            'date': e.eventdate,
            'start_time': e.start_time,
            'end_time': e.end_time,
            'max_attendees': e.max_attendees,
            'price': e.price_per_person,
        }
        for e in Event.objects.order_by("event_id")
    ]
    return render(request, "hotel/events.html", {"events": cards})
 
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
            'image_path': 'images/standard-thumb-1.jpg',
            'url_name': 'room_details_standard'
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

    events = [
        {
            'id': e.event_id,
            'title': e.title,
            'description': EVENT_DESCRIPTIONS.get(e.title, ""),
            'image_path': EVENT_IMAGES.get(e.title, "images/wedding.webp"),
            'date': e.eventdate,
            'price': e.price_per_person,
        }
        for e in Event.objects.filter(eventdate__gte=date.today()).order_by("eventdate")
    ]
    return render(request, "hotel/home.html", {"rooms": rooms, "branches": Branch.objects.order_by("branch_name"), "events": events,"today": timezone.localdate().isoformat()})
    
 
 
def search_results(request):
    branch = request.GET.get('branch', '').strip()
    room_type = request.GET.get('room_type', '').strip()
    price_range = request.GET.get('price_range', '').strip()
    amenities = request.GET.getlist('amenities')
    check_in_raw = request.GET.get('check_in', '').strip()
    check_out_raw = request.GET.get('check_out', '').strip()
    sort = request.GET.get('sort', 'price_asc')
    if sort not in ('price_asc', 'price_desc'):
        sort = 'price_asc'

    guests = _parse_guests(request.GET.get('guests', ''))
    price_bounds = _parse_price_range(price_range)
    check_in = _parse_date(check_in_raw)
    check_out = _parse_date(check_out_raw)

    errors = []
    if check_in_raw and check_in is None:
        errors.append("That check-in date isn't valid.")
    if check_out_raw and check_out is None:
        errors.append("That check-out date isn't valid.")
    if check_in and check_in < date.today():
        errors.append("Check-in cannot be in the past.")
    if check_in and check_out and check_out <= check_in:
        errors.append("Check-out must be after check-in.")
    if errors:
        check_in = check_out = None

    rooms = []
    room_qs = Room.objects.select_related("branch").filter(
        room_status="available"
    ).order_by("price", "room_id")

    if branch:
        room_qs = room_qs.filter(branch__branch_name=branch)

    if room_type:
        room_qs = room_qs.filter(room_type=room_type)

    if price_bounds:
        low, high = price_bounds
        room_qs = room_qs.filter(price__gte=low, price__lte=high)

    if check_in and check_out:
        booked_rooms = Room_Item.objects.filter(
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).exclude(booking__bk_status="cancelled").values_list("room", flat=True)
        room_qs = room_qs.exclude(room_id__in=booked_rooms)

    if sort == 'price_desc':
        room_qs = room_qs.order_by("-price", "room_id")
    else:
        room_qs = room_qs.order_by("price", "room_id")
        
    for r in room_qs:
        info = ROOM_INFO.get(r.room_type)
        if info is None:
            continue    # a room type we have no display info for

        if guests and info['guests'] < guests:
            continue    # room is too small for this party

        if amenities and not set(amenities).issubset(info['amenities']):
            continue    # room is missing a ticked amenity

        rooms.append({
            'room_id': r.room_id,
            'name': r.room_type,
            'branch': r.branch.branch_name,
            'price': r.price,
            'guests': info['guests'],
            'features': info['features'],
            'amenities': info['amenities'],
            'image_path': ROOM_IMAGES.get(r.room_type, "images/deluxe.jpg"),
            'url_name': info['url_name'],
        })


 
    context = {
        'rooms': rooms,
        'branch': branch,
        'check_in': check_in,
        'check_out': check_out,
        'guests': guests,
        'check_in_raw': check_in_raw,
        'check_out_raw': check_out_raw,
        'branches': Branch.objects.order_by('branch_name'),
        'sort': sort,
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
    room = Room.objects.filter(
        room_type="Executive Room", room_status="available"
    ).order_by("room_id").first()
    return render(request, "hotel/room_details_executive.html", {"room": room})
 
 
def room_details_family(request):
    room = Room.objects.filter(
        room_type="Family Suite", room_status="available"
    ).order_by("room_id").first()
    return render(request, "hotel/room_details_family.html", {"room": room})
 
 
def login(request):
    return render(request, "hotel/login.html")
 
 
def register(request):
    return render(request, "hotel/register.html")

@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect("home")
 
def _hours_until_checkin(b):
    """Hours from now until the start of the booking's check-in date.
    Bookings only store dates, so check-in is treated as 00:00 on that day."""
    start = datetime.combine(b.check_in, dtime.min)
    if settings.USE_TZ:
        start = timezone.make_aware(start)
        now = timezone.localtime()
    else:
        now = datetime.now()
    return (start - now).total_seconds() / 3600
 
 
def _can_cancel(b):
    return (b.bk_status in ("pending", "confirmed")
            and _hours_until_checkin(b) >= CANCEL_WINDOW_HOURS)
 

 
def cancel_booking(request, booking_id):
    if request.method != "POST":
        return redirect("customer_dashboard")
 
    customer = get_current_customer(request)
    if customer is None:
        return redirect("login")
 
    b = get_object_or_404(Booking, pk=booking_id, customer=customer)
 
    if b.bk_status not in ("pending", "confirmed"):
        messages.error(request, "That booking can no longer be cancelled.")
    elif not _can_cancel(b):
        messages.error(
            request,
            f"Bookings can only be cancelled up to {CANCEL_WINDOW_HOURS} hours before check-in.",
        )
    else:
        b.bk_status = "cancelled"
        b.save(update_fields=["bk_status", "updated_at"])
        messages.success(request, f"Booking #{b.bk_id} has been cancelled.")
    return redirect("customer_dashboard")
 
 
def book_again(request, booking_id):
    customer = get_current_customer(request)
    if customer is None:
        return redirect("login")
 
    b = get_object_or_404(
        Booking.objects.prefetch_related("booking_items"),
        pk=booking_id, customer=customer,
    )
    title = _booking_card(b, date.today())["title"]
 
    items = list(b.booking_items.all())
    main = next((i for i in items if i.bi_type != "activity"), items[0] if items else None)
    tab = {
        "room": "rooms", "package": "packages",
        "event": "events", "activity": "activities",
    }.get(main.bi_type if main else "", "rooms")
 
    # same party size, but blank dates: the old ones are in the past or cancelled
    request.session["search"] = {"checkin": "", "checkout": "", "guests": b.no_of_guests}
    request.session.modified = True
 
    if tab == "events":
        messages.info(request, f"Select {title} again, or pick another event.")
    else:
        messages.info(request, f"Choose your new dates, then select {title} again.")
    return redirect(f"{reverse('booking')}?tab={tab}")
 
 
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

def customer_profile_edit(request):
    customer = get_current_customer(request)
    if customer is None:
        return redirect("customer_profile")

    fields = ("first_name", "last_name", "email", "phone", "address", "dob")
    form = {
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "email": customer.email,
        "phone": customer.phone,
        "address": customer.address,
        "dob": customer.dob.isoformat() if customer.dob else "",
    }
    errors = []

    if request.method == "POST":
        form = {f: request.POST.get(f, "").strip() for f in fields}

        if not form["first_name"]:
            errors.append("First name is required.")
        elif len(form["first_name"]) > 150:
            errors.append("First name is too long (150 characters maximum).")

        if not form["last_name"]:
            errors.append("Last name is required.")
        elif len(form["last_name"]) > 150:
            errors.append("Last name is too long (150 characters maximum).")

        try:
            validate_email(form["email"])
            if len(form["email"]) > 254:
                raise ValidationError("too long")
        except ValidationError:
            errors.append("Enter a valid email address.")

        if form["phone"] and not re.fullmatch(r"[0-9 +().\-xX]{6,20}", form["phone"]):
            errors.append("Phone must be 6 to 20 characters: digits, spaces, + ( ) . - or x for an extension.")

        if len(form["address"]) > 255:
            errors.append("Address is too long (255 characters maximum).")

        dob = None
        if form["dob"]:
            try:
                dob = date.fromisoformat(form["dob"])
            except ValueError:
                errors.append("Enter a valid date of birth.")
            else:
                if dob >= date.today():
                    errors.append("Date of birth must be in the past.")

        if not errors:
            customer.first_name = form["first_name"]
            customer.last_name = form["last_name"]
            customer.email = form["email"]
            customer.phone = form["phone"]
            customer.address = form["address"]
            customer.dob = dob
            customer.save(update_fields=[
                "first_name", "last_name", "email", "phone", "address", "dob",
            ])
            messages.success(request, "Your details were updated.")
            return redirect("customer_profile")

    context = {"customer": customer, "form": form, "errors": errors}
    return render(request, "hotel/customer_profile_edit.html", context)

def customer_profile(request):
    customer = get_current_customer(request)
 
    if customer is None:
        return render(request, "hotel/customer_profile.html", {"no_customers": True})
 
    context = {"customer": customer}
    return render(request, "hotel/customer_profile.html", context)
 
 
def customer_support(request):
    customer = get_current_customer(request)
    if customer is None:
        return redirect("login")

    today = date.today()
    my_bookings = list(customer.bookings.select_related("branch").prefetch_related(
        "booking_items"
    ).order_by("-check_in"))
    booking_options = [
        {
            "id": b.pk,
            "label": f"BK-{b.bk_id:05d} · {_booking_card(b, today)['title']} · {b.check_in:%d %b %Y}",
        }
        for b in my_bookings
    ]

    valid_topics = {value for value, _ in Support_Ticket.CATEGORY_CHOICES}
    form = {"category": "other", "booking": "", "subject": "", "message": ""}
    errors = []

    if request.method == "POST":
        form = {key: request.POST.get(key, "").strip() for key in form}

        if form["category"] not in valid_topics:
            errors.append("Choose a topic.")
        if not form["subject"]:
            errors.append("Add a short subject.")
        elif len(form["subject"]) > 150:
            errors.append("The subject is too long (150 characters maximum).")
        if len(form["message"]) < 10:
            errors.append("Tell us a little more: the message needs at least 10 characters.")
        elif len(form["message"]) > 2000:
            errors.append("The message is too long (2000 characters maximum).")

        booking = None
        if form["booking"]:
            # only ever one of this customer's own bookings
            booking = next((b for b in my_bookings if str(b.pk) == form["booking"]), None)
            if booking is None:
                errors.append("Choose one of your own bookings, or leave it blank.")

        if not errors:
            Support_Ticket.objects.create(
                customer=customer,
                booking=booking,
                category=form["category"],
                subject=form["subject"],
                message=form["message"],
            )
            messages.success(request, "Thanks, your message has been sent. Replies will appear below.")
            return redirect("customer_support")

    context = {
        "customer": customer,
        "form": form,
        "errors": errors,
        "topics": Support_Ticket.CATEGORY_CHOICES,
        "booking_options": booking_options,
        "tickets": customer.support_tickets.select_related("booking")[:10],
        "branch": Branch.objects.order_by("branch_id").first(),
    }
    return render(request, "hotel/customer_support.html", context)
 
 
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
    today = date.today()
    yesterday = today - timedelta(days=1)
    live = Booking.objects.exclude(bk_status__iexact="cancelled")

    checkin = _card(live.filter(check_in=today), live.filter(check_in=yesterday))
    checkout = _card(live.filter(check_out=today), live.filter(check_out=yesterday))

    bookings = list(Booking.objects.select_related("customer").order_by("-created_at")[:10])
    for b in bookings:
        b.nights = (b.check_out - b.check_in).days
        b.first_room = Room_Item.objects.filter(booking=b).select_related("room").first()

    context = {"checkin": checkin, "checkout": checkout, "bookings": bookings}
    return render(request, "hotel/staff_dashboard.html", context)
 
 
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
    today = timezone.localdate()
    period = request.GET.get("period", "month")
    if period == "30days":
        start_date = today - timedelta(days=29)
        period_label = "Last 30 Days"
    elif period == "quarter":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = date(today.year, quarter_start_month, 1)
        period_label = "This Quarter"
    elif period == "year":
        start_date = date(today.year, 1, 1)
        period_label = "This Year"
    else:
        period = "month"
        start_date = today.replace(day=1)
        period_label = "This Month"

    bookings = Booking.objects.filter(
        bk_date__gte=start_date, bk_date__lte=today
    ).exclude(bk_status="cancelled")
    total_revenue = bookings.aggregate(total=Sum("estimated_sum"))["total"] or Decimal("0")
    booking_count = bookings.count()

    room_items = Room_Item.objects.filter(
        booking__bk_date__gte=start_date,
        booking__bk_date__lte=today,
    ).exclude(booking__bk_status="cancelled")
    room_totals = room_items.values("room__room_type").annotate(
        bookings=Count("booking", distinct=True),
        revenue=Sum("price"),
        average_rate=Avg("price"),
    ).order_by("room__room_type")

    period_days = (today - start_date).days + 1
    occupied_rooms_by_category = {}
    occupancy_items = Room_Item.objects.filter(
        check_in__lt=today + timedelta(days=1), check_out__gt=start_date
    ).exclude(booking__bk_status="cancelled")
    for room_type, room_id, check_in, check_out in occupancy_items.values_list(
        "room__room_type", "room_id", "check_in", "check_out"
    ):
        overlap_start = max(check_in, start_date)
        overlap_end = min(check_out, today + timedelta(days=1))
        for night_offset in range(max((overlap_end - overlap_start).days, 0)):
            night = overlap_start + timedelta(days=night_offset)
            occupied_rooms_by_category.setdefault(room_type, {}).setdefault(night, set()).add(room_id)

    room_counts = dict(
        Room.objects.values_list("room_type").annotate(total=Count("room_id"))
    )
    occupancy_rows = []
    total_inventory_nights = sum(room_counts.values()) * period_days
    category_room_nights = {
        room_type: sum(len(room_ids) for room_ids in nights.values())
        for room_type, nights in occupied_rooms_by_category.items()
    }
    total_room_nights = sum(category_room_nights.values())
    for room_type, room_count in sorted(room_counts.items()):
        occupied_nights = category_room_nights.get(room_type, 0)
        rate = (occupied_nights / (room_count * period_days) * 100) if room_count and period_days else 0
        occupancy_rows.append({"name": room_type, "rate": rate})

    room_revenue = sum((row["revenue"] or Decimal("0") for row in room_totals), Decimal("0"))
    booked_room_nights = sum(
        max((check_out - check_in).days, 0)
        for check_in, check_out in room_items.values_list("check_in", "check_out")
    )
    adr = room_revenue / booked_room_nights if booked_room_nights else Decimal("0")

    def money(value):
        return f"Rs {value:,.2f}"

    revenue_rows = [{
        "category": row["room__room_type"],
        "bookings": row["bookings"],
        "average_rate": money(row["average_rate"] or Decimal("0")),
        "revenue": money(row["revenue"] or Decimal("0")),
    } for row in room_totals]

    context = {
        "title": "Reports & Analytics",
        "period": period,
        "period_label": period_label,
        "start_date": start_date,
        "today": today,
        "total_revenue": money(total_revenue),
        "booking_count": booking_count,
        "occupancy_rate": (total_room_nights / total_inventory_nights * 100) if total_inventory_nights else 0,
        "adr": money(adr),
        "revenue_rows": revenue_rows,
        "occupancy_rows": occupancy_rows,
    }
    return render_admin_page(request, "hotel/reports.html", context)
 
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
 
        if REQUIRE_PAYMENT_DETAILS and (not card_number or not agree):
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
 
    context = {
        "cart": cart,
        "cart_total": _cart_total(cart),
        "error": error,
        "customer": get_current_customer(request),
    }
    return render(request, "hotel/cart_payment.html", context)
 
 
def booking_confirmation(request):
    booking_id = request.session.get("last_booking_id")
    booking_obj = None
    if booking_id:
        booking_obj = Booking.objects.filter(pk=booking_id).select_related(
            "customer"
        ).prefetch_related("booking_items").first()
 
    return render(request, "hotel/booking_confirmation.html", {"booking": booking_obj})
 
def loyalty_summary(customer, bookings=None, today=None):
    """One place that works out points, so every page shows the same numbers."""
    today = today or date.today()
    if bookings is None:
        bookings = customer.bookings.prefetch_related("booking_items").order_by("-check_in")
 
    loyalty = customer.loyalty
    multiplier = Decimal(str(loyalty.multiplier_rate)) if loyalty else Decimal("1")
    tier_name = loyalty.tier if loyalty else None
 
    entries, earned, pending = [], 0, 0
    for b in bookings:
        if b.bk_status == "cancelled":
            continue
        points = int((Decimal(str(b.estimated_sum)) / POINT_UNIT) * multiplier)   # rounds down
        credited = b.check_out < today
        if credited:
            earned += points
        else:
            pending += points
        entries.append({"booking": b, "points": points, "earned": credited})
    entries.sort(key=lambda e: e["booking"].check_in, reverse=True)
 
    names = [n.lower() for n, _ in TIERS]
    idx = names.index(tier_name.lower()) if tier_name and tier_name.lower() in names else None
    next_tier = to_next = None
    top_tier, progress = False, 0
    if idx is not None:
        if idx + 1 < len(TIERS):
            next_tier, next_at = TIERS[idx + 1]
            this_at = TIERS[idx][1]
            to_next = max(0, next_at - earned)
            progress = max(0, min(100, int((earned - this_at) * 100 / (next_at - this_at))))
        else:
            top_tier, progress = True, 100
 
    return {
        "entries": entries,
        "earned": earned,
        "pending": pending,
        "multiplier": float(multiplier),
        "next_tier": next_tier,
        "to_next": to_next,
        "top_tier": top_tier,
        "progress": progress,
    }
 
 
def _tier_rows(customer):
    """The tier ladder for the rewards page, using the multipliers stored in Loyalty."""
    needed = {n.lower(): pts for n, pts in TIERS}
    mine = customer.loyalty.tier.lower() if customer.loyalty else None
    rows = [{
        "name": t.tier,
        "multiplier": t.multiplier_rate,
        "threshold": needed.get(t.tier.lower()),
        "current": t.tier.lower() == mine,
    } for t in Loyalty.objects.all()]
    rows.sort(key=lambda r: (r["threshold"] is None, r["threshold"] or 0, r["multiplier"]))
    return rows
 
def _booking_card(b, today):
    """Everything the dashboard needs to draw one booking."""
    items = list(b.booking_items.all())
    main = next((i for i in items if i.bi_type != "activity"), items[0] if items else None)
 
    title, image = f"Booking #{b.bk_id}", ACTIVITY_FALLBACK
    if main:
        title = main.description or title
        try:
            if main.bi_type == "room":
                room = main.room_item.room
                title, image = room.room_type, ROOM_IMAGES.get(room.room_type, "images/deluxe.jpg")
            elif main.bi_type == "package":
                pkg = main.package_item.package
                title, image = pkg.p_name, PACKAGE_IMAGES.get(pkg.p_name, "images/Weekend.jpg")
            elif main.bi_type == "event":
                ev = main.event_item.event
                title, image = ev.title, EVENT_IMAGES.get(ev.title, "images/wedding.webp")
            elif main.bi_type == "activity":
                act = main.activity_item.activity
                title, image = act.act_name, ACTIVITY_IMAGES.get(act.act_name, ACTIVITY_FALLBACK)
        except ObjectDoesNotExist:
            pass
 
    status = b.bk_status
    bookable_ahead = status in ("pending", "confirmed") and b.check_in > today
    return {
        "booking": b,
        "title": title,
        "image": image,
        "extras": [i.description for i in items if i is not main],
        "status": status,
        "status_label": status.title(),
        "single_day": b.check_in == b.check_out,
        "can_modify": bookable_ahead,
        "can_cancel": bookable_ahead,
        "can_checkin": status == "confirmed" and b.check_in <= today <= b.check_out,
    }
 
 
def customer_dashboard(request):
    customer = get_current_customer(request)
    if customer is None:
        return render(request, "hotel/customer_dashboard.html", {"no_customers": True})
 
    today = date.today()
    bookings = customer.bookings.select_related("branch").prefetch_related(
        "booking_items"
    ).order_by("check_in")
    cards = [_booking_card(b, today) for b in bookings]
 
    active = [c for c in cards if c["status"] != "cancelled"]
    upcoming = [c for c in active if c["booking"].check_out >= today]
    past = [c for c in active if c["booking"].check_out < today][::-1]
    cancelled = [c for c in cards if c["status"] == "cancelled"]
 
    points = loyalty_summary(customer, bookings, today)
 
    context = {
        "customer": customer,
        "upcoming": upcoming,
        "past": past,
        "cancelled": cancelled,
        "stays_count": len(active),
        "points": points["earned"],
        "next_tier": points["next_tier"],
        "to_next": points["to_next"],
        "top_tier": points["top_tier"],
    }
    return render(request, "hotel/customer_dashboard.html", context)
 
 
def customer_rewards(request):
    customer = get_current_customer(request)
    if customer is None:
        return render(request, "hotel/customer_rewards.html", {"no_customers": True})
 
    today = date.today()
    bookings = customer.bookings.select_related("branch").prefetch_related(
        "booking_items"
    ).order_by("-check_in")
    points = loyalty_summary(customer, bookings, today)
 
    history = []
    for e in points["entries"]:
        card = _booking_card(e["booking"], today)
        history.append({**e, "title": card["title"], "single_day": card["single_day"]})
 
    context = {
        "customer": customer,
        "history": history,
        "tier_rows": _tier_rows(customer),
        "earned": points["earned"],
        "pending": points["pending"],
        "multiplier": points["multiplier"],
        "next_tier": points["next_tier"],
        "to_next": points["to_next"],
        "top_tier": points["top_tier"],
        "progress": points["progress"],
    }
    return render(request, "hotel/customer_rewards.html", context)



# ---------------- Admin and staff pages ----------------
from datetime import date, timedelta
from decimal import Decimal
from django.contrib import messages
from django.db.models import F, Max, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Booking, Room_Item, User


def _total(qs):
    return qs.aggregate(t=Sum("estimated_sum"))["t"] or Decimal("0")


def _card(today_qs, yesterday_qs):
    now = _total(today_qs)
    before = _total(yesterday_qs)
    change = now - before
    pct = (change / before * 100) if before else Decimal("0")
    return {
        "total": now,
        "sign": "+" if change >= 0 else "-",
        "delta": abs(change),
        "pct": abs(pct),
        "updated": today_qs.aggregate(m=Max("updated_at"))["m"],
    }


def admin_dashboard(request):
    today = date.today()
    yesterday = today - timedelta(days=1)
    live = Booking.objects.exclude(bk_status__iexact="cancelled")

    cards = [
        {"label": "\u2192] Check-In", **_card(live.filter(check_in=today), live.filter(check_in=yesterday))},
        {"label": "Check-out", **_card(live.filter(check_out=today), live.filter(check_out=yesterday))},
        {"label": "New Bookings", **_card(live.filter(bk_date=today), live.filter(bk_date=yesterday))},
    ]

    # Weekly chart: Saturday to Friday, like the Figma
    week_start = today - timedelta(days=(today.weekday() - 5) % 7)
    week_days = [week_start + timedelta(days=i) for i in range(7)]
    per_day = {
        row["bk_date"]: row["t"]
        for row in live.filter(bk_date__in=week_days).values("bk_date").annotate(t=Sum("estimated_sum"))
    }
    chart = [{"label": d.strftime("%a"), "value": per_day.get(d, Decimal("0"))} for d in week_days]
    biggest = max(c["value"] for c in chart) or 1
    for c in chart:
        c["height"] = int(c["value"] / biggest * 100)

    # Latest bookings table
    bookings = list(Booking.objects.select_related("customer").order_by("-created_at")[:10])
    for b in bookings:
        b.nights = (b.check_out - b.check_in).days
        b.first_room = Room_Item.objects.filter(booking=b).select_related("room").first()

    context = {
        "cards": cards,
        "revenue": _total(live),
        "chart": chart,
        "bookings": bookings,
    }
    return render(request, "hotel/admin_dashboard.html", context)


def admin_profile(request):
    return render(request, "hotel/admin_profile.html")


def admin_action(request):
    staff = list(
        User.objects.filter(
            Q(employee__isnull=False) | Q(is_staff=True) | Q(is_superuser=True)
        )
        .distinct()
        .order_by(F("last_login").desc(nulls_last=True), "first_name")
    )

    # make sure whoever is logged in right now is in the list
    me = request.user if request.user.is_authenticated else None
    if me and not any(s.pk == me.pk for s in staff):
        staff.insert(0, me)

    return render(request, "hotel/admin_action.html", {"staff": staff})


def staff_profile(request):
    return render(request, "hotel/staff_profile.html")

def staff_status(request):
    today = date.today()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        if not (1 <= month <= 12 and today.year - 10 <= year <= today.year + 10):
            raise ValueError
    except ValueError:
        year, month = today.year, today.month

    staff = list(
        User.objects.filter(
            Q(employee__isnull=False) | Q(is_staff=True) | Q(is_superuser=True)
        )
        .distinct()
        .order_by(F("last_login").desc(nulls_last=True), "first_name")
    )

    context = {
        "weeks": calendar.Calendar(firstweekday=6).monthdayscalendar(year, month),
        "month": month,
        "year": year,
        "months": [(i, calendar.month_name[i]) for i in range(1, 13)],
        "years": range(today.year - 10, today.year + 11),
        "today": today,
        "is_this_month": year == today.year and month == today.month,
        "staff": staff,
    }
    return render(request, "hotel/staff_status.html", context)


def _can_manage(request):
    return request.user.is_authenticated and request.user.is_staff


@require_POST
def staff_edit(request, user_id):
    if not _can_manage(request):
        messages.error(request, "Log in as an administrator to edit staff.")
        return redirect("admin_action")
    person = get_object_or_404(User, pk=user_id)
    person.first_name = request.POST.get("first_name", "").strip()
    person.last_name = request.POST.get("last_name", "").strip()
    person.email = request.POST.get("email", "").strip()
    person.phone = request.POST.get("phone", "").strip()
    person.save(update_fields=["first_name", "last_name", "email", "phone"])
    messages.success(request, f"{person.get_full_name() or person.username} was updated.")
    return redirect("admin_action")


@require_POST
def staff_delete(request, user_id):
    if not _can_manage(request):
        messages.error(request, "Log in as an administrator to delete staff.")
        return redirect("admin_action")
    person = get_object_or_404(User, pk=user_id)
    if person.pk == request.user.pk:
        messages.error(request, "You can't delete your own account.")
    elif person.is_superuser:
        messages.error(request, "Superuser accounts can't be deleted here.")
    else:
        name = person.get_full_name() or person.username
        person.delete()
        messages.success(request, f"{name} was deleted.")
    return redirect("admin_action")
