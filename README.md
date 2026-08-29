# The_Sum

Travis CI status: [![Build Status](https://travis-ci.com/uva-cp-1920/The_Sum.svg?token=SyrFHx8gYJaW1KCbD5sw&branch=master)](https://travis-ci.com/uva-cp-1920/The_Sum)

The Sum’s organizational mission is simply: To stand in solidarity with ALL people. “We do this by holding ourselves, our organizations, and our communities gently and ferociously accountable to this truth: NO ONE STANDS ALONE.
Through assessment, workshops, advocacy, and coaching we facilitate the call to a deeper purpose that will engender a just and thriving world. We individualize support to transform awareness, develop skills, and ignite empowerment to "blow the lid off" of our effectiveness, in any field, across our differences: race, sexual orientation, gender, religion, dis/ability, socio-economic class, and culture.”
The organization has an online assessment (PDA or Power of Difference Assessment) which measures one’s unconscious orientation to these socio-cultural differences. The assessment identifies areas of strength, limitation, and indicates specific areas of needed growth. The assessment asks individuals about their level of agreement with four patterns of thinking and behavior: Sensitivity, Oneness, Strength, and Leveraging. After the assessment is taken, the gathered data is processed to produce a meaningful document which a consultant uses to make meaning of the data with the person who took the assessment. The assessment may be repeated at a later time to measure changes. This year, we will be collaborating with UVA professors (in the statistics department) in order to study the assessment model and its effectiveness. We hope to have 1000 people take the assessment by the end of 2020.

We are looking to have a system where individuals can register to take the assessment, complete 19 demographic questions, and the 70 assessment items. Upon completion, we want them to be redirected to a calendar where they can register for a consultation. Also, upon completion we want the system to automatically enter the data into an excel spreadsheet, convert it to a PDF, and email to the assessment taker. The administrators for the system should be able to view each individual’s profile and data. Admins should be able to view the assessment report which they discuss with the individual who took the assessment. Admins should also be able to access and manipulate all data – aggregate demographics by any category (for example: create a report based on race, gender, age, etc.).


### Contact Information

J. Elliott Cisneros

Executive Director/Founder

434.260.9377

jelliottcisneros@thesum.org

## Local development

The Django application lives in `src/`.

These steps are intended for local review and development on a modern Mac/Python 3.9 environment. They use SQLite, print email to the console, and avoid production AWS, PayPal, and SMTP credentials.

```bash
cd src
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-local.txt
cp TheSum/.env.example TheSum/.env
python manage.py migrate
python manage.py seed_local_data
python manage.py runserver 127.0.0.1:8000
```

If package installation fails while trying to write bytecode under `~/Library/Caches/com.apple.python`, rerun the dependency install with:

```bash
pip install --no-compile -r requirements-local.txt
```

Then open:

- Public site: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

The local seed command creates:

- Admin login: `admin` / `admin`
- Institutional access code: `LOCALTEST`
- Placeholder assessment statements so the public flow can render

If you have a PostgreSQL dump of the production `core_question` table created with `pg_dump --column-inserts`, import real statements into the local SQLite database with:

```bash
python manage.py import_questions_from_pg_dump ~/Desktop/core_question.sql
```

Do not use the local `.env`, seeded admin password, or placeholder statements in production.

## Production configuration notes

Production should run with `ENV=PRODUCTION` and real values supplied by the hosting environment, not committed files.

At minimum, production needs:

- `SECRET_KEY`
- `APP_URL`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS` as Django 2.2 hostnames, for example `example.com,www.example.com`
- `RDS_DB_NAME`, `RDS_USERNAME`, `RDS_PASSWORD`, `RDS_HOSTNAME`, `RDS_PORT`
- `PAYPAL_IDENTITY_TOKEN`, `PAYPAL_RECEIVER_EMAIL`
- AWS and email variables shown in `src/TheSum/.env.example`. The app supports Brevo-style SMTP settings through `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `FROM_EMAIL`, `DEFAULT_FROM_EMAIL`, `SERVER_EMAIL`, `BCC_EMAIL`, and `EMAIL_TIMEOUT`.

`PAYPAL_RECIEVER_EMAIL` is still supported as a legacy misspelled alias, but new environments should use `PAYPAL_RECEIVER_EMAIL`.

Security defaults are enabled automatically for `ENV=PRODUCTION`: HTTPS redirect, secure session/CSRF cookies, HSTS, content-type sniffing protection, same-origin referrer policy, and `X-Forwarded-Proto` handling for a reverse proxy/load balancer.

## Dependency notes

The legacy production and Travis dependency files remain on Django 2.2.28. `requirements-local.txt` is the recommended path for local development and now uses Django 5.2.17. The production dependency files remain unchanged pending a deliberate production migration. The legacy ReportLab Git fork has been replaced with the maintained ReportLab package, pinned to the 3.x line used by the app's legacy chart rendering.
