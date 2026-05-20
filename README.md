# TaskManager — Smart Task Management System

A web-based task management app built with Flask, PostgreSQL, WebSockets, and Pandas. Built as part of an internship assignment.

---

## Features

- User registration, login, and logout
- Add, edit, delete, and view tasks
- Filter tasks by status (pending / in-progress / done)
- Analytics dashboard showing completion stats
- Real-time task updates using WebSockets (Flask-SocketIO)
- Clean, responsive UI with HTML/CSS

---

## Tech Stack

- **Backend** — Python, Flask
- **Database** — PostgreSQL (psycopg2)
- **Real-time** — Flask-SocketIO with eventlet
- **Analytics** — Pandas, NumPy
- **Frontend** — HTML5, CSS3, Vanilla JavaScript

---

## Project Structure

```
smart-task-manager/
├── app.py                  # main app, all routes and socket events
├── config.py               # config loaded from .env
├── schema.sql              # database schema
├── requirements.txt
├── .env.example
├── utils/
│   └── analytics.py        # pandas/numpy analytics module
├── templates/
│   ├── login.html
│   ├── register.html
│   └── dashboard.html
└── static/
    ├── css/
    │   ├── auth.css
    │   └── dashboard.css
    └── js/
        └── dashboard.js
```

---

## Setup Instructions

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/smart-task-manager.git
cd smart-task-manager
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # linux / mac
venv\Scripts\activate           # windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL

```bash
# create the database first
psql -U postgres -c "CREATE DATABASE taskmanager;"

# then run the schema to create the tables
psql -U postgres -d taskmanager -f schema.sql
```

### 5. Create your .env file

```bash
cp .env.example .env
```

Edit `.env` and update your database password:

```
SECRET_KEY=some-random-secret-string
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/taskmanager
```

### 6. Run the app

```bash
python app.py
```

Go to **http://localhost:5000** in your browser.

---

## API Endpoints

| Method | Endpoint                  | Description         |
|--------|---------------------------|---------------------|
| POST   | `/api/auth/register`      | Register new user   |
| POST   | `/api/auth/login`         | Login               |
| POST   | `/api/auth/logout`        | Logout              |
| GET    | `/api/tasks`              | Get all user tasks  |
| POST   | `/api/tasks`              | Create a task       |
| PUT    | `/api/tasks/<id>`         | Update a task       |
| DELETE | `/api/tasks/<id>`         | Delete a task       |
| GET    | `/api/analytics`          | Get analytics data  |

### Task fields

```json
{
  "title": "Task name",
  "description": "Details about the task",
  "priority": "low | medium | high",
  "status": "pending | in_progress | completed"
}
```

---

## WebSocket Events

The server broadcasts these events to all connected clients:

| Event          | When it fires        |
|----------------|----------------------|
| `new_task`     | A task is created    |
| `task_changed` | A task is updated    |
| `task_removed` | A task is deleted    |

---

## Analytics

The `/api/analytics` endpoint uses **Pandas** and **NumPy** to calculate:

- Total, completed, pending, and in-progress task counts
- Completion percentage
- Priority breakdown (low / medium / high)
- Average tasks created per active day