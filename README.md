Resume.aioak.co is a secure, tech-forward application designed for fashion designers to effortlessly upload and manage their design portfolios with detailed, clean, and organized tech pack information.
The platform offers a user-friendly interface and a robust authentication system, allowing users to sign in securely via Gmail, LinkedIn, or Instagram. Built with both usability and security in mind, Resume.aioak.co streamlines the process of presenting, storing, and sharing professional design documents in the fashion industry.

## Local Development Quickstart

1. **Install dependencies**
   ```bash
   pip3 install --user -r requirements.txt
   ```
   (Feel free to use a virtual environment if your system provides `python3-venv`.)

2. **Environment variables**
   - The server now loads environment files in this order:
     1. File specified via `DJANGO_ENV_FILE` or `ENV_FILE`
     2. `.env.local`
     3. `.env`
   - To opt into production values stored in `.env.production`, explicitly set `DJANGO_LOAD_PRODUCTION_DOTENV=true`.
   - When no file is found, Django falls back to your shell environment variables.

3. **Database**
   - By default, the project uses SQLite (e.g., `db.sqlite3` in the repo root) so you can run the site without a PostgreSQL instance.
   - Set `DATABASE_URL` or the `DB_*` variables if you want to target PostgreSQL or another database engine.

4. **Run migrations and start the server**
   ```bash
   python3 manage.py migrate
   python3 manage.py runserver
   ```

This workflow avoids accidental connections to production databases and works out-of-the-box on a fresh clone.
