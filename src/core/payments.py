from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.urls import reverse

from .constants import PDA_PRICE, PDA_PRICE2, PDA_PRICE3

VALID_PAYMENT_AMOUNTS = {
    Decimal(str(PDA_PRICE)),
    Decimal(str(PDA_PRICE2)),
    Decimal(str(PDA_PRICE3)),
}

COMPLETED_PAYMENT_STATUSES = {"Completed", "completed", "SUCCESS"}


def build_absolute_url(request, route_name, **kwargs):
    return "%s://%s%s" % (
        settings.PROTOCOL,
        request.get_host(),
        reverse(route_name, kwargs=kwargs),
    )


def _decimal_or_none(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _first_present_attr(obj, *names):
    for name in names:
        value = getattr(obj, name, None)
        if value not in (None, ""):
            return value
    return None


def is_valid_pdt_payment(pdt_obj, expected_user_id):
    if pdt_obj is None:
        return False

    receiver = _first_present_attr(pdt_obj, "business", "receiver_email")
    if receiver != settings.PAYPAL_RECIEVER_EMAIL:
        return False

    amount = _decimal_or_none(_first_present_attr(pdt_obj, "mc_gross", "amt", "payment_gross"))
    if amount not in VALID_PAYMENT_AMOUNTS:
        return False

    status = _first_present_attr(pdt_obj, "payment_status", "st")
    if status is not None and status not in COMPLETED_PAYMENT_STATUSES:
        return False

    custom_user_id = getattr(pdt_obj, "custom", None)
    if custom_user_id is not None and str(custom_user_id).isdigit() and str(custom_user_id) != str(expected_user_id):
        return False

    currency = _first_present_attr(pdt_obj, "mc_currency", "currency_code", "cc")
    expected_currency = getattr(settings, "PAYPAL_CURRENCY", None)
    if expected_currency and currency is not None and currency != expected_currency:
        return False

    return True
