# Checkpoint - 2026-08-03

## Current State

- The app runs locally from `src/`. The original local virtualenv is `../work/pda-venv`; a cleaner rebuilt virtualenv also exists at `../work/pda-venv-clean`.
- Local registration, direct email-verification bypass, access code, demographics, statement flow, and assessment completion were tested successfully.
- The local SQLite database has been updated with the 70 real `core_question` statements exported from production RDS.
- A pre-import local SQLite backup exists at `src/db.sqlite3.before-real-questions-import-20260803`.
- The production RDS password was rotated after accidental exposure, and Elastic Beanstalk health was reported OK afterward.
- Production is a single-instance Elastic Beanstalk environment, not a load-balanced environment.
- Direct HTTPS access to `https://thepowerofdifference.org` works. Plain domain / HTTP redirect behavior still needs cleanup.

## Local Test Data

- Local seeded admin login: `admin` / `admin`.
- Local access code: `LOCALTEST`.
- Local `.env` files and SQLite databases are intentionally ignored and must not be committed.
- The exported production statement dump lives outside the repo on the Desktop and should not be committed.

## Checkpoint Findings

- `src/.gitignore` now ignores `db.sqlite3.*` so local database backups do not appear as untracked files.
- `git ls-files` confirms local `.env` files and `src/db.sqlite3` are not tracked.
- `git status` and `git diff` were unusually slow/hanging in this local workspace. Narrower `git ls-files` checks worked.
- `python manage.py check` was attempted but hung during package import from the virtualenv. Earlier in the setup work, `manage.py check`, migration dry-run, and `python manage.py test core` had completed successfully.

## Modernization Queue

1. Capture a clean git checkpoint once GitHub/local repo workflow is settled.
2. Fix production email configuration, likely through Brevo SMTP settings.
3. Add a safe, repeatable import/seed path for real assessment statements.
4. Clean up production security and redirect behavior, including canonical HTTP to HTTPS redirects.
5. Plan the Django/Python dependency upgrade in stages, with tests run between each stage.
6. Refactor highest-risk areas first: settings, payment handling, PDF generation, email verification, and deployment configuration.

## Follow-Up Work Started

- Product repositioning notes were captured in `docs/product-strategy-notes.md`.
- A reusable `import_questions_from_pg_dump` management command was added for `pg_dump --column-inserts` exports of `core_question`.
- The pure parser for those dumps lives in `core/question_dump.py`.
- A lightweight parser unit test was added in `core/tests/test_question_dump.py` and verified with plain `unittest`.
- Local startup slowness was traced to a combination of virtualenv package metadata and eager imports of heavy optional stacks.
- `core.models` now lazy-imports S3 private media storage so local startup does not load `boto3` unless production storage is actually needed.
- `visualization.views` now lazy-imports Bokeh inside chart helpers instead of at URL import time.
- Settings now accept the Elastic Beanstalk RDS variable names that are actually present: `RDS_USERNAME`, `RDS_PASSWORD`, and `RDS_HOSTNAME`, while preserving older aliases.
- Email settings now support cleaner Brevo-style SMTP variables and default to console email in local development.
- `core.views` now lazy-imports ReportLab inside PDF/chart helper functions instead of loading it during ordinary URL/admin startup.
- `core.admin` now lazy-imports custom admin view classes and `generate_pdf()` only when those admin URLs/actions are used, and no longer imports ReportLab at module load.
- A fresh virtualenv was built at `../work/pda-venv-clean` using `pip install --no-compile -r src/requirements-local.txt`.
- A faster temporary virtualenv was built at `/private/tmp/pda-venv-20260804`; this avoided the slow virtualenv startup seen under the Documents workspace.
- `TEMPLATES['DIRS']` now uses `os.path.join(BASE_DIR, 'templates')` so management commands work correctly from outside `src/`.
- Email settings now define Django-standard `DEFAULT_FROM_EMAIL`, configurable `SERVER_EMAIL`, and `EMAIL_TIMEOUT`.
- PayPal settings now support correctly spelled `PAYPAL_RECEIVER_EMAIL` while preserving the legacy misspelled `PAYPAL_RECIEVER_EMAIL` alias.
- `README.md` and `TheSum/.env.example` now document the Brevo-facing email fields and PayPal receiver alias.

## Latest Verification

- `PYTHONPYCACHEPREFIX=/private/tmp/pda-pycache-20260804 /private/tmp/pda-venv-20260804/bin/python pda/src/manage.py check` passed.
- `python manage.py import_questions_from_pg_dump /private/tmp/core_question_sample.sql --expected-count 2 --dry-run` passed.
- `python manage.py test core.tests.test_question_dump` passed.
- `PYTHONPYCACHEPREFIX=/private/tmp/pda-pycache-20260804 /private/tmp/pda-venv-20260804/bin/python pda/src/manage.py test core` passed after the settings/email cleanup, running 287 tests successfully in about 26 seconds.
- After additional settings/email/PDF/admin changes, syntax checks passed for changed files using:
  `PYTHONPYCACHEPREFIX=/private/tmp/pda-pycache ../work/pda-venv-clean/bin/python -m py_compile ...`
- The workspace still has persistent `com.apple.provenance` extended attributes on many Python files. Attempts to clear them with `xattr -c` and escalated `xattr -cr` reported success but the attributes remained visible. The practical workaround is to use the `/private/tmp` virtualenv plus `PYTHONPYCACHEPREFIX`.

## Next Technical Step

The next stability step is to continue settings/email cleanup with the working `/private/tmp` test lane, then revisit the persistent macOS metadata issue when GitHub/reclone is available.
