import traceback

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def doc_admin_view(request):
    return render(request, 'admin.html')

def doc_customer_view(request):
    return render(request, 'customer.html')

def doc_staff_view(request):
    return render(request, 'staff.html')


def _mock_order_context():
    ticket_id = "A34567890"
    ticket_url = f"https://funfinder.ge/orders/{ticket_id}/verify"
    return {
        "subject": "Your FunFinder ticket — Benny Benassi @ WaMu Theater",
        "heading": "Order confirmation",
        "intro": "Thank you for your purchase! Please save or print your ticket before the event.",
        "brand": "FUNFINDER.GE",
        "artist_line": "BENNY<br>BENASSI",
        "location_name": "WaMu Theater",
        "location_address": "800 Occidental Ave S<br>Seattle, WA 98134",
        "event_datetime": "Saturday<br>November 2, 2026<br>8:00 PM",
        "event_name": "Benny Benassi @ WaMu Theater",
        "customer_name": "Alex Law",
        "ticket_type": "General Admission",
        "quantity": "1",
        "price": "$40.00",
        "ticket_id": ticket_id,
        "ticket_url": ticket_url,
        "hero_image_url": "https://static.vecteezy.com/system/resources/thumbnails/057/068/323/small/single-fresh-red-strawberry-on-table-green-background-food-fruit-sweet-macro-juicy-plant-image-photo.jpg",
        "hero_eyebrow": "Order confirmed",
        "year": "2026",
    }


@csrf_exempt
def sendgrid_test_view(request):
    """Send the order-confirmation email template (mock data) via SendGrid Web API.

    Query params:
      - to=...        override recipient (default: shabashvilinika07@gmail.com)
      - preview=1     render the template in the browser instead of sending
    """
    sender = getattr(settings, "SENDGRID_EMAIL_SENDER", "") or ""
    api_key = getattr(settings, "SENDGRID_API_KEY", "") or ""

    to = request.GET.get("to") or "shabashvilinika07@gmail.com"
    ctx = _mock_order_context()
    subject = ctx["subject"]

    if request.GET.get("preview") == "1":
        return HttpResponse(render_to_string("email/order_confirmation.html", ctx))

    html = render_to_string("email/order_confirmation.html", ctx)

    payload = {
        "transport": "web_api",
        "template": "email/order_confirmation.html",
        "from": sender,
        "to": to,
        "subject": subject,
    }

    try:
        mail = Mail(
            from_email=sender,
            to_emails=to,
            subject=subject,
            html_content=html,
        )
        resp = SendGridAPIClient(api_key).send(mail)
        return JsonResponse({
            **payload,
            "ok": True,
            "status_code": resp.status_code,
            "message_id": resp.headers.get("X-Message-Id"),
        })
    except Exception as exc:
        return JsonResponse({
            **payload,
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }, status=500)
