# Start Django runserver on port 8004 (HTTP only).
# Then run: .\open_http_browser.ps1  to open http://127.0.0.1:8004 in your default browser.
$env:DEBUG = "True"
$env:SECURE_SSL_REDIRECT = "False"
$port = 8004
$url = "http://127.0.0.1:$port"
Write-Host "Starting Django server at $url (HTTP only)." -ForegroundColor Green
Write-Host "In your browser use: $url  (http, NOT https)" -ForegroundColor Yellow
python manage.py runserver $port
