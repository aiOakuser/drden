# Local development server script for PowerShell
# This sets the correct environment variables for local development

$env:DEBUG="True"
$env:SECRET_KEY="P;35^4+cV=@*kXYexh==?wyH}a8b6k01H#,CUZ<X1PEFzmMqy%"
$env:SECURE_SSL_REDIRECT="False" 
$env:SESSION_COOKIE_SECURE="False"
$env:CSRF_COOKIE_SECURE="False"
$env:SOCIAL_AUTH_REDIRECT_IS_HTTPS="False"

$port = if ($args[0]) { $args[0] } else { "8000" }
Write-Host "Starting Django development server with local settings..." -ForegroundColor Green
Write-Host "Access your site at: http://127.0.0.1:$port" -ForegroundColor Yellow
Write-Host "NOTE: Use HTTP (not HTTPS) — type http://127.0.0.1:$port in the browser!" -ForegroundColor Red
python manage.py runserver $port