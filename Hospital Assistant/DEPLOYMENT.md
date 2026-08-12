# Deployment Runbook (Production)

This project uses environment-based settings modules.

## 1) Production environment variables

Set these variables on the server before starting the app:

```bash
DJANGO_ENV=prod
DJANGO_SETTINGS_MODULE=Hospital_Assistant.settings_prod

DJANGO_SECRET_KEY=<strong-random-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com

DJANGO_DB_ENGINE=django.db.backends.postgresql
DJANGO_DB_NAME=<database_name>
DJANGO_DB_USER=<database_user>
DJANGO_DB_PASSWORD=<database_password>
DJANGO_DB_HOST=<database_host>
DJANGO_DB_PORT=5432

DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SESSION_COOKIE_HTTPONLY=True
DJANGO_CSRF_COOKIE_HTTPONLY=True
DJANGO_SESSION_COOKIE_SAMESITE=Lax
DJANGO_CSRF_COOKIE_SAMESITE=Lax
DJANGO_SECURE_HSTS_SECONDS=31536000
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=True
DJANGO_SECURE_HSTS_PRELOAD=True
DJANGO_SECURE_CONTENT_TYPE_NOSNIFF=True
DJANGO_SECURE_REFERRER_POLICY=same-origin
DJANGO_X_FRAME_OPTIONS=DENY

DJANGO_STATICFILES_STORAGE=whitenoise.storage.CompressedManifestStaticFilesStorage
```

## 2) Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Run checks and database migrations

```bash
python manage.py check --deploy
python manage.py migrate
```

## 4) Collect static files

```bash
python manage.py collectstatic --noinput
```

## 5) Start application server

Example (Gunicorn):

```bash
gunicorn Hospital_Assistant.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

## 6) Post-deploy verification

- Open `/` and verify login page and navigation load.
- Verify staff/patient/encounter pages load for authorized users.
- Verify AI workflow pages load for allowed roles.
- Confirm static files are served correctly.

## 7) Every release checklist

1. Pull latest code.
2. Install/update dependencies.
3. Run migrations.
4. Run collectstatic.
5. Restart app process.
6. Verify application health.
