Resume.aioak.co is a secure, tech-forward application designed for fashion designers to effortlessly upload and manage their design portfolios with detailed, clean, and organized tech pack information.
The platform offers a user-friendly interface and a robust authentication system, allowing users to sign in securely via Gmail, LinkedIn, or Instagram. Built with both usability and security in mind, Resume.aioak.co streamlines the process of presenting, storing, and sharing professional design documents in the fashion industry.

## Suspicious traffic filtering

The server now short-circuits obvious scanner traffic (e.g., `/wp-admin`, `*.php`, `/lander/...`) via `designer_portfolio.middleware.SuspiciousRequestThrottleMiddleware`.  
Configuration knobs (all optional) can be set via environment variables:

- `SUSPICIOUS_REQUEST_FILTER_ENABLED` (default: `True` when `DEBUG` is false) — disable entirely if you need to debug custom routes.
- `SUSPICIOUS_PATH_PATTERNS` — comma or newline separated regex patterns to match additional paths; if unset, sensible defaults are used.
- `SUSPICIOUS_REQUEST_RATE_LIMIT` — maximum number of suspicious hits per IP within the window (default: `120`).
- `SUSPICIOUS_REQUEST_RATE_WINDOW` — window length in seconds for the above rate limit (default: `60`).

Filtered responses include the `X-Request-Filtered: suspicious` header and will return either `404` or `429` when the rate limit triggers.
