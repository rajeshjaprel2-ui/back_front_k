import logging
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

LOGO_CID = "brand-logo"
DATETIME_FORMAT = "%d %B %Y, %I:%M %p"

BROWSERS = [
    ("Edg/", "Microsoft Edge"),
    ("OPR/", "Opera"),
    ("Chrome/", "Google Chrome"),
    ("Firefox/", "Mozilla Firefox"),
    ("Safari/", "Safari"),
]
SYSTEMS = [
    ("Android", "Android"),
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Windows", "Windows"),
    ("Mac OS X", "macOS"),
    ("Linux", "Linux"),
]
ROLES = {
    "admin": {"label": "Administrator", "cta": "Open admin dashboard"},
    "student": {"label": "Student", "cta": "Go to my dashboard"},
}


def _brand():
    return settings.EMAIL_BRAND


def _role(user):
    return "admin" if user.is_staff else "student"


def _site_link(url_name):
    return f"{settings.SITE_URL}{reverse(url_name)}"


def _send_branded(subject, text, template, context, to):
    """Send a plain-text email with an HTML version that embeds the brand logo."""
    brand = _brand()
    html = render_to_string(
        template, {**context, "brand": brand, "site_url": settings.SITE_URL, "logo_cid": LOGO_CID}
    )
    message = EmailMultiAlternatives(subject=subject, body=text, from_email=settings.DEFAULT_FROM_EMAIL, to=[to])
    message.mixed_subtype = "related"
    message.attach_alternative(html, "text/html")
    with open(brand["logo"], "rb") as fh:
        logo = MIMEImage(fh.read())
    logo.add_header("Content-ID", f"<{LOGO_CID}>")
    logo.add_header("Content-Disposition", "inline", filename=brand["logo"].name)
    message.attach(logo)
    message.send()


def send_welcome_email(user):
    """Thank a newly signed-up user and confirm their account details. Returns True if sent."""
    if not user.email:
        return False
    brand = _brand()
    name = user.get_full_name() or user.username
    signed_up = timezone.localtime(user.date_joined).strftime(DATETIME_FORMAT)
    lines = [
        f"Dear {name},",
        "",
        f"Thank you for signing up with {brand['portal']}! We're excited to have you on board "
        "and can't wait to help you explore the seminars, workshops, sports and cultural events happening on campus.",
        "",
        "Your Account Details",
        f"  Email       : {user.email}",
        f"  Username    : {user.username}",
        f"  Signup Date : {signed_up}",
        "",
        "You can now sign in, browse upcoming events and reserve your seat in one click.",
        "",
        brand["team"],
    ]
    try:
        _send_branded(
            f"Welcome to {brand['portal']}!",
            "\n".join(lines),
            "events/emails/welcome.html",
            {"name": name, "email": user.email, "username": user.username, "signed_up": signed_up},
            user.email,
        )
    except Exception:
        logger.exception("Could not send welcome email to %s", user.email)
        return False
    return True


def _describe_device(user_agent):
    ua = user_agent or ""
    browser = next((name for key, name in BROWSERS if key in ua), "Unknown browser")
    system = next((name for key, name in SYSTEMS if key in ua), "Unknown device")
    return f"{browser} on {system}"


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "") or "Unknown"


def send_login_alert(user, request):
    """Email a first sign-in welcome with sign-in details to roles listed in LOGIN_ALERT_ROLES. Returns True if sent."""
    role = _role(user)
    if role not in settings.LOGIN_ALERT_ROLES or not user.email:
        return False
    brand = _brand()
    role_info = ROLES[role]
    name = user.get_full_name() or user.username
    signed_in = timezone.localtime().strftime(DATETIME_FORMAT)
    device = _describe_device(request.META.get("HTTP_USER_AGENT"))
    ip = _client_ip(request)
    dashboard_url = _site_link("dashboard")
    lines = [
        f"Dear {name},",
        "",
        f"You have signed in to your {brand['portal']} account for the first time. Welcome aboard!",
        "",
        "Sign-in Details",
        f"  Email      : {user.email}",
        f"  Username   : {user.username}",
        f"  Role       : {role_info['label']}",
        f"  Time       : {signed_in}",
        f"  Device     : {device}",
        f"  IP address : {ip}",
        "",
        f"{role_info['cta']}: {dashboard_url}",
        "",
        "If this was you, no action is needed. If you don't recognise this sign-in, "
        "please contact the events administrator immediately.",
        "",
        brand["team"],
    ]
    try:
        _send_branded(
            f"Your first sign-in to {brand['portal']}",
            "\n".join(lines),
            "events/emails/login_alert.html",
            {
                "name": name,
                "email": user.email,
                "username": user.username,
                "role": role_info["label"],
                "cta": role_info["cta"],
                "dashboard_url": dashboard_url,
                "signed_in": signed_in,
                "device": device,
                "ip": ip,
            },
            user.email,
        )
    except Exception:
        logger.exception("Could not send login alert to %s", user.email)
        return False
    return True


def send_registration_confirmation(registration):
    """Email the student the event name, date, time and venue. Returns True if sent."""
    student = registration.student
    event = registration.event
    if not student.email:
        return False

    when = event.date.strftime("%A, %d %B %Y")
    start = event.time.strftime("%I:%M %p")
    if event.end_time:
        start = f"{start} - {event.end_time.strftime('%I:%M %p')}"
    if event.end_date and event.end_date != event.date:
        when = f"{when} to {event.end_date.strftime('%A, %d %B %Y')}"

    lines = [
        f"Dear {student.get_full_name() or student.username},",
        "",
        f'You have successfully registered for "{event.title}".',
        "",
        "Event details:",
        f"  Event    : {event.title}",
        f"  Date     : {when}",
        f"  Time     : {start}",
        f"  Location : {event.venue}",
        f"  Type     : {registration.get_participation_type_display()}",
    ]
    if registration.participation_type == "team":
        lines.append(f"  Team     : {registration.team_name}")
        lines.append(f"  Players  : {', '.join(registration.member_list)}")
    if event.student_coordinator_name or event.teacher_coordinator_name:
        lines += ["", "Coordinators:"]
        if event.student_coordinator_name:
            lines.append(f"  Student : {event.student_coordinator_name} ({event.student_coordinator_phone})")
        if event.teacher_coordinator_name:
            lines.append(f"  Teacher : {event.teacher_coordinator_name} ({event.teacher_coordinator_phone})")
    lines += ["", "Please arrive on time. We look forward to seeing you!", "", _brand()["team"]]

    try:
        send_mail(
            subject=f"Registration confirmed: {event.title}",
            message="\n".join(lines),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
        )
    except Exception:
        logger.exception("Could not send registration email to %s", student.email)
        return False
    return True
