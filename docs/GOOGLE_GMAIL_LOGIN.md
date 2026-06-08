# Configure user Gmail (Google) sign-in

This app uses **Google OAuth2** for “Continue with Google”. The callback is under `/auth/`, so the **redirect URI** must match exactly in Google Cloud Console.

---

## Fix Error 400: redirect_uri_mismatch

This error means the **Authorized redirect URI** in Google Cloud Console does not match the URL your app uses. For this project the callback path is **`/auth/complete/google-oauth2/`**.

**Tip:** With the server running, visit `http://127.0.0.1:8005/health/?google_redirect=1` (use your actual host/port) to see the exact redirect URI your app sends. Add that URI to Google Console. (Requires `DEBUG=True` or `GOOGLE_OAUTH_DEBUG=1` in `.env`.)

So the full redirect URIs are:

| Environment | Authorized redirect URI |
|-------------|-------------------------|
| **Production** | `https://globaldesignerhub.com/auth/complete/google-oauth2/` |
| **Production (www)** | `https://www.globaldesignerhub.com/auth/complete/google-oauth2/` |
| **Local (port 8005)** | `http://localhost:8005/auth/complete/google-oauth2/` |
| **Local (port 8005)** | `http://127.0.0.1:8005/auth/complete/google-oauth2/` |
| **Local (port 8004)** | `http://localhost:8004/auth/complete/google-oauth2/` |
| **Local (port 8004)** | `http://127.0.0.1:8004/auth/complete/google-oauth2/` |
| **Local (port 8000)** | `http://localhost:8000/auth/complete/google-oauth2/` |
| **Local (port 8000)** | `http://127.0.0.1:8000/auth/complete/google-oauth2/` |

Add every URI you use (production + local if you test locally). Scheme (http/https), domain, path, and trailing slash must match exactly.

---

## Step-by-step: Google Cloud Console

### 1. Open Google Cloud Console

- Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
- Sign in with the Google account that owns the OAuth client (e.g. pchaganti0@gmail.com or your org account).

### 2. Select or create a project

- Use the project dropdown at the top.
- If you don’t have a project for GlobalDesignerHub, click **Create project**, name it (e.g. “GlobalDesignerHub”), then select it.

### 3. OAuth consent screen

- Go to **APIs & Services** → **OAuth consent screen**.
- If not set up: choose **External** (or Internal for Workspace), then fill:
  - **App name:** e.g. GlobalDesignerHub
  - **User support email:** your email
  - **Developer contact:** your email
- Under **Scopes**, ensure you have at least:
  - `.../auth/userinfo.email`
  - `.../auth/userinfo.profile`
  - (Or use **openid**, **email**, **profile** — the app already requests these.)
- If the app is in **Testing**, add **Test users** (the Gmail addresses that can sign in) and save.

### 4. Create or edit OAuth 2.0 credentials

- Go to **APIs & Services** → **Credentials**.
- Either:
  - **Create credentials** → **OAuth client ID**, or
  - Open your existing **Web application** client for this app.
- **Application type:** Web application.
- **Name:** e.g. “GlobalDesignerHub Web” (any label).

### 5. Authorized redirect URIs (critical)

Under **Authorized redirect URIs**, click **Add URI** and add **each** of these you use (copy/paste; no typos, no extra spaces):

**Production (required for globaldesignerhub.com):**

```
https://globaldesignerhub.com/auth/complete/google-oauth2/
```

If you also use `www`:

```
https://www.globaldesignerhub.com/auth/complete/google-oauth2/
```

**Local (only if you test “Continue with Google” on your machine):**

The **port must match** your runserver port. If you use `runserver 8005`, add:
```
http://localhost:8005/auth/complete/google-oauth2/
http://127.0.0.1:8005/auth/complete/google-oauth2/
```
For port 8004 (see `AGENTS.md` quick reference):
```
http://localhost:8004/auth/complete/google-oauth2/
http://127.0.0.1:8004/auth/complete/google-oauth2/
```
For port 8000:
```
http://localhost:8000/auth/complete/google-oauth2/
http://127.0.0.1:8000/auth/complete/google-oauth2/
```

- Do **not** use `/accounts/google/login/callback/` — this app uses `/auth/complete/google-oauth2/`.
- Save (e.g. **Save** or **Create**).

### 6. Copy Client ID and Client Secret

- In the OAuth client, copy **Client ID** and **Client secret**.
- Keep the secret secure; do not commit it to git.

---

## Step-by-step: Django / environment

### 1. Environment variables

**Production** (e.g. `.env.production` or your server env):

```bash
GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here
SOCIAL_AUTH_REDIRECT_IS_HTTPS=True
```

Optional (same values):

```bash
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=${GOOGLE_CLIENT_ID}
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=${GOOGLE_CLIENT_SECRET}
```

**Local** (e.g. `.env`):

```bash
GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here
# For local HTTP only:
# SOCIAL_AUTH_REDIRECT_IS_HTTPS=False
```

### 2. Confirm Django settings

The project already configures:

- `social_django` in `INSTALLED_APPS`
- `social_django.urls` under `path("auth/", ...)` in `gdh/urls.py`
- `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY` / `_SECRET` from `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` in `gdh/settings.py`
- `SOCIAL_AUTH_LOGIN_REDIRECT_URL` (e.g. `/dashboard/`) and `SOCIAL_AUTH_LOGIN_ERROR_URL` (e.g. `/accounts/login/`)

No code change is needed if the redirect URIs in Google match the table above.

### 3. Restart the app

- Restart the Django/Gunicorn process so it picks up env changes.
- Try “Continue with Google” again on production; clear cache or use an incognito window if needed.

---

## Quick checklist

- [ ] Google Cloud Console: OAuth consent screen set (app name, support email, scopes, test users if in Testing).
- [ ] Credentials: **Web application** client created.
- [ ] **Authorized redirect URIs** include exactly:  
  `https://globaldesignerhub.com/auth/complete/google-oauth2/`  
  (and `https://www.globaldesignerhub.com/auth/complete/google-oauth2/` if you use www).
- [ ] Production env has `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and optionally `SOCIAL_AUTH_REDIRECT_IS_HTTPS=True`.
- [ ] App restarted after changing env or Google Console.

After this, user Gmail sign-in should work; the “Continue with Google” button in the auth modal and login page will use the correct redirect URI and avoid **Error 400: redirect_uri_mismatch**.
