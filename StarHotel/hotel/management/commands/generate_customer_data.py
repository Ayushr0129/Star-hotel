"""
Django management command: generate_customer_data

Creates DEMO customers and realistic bookings that look like the ones the
real checkout produces (same item types, same price maths, same descriptions):

  - room stays        (Room_Item, optional Activity_Item add-ons inside the dates)
  - package stays     (Package_Item, length = package.nights, optional add-ons)
  - events            (Event_Item, single day = the event's date)
  - activity-only     (Activity_Item, single day)

READ-ONLY for Loyalty, Branch, Room, Packages, Event and Activity. It only uses
what already exists, and only creates Customer / Booking / *_Item rows.

Demo customers get the username prefix "demo." so --clear only ever removes
demo data, never real customers who registered through the site.

PLACE AT:  hotel/management/commands/generate_customer_data.py

RUN
---
python manage.py generate_customer_data
python manage.py generate_customer_data --customers 30 --clear
python manage.py generate_customer_data --clear-all     (removes EVERY customer)

All demo customers have the password:  TestPass123!
"""

import random
import re
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

try:
    from faker import Faker
except ImportError:
    raise SystemExit("Missing dependency: run `pip install faker`")

from ...models import (  # noqa
    Customer, Loyalty, Branch, Room, Packages, Event, Activity,
    Booking, Room_Item, Package_Item, Event_Item, Activity_Item,
)

fake = Faker()

DEMO_PREFIX = "demo."
DEMO_PASSWORD = "TestPass123!"
PAYMENT_METHODS = ["credit_card", "debit_card", "bank_transfer", "e-wallet"]

# Room has no capacity field, so mirror the spec text used on the site.
ROOM_CAPACITY = {
    "Standard Room": 2,
    "Deluxe Room": 2,
    "Executive Room": 3,
    "Family Suite": 4,
}


