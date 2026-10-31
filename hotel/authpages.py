import uuid

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .models import Customer, Loyalty

User = get_user_model()


def _landing_page(user):
    """URL name to send a user to after login, based on who they are."""
    if user.is_superuser or hasattr(user, "administrator"):
        return "admin_dashboard"
    if hasattr(user, "employee"):
        return "staff_dashboard"
    if hasattr(user, "customer"):
        return "customer_dashboard"
    return "home"


def _safe_next(request):
    """?next=/some/page/ is only honoured if it points back to this site."""
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    ok = url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )
    return nxt if ok else ""


def _authenticate_by_email(request, email, password):
    """Email isn't unique in the User model, so try every account with that email."""
    if not email or not password:
        return None
    for account in User.objects.filter(email__iexact=email):
        user = authenticate(request, username=account.get_username(), password=password)
        if user is not None:
            return user
    return None


def login_view(request):
    if request.user.is_authenticated:
        return redirect(_landing_page(request.user))

    context = {"next": _safe_next(request), "email": "", "error": ""}

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = _authenticate_by_email(request, email, password)

        if user is None:
            # same message for "no such email" and "wrong password" on purpose
            context.update(email=email, error="Incorrect email or password.")
            return render(request, "hotel/login.html", context)

        auth_login(request, user)
        if not request.POST.get("remember"):
            request.session.set_expiry(0)      # forget the login when the browser closes
        return redirect(context["next"] or _landing_page(user))

    return render(request, "hotel/login.html", context)


def logout_view(request):
    auth_logout(request)
    return redirect("home")


def register_view(request):
    if request.user.is_authenticated:
        return redirect(_landing_page(request.user))

    context = {"errors": [], "first_name": "", "last_name": "", "email": ""}

    if request.method == "POST":
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        context.update(first_name=first_name, last_name=last_name, email=email)

        errors = []
        if not first_name or not last_name:
            errors.append("Please enter your first and last name.")
        try:
            validate_email(email)
        except ValidationError:
            errors.append("Please enter a valid email address.")
        else:
            if User.objects.filter(email__iexact=email).exists():
                errors.append("An account with this email already exists.")

        if not errors:
            try:
                validate_password(password, user=Customer(
                    username=email, email=email,
                    first_name=first_name, last_name=last_name))
            except ValidationError as exc:
                errors.extend(exc.messages)

        if not errors:
            try:
                with transaction.atomic():
                    customer = Customer.objects.create_user(
                        username=email,              # email is used as the username
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        # nid is required + unique but the form doesn't ask for it,
                        # so use a placeholder until the customer adds it in their profile
                        nid="TMP" + uuid.uuid4().hex[:12],
                        loyalty=Loyalty.objects.order_by("discount_rate", "loyalty_num").first(),
                    )
            except IntegrityError:
                errors.append("Could not create the account. Please try again.")
            else:
                auth_login(request, customer)
                return redirect("customer_dashboard")

        context["errors"] = errors

    return render(request, "hotel/register.html", context)