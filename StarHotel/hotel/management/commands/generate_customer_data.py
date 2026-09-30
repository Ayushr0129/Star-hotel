"""
Django management command: generate_customer_data

 
This script is READ-ONLY with respect to Loyalty, Branch, Room, Packages
and Even. It looks up whatever already exists in the database and uses it; it never creates,
edits, or deletes those rows. If a table is empty, the script tells you
and skips anything that depends on it.
"""
 
import random
from datetime import timedelta, date
 
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
 
try:
    from faker import Faker
except ImportError:
    raise SystemExit("Missing dependency: run `pip install faker --break-system-packages`")
 
# ADJUST THIS: import your actual models module
from ...models import (  # noqa
    Customer, Loyalty, Branch, Room, Packages, Event,
    Booking, Room_Item, Package_Item, Event_Item,
)
 
fake = Faker()
 
BOOKING_STATUSES = ["pending", "confirmed", "completed", "cancelled"]
PAYMENT_METHODS = ["credit_card", "debit_card", "bank_transfer", "cash", "e-wallet"]
 
 
class Command(BaseCommand):
    help = "Generate synthetic data for the customer dashboard"
 
    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=50,
                             help="Number of customers to create (default: 50)")
        parser.add_argument("--bookings-per-customer", type=int, default=3,
                             help="Max bookings per customer (default: 3)")
        parser.add_argument("--clear", action="store_true",
                             help="Delete existing customer-dashboard data first")
        parser.add_argument("--seed", type=int, default=None,
                             help="Random seed for reproducible output")
 
    def handle(self, *args, **options):
        if options["seed"] is not None:
            random.seed(options["seed"])
            Faker.seed(options["seed"])
 
        if options["clear"]:
            self._clear()
 
        loyalties, branches, rooms, packages, events = self._load_reference_data()
 
        with transaction.atomic():
            customers = self._create_customers(options["customers"], loyalties)
            self._create_bookings(
                customers, branches, rooms, packages, events,
                options["bookings_per_customer"],
            )
 
        self.stdout.write(self.style.SUCCESS(f"Done. {options['customers']} customers created."))
 
    # ---------- clearing  ----------
 
    def _clear(self):
        self.stdout.write("Clearing existing customer/booking/cart data (leaving "
                           "Loyalty, Branch, Room, Packages and Event untouched)...")
        Room_Item.objects.all().delete()
        Package_Item.objects.all().delete()
        Event_Item.objects.all().delete()
        Booking.objects.all().delete()
        Customer.objects.all().delete()
 
    # ---------- reference data: READ ONLY ----------
 
    def _load_reference_data(self):
        """
        Pulls in whatever already exists for Loyalty, Branch, Room, Packages
        and Event. Never creates/edits/deletes any of these -- that's your
        teammates' data. Anything missing is skipped with a warning so you
        know what to wait on.
        """
        loyalties = list(Loyalty.objects.all())
        branches = list(Branch.objects.all())
        rooms = list(Room.objects.all())
        packages = list(Packages.objects.all())
        events = list(Event.objects.all())
 
        self.stdout.write("Using existing reference data (read-only):")
        self.stdout.write(f"  Loyalty tiers found: {len(loyalties)}")
        self.stdout.write(f"  Branches found: {len(branches)}")
        self.stdout.write(f"  Rooms found: {len(rooms)}")
        self.stdout.write(f"  Packages found: {len(packages)}")
        self.stdout.write(f"  Events found: {len(events)}")
 
        if not branches:
            self.stdout.write(self.style.WARNING(
                "  No branches found -- bookings need a branch, so no bookings "
                "will be created until your teammate adds Branch data."
            ))
        if not (rooms or packages or events):
            self.stdout.write(self.style.WARNING(
                "  No rooms, packages, or events found -- cart items can't be "
                "created until at least one of those exists."
            ))
        if not loyalties:
            self.stdout.write(self.style.WARNING(
                "  No loyalty tiers found -- customers will be created with "
                "loyalty left blank."
            ))
 
        return loyalties, branches, rooms, packages, events
 
    # ---------- customers ----------
 
    def _create_customers(self, count, loyalties):
        customers = []
        used_usernames = set()
        for i in range(count):
            first = fake.first_name()
            last = fake.last_name()
            username = f"{first}.{last}.{i}".lower()
            if username in used_usernames:
                username = f"{username}{random.randint(100, 999)}"
            used_usernames.add(username)
 
            dob = fake.date_of_birth(minimum_age=18, maximum_age=80)
 
            customer = Customer.objects.create_user(
                username=username,
                email=fake.unique.email(),
                password="TestPass123!",
                first_name=first,
                last_name=last,
                dob=dob,
                phone=fake.phone_number()[:20],
                address=fake.address().replace("\n", ", ")[:255],
                nid=fake.unique.bothify(text="??######???"),
                loyalty=random.choice(loyalties) if loyalties else None,
            )
            customers.append(customer)
 
        self.stdout.write(f"  Customers: {len(customers)}")
        return customers
 
    # ---------- bookings ----------
 
    def _create_bookings(self, customers, branches, rooms, packages, events, max_per_customer):
        if not branches:
            self.stdout.write(self.style.WARNING(
                "  Skipping bookings: no Branch rows exist yet."
            ))
            return
        if not (rooms or packages or events):
            self.stdout.write(self.style.WARNING(
                "  Skipping bookings: no Room, Package, or Event rows exist yet "
                "to put in the cart."
            ))
            return
 
        rooms_by_branch = {}
        for room in rooms:
            rooms_by_branch.setdefault(room.branch_id, []).append(room)
 
        booking_count = 0
        item_count = 0
 
        for customer in customers:
            n_bookings = random.randint(0, max_per_customer)
            for _ in range(n_bookings):
                branch = random.choice(branches)
                check_in = date.today() + timedelta(days=random.randint(-120, 120))
                stay_length = random.randint(1, 10)
                check_out = check_in + timedelta(days=stay_length)
                status = random.choice(BOOKING_STATUSES)
 
                booking = Booking.objects.create(
                    no_of_guests=random.randint(1, 6),
                    check_in=check_in,
                    check_out=check_out,
                    bk_status=status,
                    estimated_sum=0,  # filled in after items are created
                    customer=customer,
                    branch=branch,
                )
                booking_count += 1
 
                total = 0
                n_items = random.randint(1, 3)
                for _ in range(n_items):
                    item_type = random.choices(
                        ["room", "package", "event"], weights=[0.6, 0.25, 0.15]
                    )[0]
                    created = False
 
                    if item_type == "room" and rooms_by_branch.get(branch.branch_id):
                        room = random.choice(rooms_by_branch[branch.branch_id])
                        price = float(room.price) * stay_length
                        Room_Item.objects.create(
                            bi_type="room",
                            price=round(price, 2),
                            payment_method=random.choice(PAYMENT_METHODS),
                            description=f"{room.room_type} room, {stay_length} night(s)",
                            booking=booking,
                            room=room,
                            check_in=check_in,
                            check_out=check_out,
                        )
                        total += price
                        created = True
 
                    elif item_type == "package" and packages:
                        package = random.choice(packages)
                        guests = random.randint(1, 4)
                        price = float(package.base_price) * guests
                        Package_Item.objects.create(
                            bi_type="package",
                            price=round(price, 2),
                            payment_method=random.choice(PAYMENT_METHODS),
                            description=f"{package.p_name} for {guests} guest(s)",
                            booking=booking,
                            package=package,
                            no_of_guests=guests,
                        )
                        total += price
                        created = True
 
                    elif events:
                        event = random.choice(events)
                        guests = random.randint(1, 4)
                        price = float(event.price_per_person) * guests
                        Event_Item.objects.create(
                            bi_type="event",
                            price=round(price, 2),
                            payment_method=random.choice(PAYMENT_METHODS),
                            description=f"{event.title} for {guests} guest(s)",
                            booking=booking,
                            event=event,
                            no_of_guests=guests,
                        )
                        total += price
                        created = True
 
                    if created:
                        item_count += 1
 
                booking.estimated_sum = round(total, 2)
                booking.save(update_fields=["estimated_sum"])
 
        self.stdout.write(f"  Bookings: {booking_count}")
        self.stdout.write(f"  Booking items: {item_count}")