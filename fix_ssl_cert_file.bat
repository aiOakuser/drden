@echo off
echo Fixing invalid SSL_CERT_FILE environment variable...

:: Remove user-level SSL_CERT_FILE
reg delete "HKCU\Environment" /v SSL_CERT_FILE /f

:: Remove system-level SSL_CERT_FILE (requires admin)
reg delete "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v SSL_CERT_FILE /f

echo Done. Please restart your terminal or PC for changes to take effect.
pause
