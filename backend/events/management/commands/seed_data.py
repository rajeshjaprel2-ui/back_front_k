from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from events.models import Event, Registration, StudentProfile


class Command(BaseCommand):
    help = "Load demo admin, students, events, and registrations."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "first_name": "College",
                "last_name": "Admin",
                "email": "admin@college.edu",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password("admin123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        students_data = [
            ("rahul", "Rahul", "Sharma", "BCA2024001", "BCA", "2", "9876543210"),
            ("priya", "Priya", "Nair", "BCA2024002", "BCA", "2", "9876543211"),
            ("amit", "Amit", "Patel", "BBA2024003", "BBA", "1", "9876543212"),
            ("sneha", "Sneha", "Reddy", "BCA2023004", "BCA", "3", "9876543213"),
        ]
        students = []
        for username, first, last, roll, dept, year, phone in students_data:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"first_name": first, "last_name": last, "email": f"{username}@college.edu"},
            )
            user.set_password("student123")
            user.first_name = first
            user.last_name = last
            user.save()
            profile, _ = StudentProfile.objects.get_or_create(
                user=user,
                defaults={"roll_number": roll, "department": dept, "year": year, "phone": phone},
            )
            students.append(user)

        today = date.today()
        events_data = [
            {
                "title": "AI & Career Opportunities Seminar",
                "description": "A seminar on artificial intelligence, career paths, and industry skills for BCA students.",
                "category": "seminar",
                "date": today + timedelta(days=10),
                "time": time(10, 30),
                "venue": "Seminar Hall, Block A",
                "max_participants": 80,
                "status": "upcoming",
            },
            {
                "title": "Web Development Workshop",
                "description": "Hands-on Django and frontend workshop covering forms, databases, and hosting a college project.",
                "category": "workshop",
                "date": today + timedelta(days=18),
                "time": time(14, 0),
                "venue": "Computer Lab 2",
                "max_participants": 40,
                "status": "upcoming",
            },
            {
                "title": "Inter-College Cricket Trophy",
                "description": "Annual sports event. Register as a player or volunteer for the college cricket tournament.",
                "category": "sports",
                "date": today + timedelta(days=25),
                "time": time(8, 0),
                "venue": "College Ground",
                "max_participants": 60,
                "participation_type": "team",
                "max_team_size": 11,
                "rules": (
                    "Each team must have 11 players plus up to 4 substitutes.\n"
                    "All players must carry their college ID card.\n"
                    "Matches are 10 overs per side; the umpire's decision is final.\n"
                    "Teams must report 30 minutes before their scheduled match."
                ),
                "status": "upcoming",
            },
            {
                "title": "Cultural Fest – Rhythm 2026",
                "description": "Dance, music, and drama competitions for all departments.",
                "category": "cultural",
                "date": today + timedelta(days=35),
                "time": time(16, 0),
                "venue": "Main Auditorium",
                "max_participants": 120,
                "status": "upcoming",
            },
            {
                "title": "Hackathon: Code for Campus",
                "description": "24-hour technical event to build useful tools for college administration and students.",
                "category": "technical",
                "date": today - timedelta(days=20),
                "time": time(9, 0),
                "venue": "Innovation Lab",
                "max_participants": 50,
                "status": "completed",
            },
        ]

        common = {
            "rules": (
                "Carry your college ID card.\n"
                "Report at the venue 15 minutes before the start time.\n"
                "Maintain discipline; misconduct leads to disqualification.\n"
                "The coordinators' decision is final."
            ),
            "student_coordinator_name": "Rahul Sharma",
            "student_coordinator_phone": "9876543210",
            "teacher_coordinator_name": "Dr. Anitha Rao",
            "teacher_coordinator_phone": "9845012345",
        }
        created_events = []
        for data in events_data:
            event, _ = Event.objects.get_or_create(
                title=data["title"],
                defaults={**common, **data, "created_by": admin},
            )
            created_events.append(event)

        pairs = [
            (0, 0),
            (0, 1),
            (1, 0),
            (1, 2),
            (2, 3),
            (3, 1),
            (3, 3),
            (4, 0),
            (4, 1),
        ]
        for e_idx, s_idx in pairs:
            Registration.objects.get_or_create(event=created_events[e_idx], student=students[s_idx])

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("Admin login:  admin / admin123")
        self.stdout.write("Student login: rahul / student123")
