# College Events Management System

Srinivas University · Django project to manage college events.

## Project structure

```
College event management system/
├── backend/                  ← BACKEND (Python / Django: logic + database)
│   ├── college_events/       project settings, main URLs, WSGI/ASGI
│   └── events/               events app
│       ├── models.py         database tables (Event, StudentProfile, Registration)
│       ├── views.py          request handling / business logic
│       ├── forms.py          form validation
│       ├── urls.py           page routes
│       ├── admin.py          Django admin config
│       ├── migrations/       database schema history
│       └── management/commands/seed_data.py   demo data
│
├── frontend/                 ← FRONTEND (what users see in the browser)
│   ├── templates/events/     HTML pages (home, login, dashboards, events...)
│   └── static/events/
│       ├── css/style.css     design system / styling
│       └── img/              logo and images
│
├── media/                    uploaded event posters
├── db.sqlite3                database file
├── manage.py                 run commands from here
├── requirements.txt
└── run.bat                   one-click start on Windows
```

## Windows (send this to your friend)

1. Install Python from https://www.python.org/downloads/  
   Tick **Add python.exe to PATH**, then restart the laptop.
2. Unzip `College-Events-Management-System.zip`.
3. Open the folder that contains `manage.py`.
4. Double-click **`run.bat`**.
5. Open Chrome: http://127.0.0.1:8000/

Login: `admin` / `admin123` or `rahul` / `student123`

### Windows Command Prompt (if run.bat does not work)

```bat
cd %USERPROFILE%\Desktop\College-Events-Management-System
py -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```

Open: http://127.0.0.1:8000/

Do not use `source venv/bin/activate` or `python3` on Windows.

## Linux / Mac

```bash
cd College-Events-Management-System
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data
python manage.py runserver
```
