# Social Authentication Setup Guide

## 1. Install Dependencies

```bash
pip install social-auth-app-django
pip install social-auth-core[openidconnect]
```

## 2. Update requirements.txt

Add these lines to requirements.txt:

```
social-auth-app-django==5.4.0
social-auth-core[openidconnect]==4.4.2
```

## 3. Update settings.py

Add to INSTALLED_APPS:

```python
INSTALLED_APPS = [
    # ... existing apps
    'social_django',
]
```

Add to MIDDLEWARE:

```python
MIDDLEWARE = [
    # ... existing middleware
    'social_django.middleware.SocialAuthExceptionMiddleware',
]
```

Add authentication backends:

```python
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.linkedin.LinkedinOAuth2',
    'social_core.backends.instagram.InstagramOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)
```

Add social auth settings:

```python
# Social Auth Settings
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('GOOGLE_OAUTH2_SECRET')

SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY = os.getenv('LINKEDIN_OAUTH2_KEY')
SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET = os.getenv('LINKEDIN_OAUTH2_SECRET')
SOCIAL_AUTH_LINKEDIN_OAUTH2_SCOPE = ['r_liteprofile', 'r_emailaddress']

SOCIAL_AUTH_INSTAGRAM_KEY = os.getenv('INSTAGRAM_KEY')
SOCIAL_AUTH_INSTAGRAM_SECRET = os.getenv('INSTAGRAM_SECRET')

# Redirect URLs
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_LOGIN_ERROR_URL = '/accounts/login/'
```

## 4. Update main urls.py

Add to urlpatterns:

```python
urlpatterns = [
    # ... existing patterns
    path('auth/', include('social_django.urls', namespace='social')),
]
```

## 5. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

## 6. Create OAuth Applications

### Google OAuth2:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs: `http://localhost:8000/auth/complete/google-oauth2/`

### LinkedIn OAuth2:

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Create a new app
3. Add authorized redirect URLs: `http://localhost:8000/auth/complete/linkedin-oauth2/`

### Instagram OAuth2:

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create a new app
3. Add Instagram Basic Display product
4. Add redirect URI: `http://localhost:8000/auth/complete/instagram/`

## 7. Environment Variables

Create a .env file or set environment variables:

```
GOOGLE_OAUTH2_KEY=your_google_client_id
GOOGLE_OAUTH2_SECRET=your_google_client_secret
LINKEDIN_OAUTH2_KEY=your_linkedin_client_id
LINKEDIN_OAUTH2_SECRET=your_linkedin_client_secret
INSTAGRAM_KEY=your_instagram_app_id
INSTAGRAM_SECRET=your_instagram_app_secret
```

## 8. Update Copilot Instructions

The `.github/copilot-instructions.md` should be updated to include:

- Social authentication setup requirements
- OAuth app configuration patterns
- Environment variable management for social auth
