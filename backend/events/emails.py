import logging
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

LOGO_PATH = settings.FRONTEND_DIR / "static" / "events" / "img" / "srinivas-logo.jpeg"
LOGO_CID = "srinivas-logo"


def send_welcome_email(user):
    """Thank a newly signed-up student and confirm their account details. Returns True if sent."""
    if not user.email:
        return False
    signed_up = timezone.localtime(user.date_joined).strftime("%d %B %Y, %I:%M %p")
    lines = [
        f"Dear {user.get_full_name() or user.username},",
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
    name = user.get_full_name() or user.username
    html = render_to_string(
        "events/emails/welcome.html",
        {
            "name": name,
            "email": user.email,
            "username": user.username,
            "signed_up": signed_up,
            "site_url": settings.SITE_URL,
            "logo_cid": LOGO_CID,
        },
    )
    message = EmailMultiAlternatives(
        subject="Welcome to Srinivas University Events!",
        body="\n".join(lines),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.mixed_subtype = "related"
    message.attach_alternative(html, "text/html")
    with open(LOGO_PATH, "rb") as fh:
        logo = MIMEImage(fh.read())
    logo.add_header("Content-ID", f"<{LOGO_CID}>")
    logo.add_header("Content-Disposition", "inline", filename="srinivas-logo.jpeg")
    message.attach(logo)
    try:
        message.send()
    except Exception:
        logger.exception("Could not send welcome email to %s", user.email)
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
