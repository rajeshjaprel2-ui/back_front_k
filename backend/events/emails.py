import logging
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

LOGO_PATH = settings.FRONTEND_DIR / "static" / "events" / "img" / "srinivas-logo.jpeg"
LOGO_CID = "srinivas-logo"


def _send_branded(subject, text, template, context, to):
    """Send a plain-text email with an HTML version that embeds the university logo."""
    html = render_to_string(template, {**context, "site_url": settings.SITE_URL, "logo_cid": LOGO_CID})
    message = EmailMultiAlternatives(subject=subject, body=text, from_email=settings.DEFAULT_FROM_EMAIL, to=[to])
    message.mixed_subtype = "related"
    message.attach_alternative(html, "text/html")
    with open(LOGO_PATH, "rb") as fh:
        logo = MIMEImage(fh.read())
    logo.add_header("Content-ID", f"<{LOGO_CID}>")
    logo.add_header("Content-Disposition", "inline", filename="srinivas-logo.jpeg")
    message.attach(logo)
    message.send()


def send_welcome_email(user):
    """Thank a newly signed-up student and confirm their account details. Returns True if sent."""
    if not user.email:
        return False
    name = user.get_full_name() or user.username
    signed_up = timezone.localtime(user.date_joined).strftime("%d %B %Y, %I:%M %p")
    lines = [
        f"Dear {name},",
        "",
        "Thank you for signing up with Srinivas University Events! We're excited to have you on board "
        "and can't wait to help you explore the seminars, workshops, sports and cultural events happening on campus.",
        "",
        "Your Account Details",
        f"  Email       : {user.email}",
        f"  Username    : {user.username}",
        f"  Signup Date : {signed_up}",
        "",
        "You can now sign in, browse upcoming events and reserve your seat in one click.",
        "",
        "Srinivas University Events Team",
    ]
    try:
        _send_branded(
            "Welcome to Srinivas University Events!",
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
    browser = next(
        (name for key, name in [("Edg/", "Microsoft Edge"), ("OPR/", "Opera"), ("Chrome/", "Google Chrome"),
                                ("Firefox/", "Mozilla Firefox"), ("Safari/", "Safari")] if key in ua),
        "Unknown browser",
    )
    system = next(
        (name for key, name in [("Android", "Android"), ("iPhone", "iPhone"), ("iPad", "iPad"), ("Windows", "Windows"),
                                ("Mac OS X", "macOS"), ("Linux", "Linux")] if key in ua),
        "Unknown device",
    )
    return f"{browser} on {system}"


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "") or "Unknown"


def send_login_alert(user, request):
    """Tell a student that their account was just signed in to. Returns True if sent."""
    if not user.email:
        return False
    name = user.get_full_name() or user.username
    signed_in = timezone.localtime().strftime("%d %B %Y, %I:%M %p")
    device = _describe_device(request.META.get("HTTP_USER_AGENT"))
    ip = _client_ip(request)
    lines = [
        f"Dear {name},",
        "",
        "You have successfully signed in to your Srinivas University Events account.",
        "",
        "Sign-in Details",
        f"  Email      : {user.email}",
        f"  Username   : {user.username}",
        f"  Time       : {signed_in}",
        f"  Device     : {device}",
        f"  IP address : {ip}",
        "",
        "If this was you, no action is needed. If you don't recognise this sign-in, "
        "please contact the events administrator immediately.",
        "",
        "Srinivas University Events Team",
    ]
    try:
        _send_branded(
            "New sign-in to your Srinivas University Events account",
            "\n".join(lines),
            "events/emails/login_alert.html",
            {"name": name, "email": user.email, "username": user.username,
             "signed_in": signed_in, "device": device, "ip": ip},
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
    lines += ["", "Please arrive on time. We look forward to seeing you!", "", "College Events Team"]

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
