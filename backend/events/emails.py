import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


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
