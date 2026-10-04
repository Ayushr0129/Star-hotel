"""
Django management command: generate_reference_data

Seeds the reference/catalog data your booking flow depends on:
  - Loyalty tiers
  - Branches
  - Rooms      (names/prices match the ones shown on the home page)
  - Packages   (names/prices match the ones shown on the home page)
  - Events

Safe to rerun: uses get_or_create keyed on natural names, so running it
multiple times won't create duplicates. Use --clear if you deliberately
want to wipe and reseed everything it owns.

INSTALL
-------
Same spot as generate_customer_data.py:
  hotel/management/commands/generate_reference_data.py

RUN
---
python manage.py generate_reference_data
python manage.py generate_reference_data --clear
"""

import random
from datetime import timedelta, date

from django.core.management.base import BaseCommand
from django.db import transaction
from ...models import Loyalty, Branch, Room, Packages, Event, Activity  # noqa

try:
    from faker import Faker
except ImportError:
    raise SystemExit("Missing dependency: run `pip install faker --break-system-packages`")

from ...models import Loyalty, Branch, Room, Packages, Event  # noqa

fake = Faker()

LOYALTY_TIERS = [
    ("Bronze", 0.00, 1.0),
    ("Silver", 0.05, 1.25),
    ("Gold", 0.10, 1.5),
    ("Platinum", 0.15, 2.0),
]

BRANCH_CITIES = [
    ("Port Louis Grand", "Port Louis"),
    ("Grand Baie Resort", "Grand Baie"),
    ("Flic-en-Flac Shores", "Flic-en-Flac"),
    ("Belle Mare Bay", "Belle Mare"),
]

# Matches the hardcoded cards on home.html exactly (name, price).
# Every branch gets one of each room type at this fixed price, so whatever
# a customer sees on the home page is exactly what exists in the booking
# flow too.
ROOM_TYPES = [
    ("Deluxe Room", 15000),
    ("Standard Room", 9500),
    ("Studio Room", 12500),
    ("Executive Room", 18000),
]

# Matches the "Packages & Promotions" cards on home.html exactly.
PACKAGE_DEFS = [
    ("Weekend Getaway", 9500),
    ("Romantic Escape", 12000),
    ("Family Fun Package", 15500),
]

# home.html's "Activities" section (Spa/Golf/Tennis/Swimming) uses a
# separate Activity model that has no link to Booking_Item in models.py,
# so those can't be seeded as bookable Events. These Event entries instead
# match what was already hardcoded in the booking.html events tab.
EVENT_TITLES = [
    ("Garden Wedding Package", "wedding", 2500),
    ("Birthday Celebration Package", "birthday", 3500),
    ("Corporate Retreat Package", "corporate", 4000),
]

# (name, location, capacity, duration in minutes, price per person)
# duration 0 = "Flexible duration", price 0 = "Complimentary" on the booking page.
# Names must match the home page exactly, since the booking page uses them
# to find each activity's image and description.
ACTIVITY_DEFS = [
    ("Spa & Wellness",     "Hotel Spa",     4, 60, 2500),
    ("Golf Experience",    "Hotel Grounds", 4, 90, 1800),
    ("Tennis session",     "Tennis Courts", 4, 60, 1200),
    ("Swimming & Leisure", "Pool Area",    20,  0,    0),
]

class Command(BaseCommand):
    help = "Seed reference data: Loyalty, Branch, Room, Packages, Event"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true",
                             help="Delete existing rows in these tables before reseeding")
        parser.add_argument("--seed", type=int, default=None,
                             help="Random seed for reproducible output")

    def handle(self, *args, **options):
        if options["seed"] is not None:
            random.seed(options["seed"])
            Faker.seed(options["seed"])

        if options["clear"]:
            self._clear()

        with transaction.atomic():
            loyalties = self._create_loyalty_tiers()
            branches = self._create_branches()
            rooms = self._create_rooms(branches)
            packages = self._create_packages()
            events = self._create_events()
            activities = self._create_activities()

        self.stdout.write(self.style.SUCCESS(
            f"Done. {len(loyalties)} loyalty tiers, {len(branches)} branches, "
            f"{len(rooms)} rooms, {len(packages)} packages, {len(events)} events."
            f"{len(activities)} activities."
        ))

    def _clear(self):
        self.stdout.write("Clearing existing reference data (Room, Branch, Packages, "
                           "Event, Loyalty)...")
        Room.objects.all().delete()
        Branch.objects.all().delete()
        Packages.objects.all().delete()
        Event.objects.all().delete()
        Loyalty.objects.all().delete()

    def _create_loyalty_tiers(self):
        tiers = []
        for tier, discount, multiplier in LOYALTY_TIERS:
            obj, _ = Loyalty.objects.get_or_create(
                tier=tier,
                defaults={"discount_rate": discount, "multiplier_rate": multiplier},
            )
            tiers.append(obj)
        self.stdout.write(f"  Loyalty tiers: {len(tiers)}")
        return tiers

    def _create_branches(self):
        branches = []
        for name, city in BRANCH_CITIES:
            obj, _ = Branch.objects.get_or_create(
                branch_name=name,
                defaults={
                    "tel_no": fake.phone_number()[:20],
                    "street": fake.street_address()[:150],
                    "city": city,
                    "zipcode": fake.postcode()[:10],
                },
            )
            branches.append(obj)
        self.stdout.write(f"  Branches: {len(branches)}")
        return branches

    def _create_rooms(self, branches):
        rooms = []
        for branch in branches:
            for room_type, price in ROOM_TYPES:
                obj, created = Room.objects.get_or_create(
                    branch=branch,
                    room_type=room_type,
                    defaults={"room_status": "available", "price": price},
                )
                if created:
                    rooms.append(obj)
        total_rooms = Room.objects.count()
        self.stdout.write(f"  Rooms created this run: {len(rooms)} (total now: {total_rooms})")
        return rooms

    def _create_packages(self):
        packages = []
        for name, price in PACKAGE_DEFS:
            valid_from = date.today() - timedelta(days=random.randint(0, 90))
            valid_to = valid_from + timedelta(days=random.randint(180, 365))
            obj, _ = Packages.objects.get_or_create(
                p_name=name,
                defaults={
                    "base_price": price,
                    "is_active": True,
                    "valid_from": valid_from,
                    "valid_to": valid_to,
                },
            )
            packages.append(obj)
        self.stdout.write(f"  Packages: {len(packages)}")
        return packages

    def _create_events(self):
        events = []
        for title, ev_type, price in EVENT_TITLES:
            ev_date = date.today() + timedelta(days=random.randint(-60, 180))
            start_hour = random.randint(9, 18)
            obj, _ = Event.objects.get_or_create(
                title=title,
                defaults={
                    "event_type": ev_type,
                    "eventdate": ev_date,
                    "start_time": f"{start_hour:02d}:00:00",
                    "end_time": f"{min(start_hour + 3, 23):02d}:00:00",
                    "max_attendees": random.randint(20, 300),
                    "price_per_person": price,
                },
            )
            events.append(obj)
        self.stdout.write(f"  Events: {len(events)}")
        return events

    def _create_activities(self):
        activities = []
        for name, loc, cap, mins, price in ACTIVITY_DEFS:
            obj, _ = Activity.objects.get_or_create(
                act_name=name,
                defaults={
                    "location": loc,
                    "capacity": cap,
                    "duration": mins,
                    "price_per_person": price,
                },
            )
            activities.append(obj)
        self.stdout.write(f"  Activities: {len(activities)}")
        return activities