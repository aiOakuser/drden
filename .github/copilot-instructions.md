# designer Fashion Portfolio - AI Coding Guidelines

## Project Architecture

**designer** is a Django fashion portfolio platform for showcasing designer Manya's work. This is a single-app Django project with both web interface and REST API endpoints.

### Core App Structure

- **`designer/`** - Django project settings and main URL routing
- **`designer_portfolio/`** - Main application containing all business logic
- **Database**: SQLite for local dev, configurable for Postgres in production via environment variables

### Key Models & Relationships

```python
# Core content models
Brand (singleton) → stores brand identity (colors, fonts, logo)
Collection → CollectionImage, Look (fashion collections by year/season)
Design → DesignImage, Techpack (individual designs with technical specs)
Event → EventImage (fashion shows, popups)

# User management
User (Django auth) + RejectedDesigner (tracks rejected signups)
```

## Critical Development Patterns

### 1. Static Media Management

- **Static files**: `designer_portfolio/static/` with subdirs `css/`, `images/`, `js/`, `swatches/`
- **Media uploads**: Models use specific upload paths like `collections/covers/`, `designs/gallery/`
- **Helper function**: Use `utils.list_static_media(path)` for directory listings with automatic sorting
- **Brand assets**: Logo switching logic in navbar uses `logo-green.png` and `logo-dark.png`

### 2. URL & View Architecture

```python
# URL pattern: /collections/slug/, /designs/slug/, /events/slug/
# API endpoints: /api/brands/, /api/collections/, /api/designs/, /api/events/
# Special routes: /designs/upload/ (auth required), /admin/pending-designers/
```

### 3. Template Structure

- **Base template**: `base.html` includes navbar, footer, popup functionality
- **Includes**: `navbar.html`, `footer.html` for reusable components
- **Static loading**: Always use `{% load static %}` and `{% static 'path' %}`
- **Brand consistency**: Purple header (`#280768`), orange hover effects (`darkorange`)

### 4. Data Constants

- **`constants.py`**: Contains hardcoded `COLLECTION_DETAILS` and `EVENT_DETAILS` dictionaries
- **When adding collections/events**: Update both database models AND constants file for consistency

## Essential Development Commands

```bash
# Environment setup (virtual env already exists in env/)
.\env\Scripts\activate  # Windows activation
pip install -r requirements.txt

# Standard Django workflow
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver

# Database seeding
python manage.py loaddata designer_portfolio/fixtures/brand.json
```

## Environment Configuration

- **Local development**: Uses SQLite, no environment variables required
- **Production**: Set `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- **Caching**: Redis in production (`REDIS_URL`), local memory cache in development
- **Security**: Set `SECRET_KEY`, `DEBUG=False` for production

## Admin & Authentication Patterns

### Custom User Flows

- **Designer signup**: Uses `DesignerSignUpForm`, creates inactive users pending approval
- **Admin approval**: Special views at `/admin/pending-designers/` for user management
- **Permissions**: `ReadOnlyOrAuthWrite` for API (public read, auth required for write)

### Admin Interface Customizations

- **Image previews**: All admin models show thumbnail previews using `format_html()`
- **Inline editing**: `TechpackInline`, `DesignImageInline`, `EventImageInline` for related objects
- **Prepopulated slugs**: Auto-generate from title/year combinations

## Deployment & Production

- **Platform**: Uses Nixpacks configuration (`nixpacks.toml`)
- **Server**: Gunicorn WSGI server on port 8014
- **Static files**: WhiteNoise middleware with compression
- **SSL**: Custom batch file `fix_ssl_cert_file.bat` for certificate issues

## Common Gotchas

1. **Duplicate model fields**: `Collection` model has `cover_image` field defined twice - check before editing
2. **URL conflicts**: `/designs/upload/` appears twice in `urls.py` - maintain this pattern for routing precedence
3. **Constants sync**: When adding collections/events via admin, manually update `constants.py` dictionaries
4. **Static media paths**: Use forward slashes in `static()` calls even on Windows
5. **Image ordering**: Models use `order` field for gallery sorting - always include in admin interfaces

## Testing Approach

- **Test file**: `tests.py` is minimal (only contains placeholder comment)
- **Manual testing**: Focus on admin interface, file uploads, and API endpoints
- **Static file serving**: Test image loading across different collection/design galleries

When working on this codebase, prioritize consistency with existing patterns, especially the brand color scheme, URL structure, and admin interface design patterns.
