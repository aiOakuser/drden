@echo off
REM Local development server script
REM This sets the correct environment variables for local development

set DEBUG=True
set SECRET_KEY=P;35^4+cV=@*kXYexh==?wyH}a8b6k01H#,CUZ<X1PEFzmMqy%
set SECURE_SSL_REDIRECT=False
set SESSION_COOKIE_SECURE=False
set CSRF_COOKIE_SECURE=False
set SOCIAL_AUTH_REDIRECT_IS_HTTPS=False

set PORT=8000
if not "%~1"=="" set PORT=%~1
echo Starting Django development server with local settings...
echo Access your site at: http://127.0.0.1:%PORT%
echo NOTE: Use HTTP (not HTTPS) — type http://127.0.0.1:%PORT% in the browser!
python manage.py runserver %PORT%