class Command(BaseCommand):
    help = "Generate demo customers and realistic bookings"

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=20,
                            help="Number of demo customers to create (default: 20)")
        parser.add_argument("--bookings-per-customer", type=int, default=3,
                            help="Max bookings per customer (default: 3)")
        parser.add_argument("--clear", action="store_true",
                            help="Delete existing DEMO customers (and their bookings) first")
        parser.add_argument("--clear-all", action="store_true",
                            help="Delete EVERY customer and their bookings first")
        parser.add_argument("--seed", type=int, default=None,
                            help="Random seed for reproducible output")

    def handle(self, *args, **options):
        if options["seed"] is not None:
            random.seed(options["seed"])
            Faker.seed(options["seed"])

        if options["clear_all"]:
            self._clear(Customer.objects.all(), "ALL customers")
        elif options["clear"]:
            self._clear(Customer.objects.filter(username__startswith=DEMO_PREFIX),
                        "demo customers")

        catalogue = self._load_catalogue()

        made_customers = made_bookings = 0
        with transaction.atomic():
            for _ in range(options["customers"]):
                customer = self._create_customer(catalogue["loyalties"])
                made_customers += 1
                for _ in range(random.randint(0, options["bookings_per_customer"])):
                    if self._create_booking(customer, catalogue):
                        made_bookings += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. {made_customers} customers, {made_bookings} bookings. "
            f"Password for all demo customers: {DEMO_PASSWORD}"
        ))

    # ---------- housekeeping ----------

    def _clear(self, queryset, label):
        count = queryset.count()
        queryset.delete()   # cascades to bookings and their items
        self.stdout.write(f"Removed {count} ({label}).")

    def _load_catalogue(self):
        cat = {
            "loyalties": list(Loyalty.objects.all()),
            "branches": list(Branch.objects.all()),
            "rooms": list(Room.objects.select_related("branch")),
            "packages": list(Packages.objects.filter(is_active=True)),
            "events": list(Event.objects.all()),
            "activities": list(Activity.objects.all()),
        }
        self.stdout.write("Using existing catalogue (read-only): " +
                          ", ".join(f"{len(v)} {k}" for k, v in cat.items()))
        for name in ("branches", "rooms", "packages", "events", "activities"):
            if not cat[name]:
                self.stdout.write(self.style.WARNING(
                    f"  No {name} found, so no bookings that need {name} will be made."))
        return cat

    # ---------- customers ----------

    def _create_customer(self, loyalties):
        first, last = fake.first_name(), fake.last_name()
        slug = lambda s: re.sub(r"[^a-z0-9]", "", s.lower()) or "x"   # noqa: E731
        while True:
            username = f"{DEMO_PREFIX}{slug(first)}.{slug(last)}.{random.randint(1000, 9999)}"
            if not Customer.objects.filter(username=username).exists():
                break
        return Customer.objects.create_user(
            username=username,
            email=fake.unique.email(),
            password=DEMO_PASSWORD,
            first_name=first,
            last_name=last,
            dob=fake.date_of_birth(minimum_age=18, maximum_age=80),
            phone=fake.phone_number()[:20],
            address=fake.address().replace("\n", ", ")[:255],
            nid=fake.unique.bothify(text="??######???"),
            loyalty=random.choice(loyalties) if loyalties else None,
        )

    # ---------- bookings ----------

    def _create_booking(self, customer, cat):
        today = date.today()

        kinds, weights = [], []
        for kind, key, weight in (("room", "rooms", 50), ("package", "packages", 20),
                                  ("event", "events", 15), ("activity", "activities", 15)):
            if cat[key]:
                kinds.append(kind)
                weights.append(weight)
        if not kinds or not cat["branches"] and not cat["rooms"]:
            return None
        kind = random.choices(kinds, weights)[0]

        start = today + timedelta(days=random.randint(-150, 150))
        items = []          # dicts: type, price, description, extra (model kwargs)
        booking_type = "stay"

        if kind == "room":
            room = random.choice(cat["rooms"])
            guests = random.randint(1, ROOM_CAPACITY.get(room.room_type, 2))
            nights = random.randint(1, 7)
            ci, co = start, start + timedelta(days=nights)
            branch = room.branch
            items.append({
                "type": "room", "price": room.price * nights,
                "description": f"{room.room_type}, {room.branch.branch_name}",
                "extra": {"room": room, "check_in": ci, "check_out": co},
            })

        elif kind == "package":
            pkg = random.choice(cat["packages"])
            guests = random.randint(1, 4)
            ci, co = start, start + timedelta(days=pkg.nights)
            branch = random.choice(cat["branches"]) if cat["branches"] else None
            items.append({
                "type": "package", "price": pkg.base_price * guests,
                "description": pkg.p_name,
                "extra": {"package": pkg, "no_of_guests": guests},
            })

        elif kind == "event":
            ev = random.choice(cat["events"])
            guests = random.randint(1, max(1, min(30, ev.max_attendees)))
            ci = co = ev.eventdate
            booking_type = "event"
            branch = random.choice(cat["branches"]) if cat["branches"] else None
            items.append({
                "type": "event", "price": ev.price_per_person * guests,
                "description": ev.title,
                "extra": {"event": ev, "no_of_guests": guests},
            })

        else:  # activity only
            act = random.choice(cat["activities"])
            guests = random.randint(1, max(1, min(4, act.capacity)))
            ci = co = start
            booking_type = "activity"
            branch = random.choice(cat["branches"]) if cat["branches"] else None
            items.append(self._activity_item(act, guests, ci))

        if branch is None:
            return None

        # activities booked on top of a stay, always inside the stay's dates
        if booking_type == "stay" and cat["activities"] and random.random() < 0.4:
            for act in random.sample(cat["activities"], k=min(len(cat["activities"]),
                                                              random.randint(1, 2))):
                day = ci + timedelta(days=random.randint(0, (co - ci).days))
                items.append(self._activity_item(act, min(guests, act.capacity), day))

        booking = Booking.objects.create(
            booking_type=booking_type,
            no_of_guests=guests,
            check_in=ci,
            check_out=co,
            bk_status=self._status(ci, co, today),
            estimated_sum=sum(i["price"] for i in items),
            customer=customer,
            branch=branch,
        )

        for item in items:
            common = dict(
                bi_type=item["type"], price=item["price"],
                payment_method=random.choice(PAYMENT_METHODS),
                description=item["description"], booking=booking,
            )
            model = {"room": Room_Item, "package": Package_Item,
                     "event": Event_Item, "activity": Activity_Item}[item["type"]]
            model.objects.create(**common, **item["extra"])
        return booking

    @staticmethod
    def _activity_item(act, guests, day):
        return {
            "type": "activity", "price": act.price_per_person * guests,
            "description": f"{act.act_name}, {act.location}",
            "extra": {"activity": act, "activity_date": day, "no_of_guests": guests},
        }

    @staticmethod
    def _status(ci, co, today):
        if co < today:
            return "cancelled" if random.random() < 0.15 else "completed"
        if ci <= today:
            return "confirmed"
        return random.choices(["confirmed", "pending", "cancelled"], [60, 25, 15])[0]