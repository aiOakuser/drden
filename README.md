Resume.aioak.co is a secure, tech-forward application designed for fashion designers to effortlessly upload and manage their design portfolios with detailed, clean, and organized tech pack information.
The platform offers a user-friendly interface and a robust authentication system, allowing users to sign in securely via Gmail, LinkedIn, or Instagram. Built with both usability and security in mind, Resume.aioak.co streamlines the process of presenting, storing, and sharing professional design documents in the fashion industry.

## Google Login Setup (Designers)

1. Create OAuth 2.0 credentials in the [Google Cloud Console](https://console.cloud.google.com/) and add the callback `https://<your-domain>/auth/complete/google-oauth2/` (and `http://localhost:8000/auth/complete/google-oauth2/` for local development).
2. Set the following environment variables (either directly or via `.env.local`/`.env.production`):
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - Optional: `SOCIAL_AUTH_REDIRECT_IS_HTTPS=True` when running behind HTTPS.
3. Restart the Django app so that `social-auth-app-django` can pick up the credentials. Designers will now see the “Continue with Google” option on the login page and can sign in with their verified Google accounts.
