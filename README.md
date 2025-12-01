Resume.aioak.co is a secure, tech-forward application designed for fashion designers to effortlessly upload and manage their design portfolios with detailed, clean, and organized tech pack information.
The platform offers a user-friendly interface and a robust authentication system, allowing users (including staff admins) to sign in securely via Google, LinkedIn, or Instagram OAuth flows or with traditional credentials. Built with both usability and security in mind, Resume.aioak.co streamlines the process of presenting, storing, and sharing professional design documents in the fashion industry.

## Authentication highlights

- OAuth providers: enable any mix of Google, LinkedIn, and Instagram by setting the corresponding `SOCIAL_AUTH_*_KEY` and `SOCIAL_AUTH_*_SECRET` env variables. The login view automatically surfaces only the providers that are configured, and staff can use the same flow (set `?next=/admin/` to jump back into Django admin after signing in).
- Email-first login: the custom `EmailOrUsernameModelBackend` allows either usernames or email addresses when using passwords.
- Passkey support: WebAuthn endpoints remain available for designers who prefer password-less sign-in.
- Automatic onboarding email: successful registrations—via forms, API, or OAuth—trigger a welcome email to the designer and a notification to the site owner.
- Password hygiene: forgot-password requests notify admins, and successful resets send a confirmation email to the account owner for additional visibility.

## Suspicious traffic filtering

The server now short-circuits obvious scanner traffic (e.g., `/wp-admin`, `*.php`, `/lander/...`) via `designer_portfolio.middleware.SuspiciousRequestThrottleMiddleware`.  
Configuration knobs (all optional) can be set via environment variables:

- `SUSPICIOUS_REQUEST_FILTER_ENABLED` (default: `True` when `DEBUG` is false) — disable entirely if you need to debug custom routes.
- `SUSPICIOUS_PATH_PATTERNS` — comma or newline separated regex patterns to match additional paths; if unset, sensible defaults are used.
- `SUSPICIOUS_REQUEST_RATE_LIMIT` — maximum number of suspicious hits per IP within the window (default: `120`).
- `SUSPICIOUS_REQUEST_RATE_WINDOW` — window length in seconds for the above rate limit (default: `60`).

Filtered responses include the `X-Request-Filtered: suspicious` header and will return either `404` or `429` when the rate limit triggers.

## Automated repository housekeeping

A scheduled GitHub Action (`.github/workflows/cleanup-unused-branches.yml`) keeps the hosted repository tidy by pruning feature branches that have been inactive for 45 days. The job runs every Monday at 06:00 UTC (and can also be triggered manually with `workflow_dispatch`) and executes `.github/scripts/cleanup_branches.py`, which calls the GitHub API to:

- Skip protected/default branches, well-known prefixes (`release/*`, `dependabot/*`, etc.), and branches linked to open PRs.
- Respect configurable limits via environment variables such as `BRANCH_STALE_DAYS`, `BRANCH_DELETE_LIMIT`, and `PROTECTED_BRANCHES`.
- Support a dry-run mode on manual invocations so the proposed deletions can be reviewed safely before applying.

Update the workflow inputs or the script’s environment variables if you need different retention windows or protected branch rules.
