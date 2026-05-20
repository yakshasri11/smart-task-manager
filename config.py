import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = 'mysecretkey123'
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres123@localhost:5432/taskmanager')
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True