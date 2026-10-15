# Deploying MindTrack (Firebase Hosting → Cloud Run → Cloud SQL PostgreSQL)

```
Browser ──HTTPS──► Firebase Hosting (your-project.web.app)
                     │  rewrite "**"
                     ▼
                   Cloud Run service "mindtrack" (asia-south1)
                     │  Gunicorn → run:app → create_app()
                     ▼
                   Cloud SQL for PostgreSQL (Unix socket /cloudsql/...)
```

Nothing in this guide has been run against real Google Cloud resources yet. Local checks done
before writing it are listed at the end. **Several steps create billable resources** (Cloud SQL is
billed per hour even when idle; Cloud Run and Cloud Build have free tiers). Firebase Hosting
rewrites to Cloud Run require the project to have billing enabled (Blaze plan).

Commands are written for **Git Bash** (already on this machine) or Google Cloud Shell.
Replace every `<ANGLE_BRACKET>` value with your own. Nothing below prints your secrets.

---

## 0. What the app expects in production

| Variable | Where it comes from | Notes |
|---|---|---|
| `MINDTRACK_ENV=production` | env var (also set in the Dockerfile; Cloud Run is auto-detected) | turns on secure cookies, `__session` cookie name, no auto table creation |
| `SECRET_KEY` | Secret Manager | signs sessions. A new value for production is fine (it only logs everyone out). |
| `MINTRACK_ENCRYPTION_KEY` | Secret Manager | **must be the ORIGINAL key from your local `.env`**. Without it, existing journal entries, reflections and Mindy chats can never be decrypted. Never generate a new one for existing data. |
| `INSTANCE_CONNECTION_NAME`, `DB_NAME`, `DB_USER` | env vars | the app builds the Cloud SQL socket URL itself (no URL-encoding needed) |
| `DB_PASS` | Secret Manager | |
| `DATABASE_URL` | optional alternative to the four above | `postgres://` and `postgresql://` are converted to `postgresql+psycopg://` |

Why the session cookie is named `__session`: Firebase Hosting forwards **only** that cookie to
Cloud Run and strips all others. With Flask's default name, logins and CSRF would silently fail.

---

## 1. One-time tool setup

```bash
# Google Cloud CLI is installed at "C:\Users\Tashvi\OneDrive\Documents\google cloud\google-cloud-sdk".
gcloud --version
gcloud auth login
gcloud config set project <PROJECT_ID>

# Firebase CLI (needs Node.js)
npm install -g firebase-tools
firebase login
```

Shell variables used below:

```bash
PROJECT_ID=<PROJECT_ID>
REGION=asia-south1
SERVICE=mindtrack
SQL_INSTANCE=mindtrack-db
DB_NAME=mindtrack
DB_USER=mindtrack_app
INSTANCE_CONNECTION_NAME="$PROJECT_ID:$REGION:$SQL_INSTANCE"
RUN_SA="mindtrack-run@$PROJECT_ID.iam.gserviceaccount.com"
```

## 2. Enable the required APIs

```bash
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com firebasehosting.googleapis.com
```

## 3. Create Cloud SQL for PostgreSQL (billable)

```bash
gcloud sql instances create "$SQL_INSTANCE" --database-version=POSTGRES_16 --region="$REGION" \
  --edition=ENTERPRISE --tier=db-f1-micro --storage-size=10 --backup-start-time=21:00

gcloud sql databases create "$DB_NAME" --instance="$SQL_INSTANCE"

# Generate a URL-safe password (letters, digits, - and _ only) straight into a secret.
python -c "import secrets,sys; sys.stdout.write(secrets.token_urlsafe(24))" > /tmp/dbpass
gcloud sql users create "$DB_USER" --instance="$SQL_INSTANCE" --password="$(cat /tmp/dbpass)"
gcloud secrets create mindtrack-db-pass --replication-policy=automatic --data-file=/tmp/dbpass
rm /tmp/dbpass
```

`db-f1-micro` is the smallest shared-core tier: fine for a college project, not for heavy load.

## 4. Store the app secrets in Secret Manager

Run from the `mindtrack` folder. Values are piped from your local `.env` and never echoed.

```bash
# The ORIGINAL encryption key (required to read existing data)
.venv/Scripts/python.exe -c "from dotenv import dotenv_values; import sys; sys.stdout.write(dotenv_values('.env')['MINTRACK_ENCRYPTION_KEY'])" \
  | gcloud secrets create mindtrack-encryption-key --replication-policy=automatic --data-file=-

# A fresh SECRET_KEY for production
python -c "import secrets,sys; sys.stdout.write(secrets.token_hex(32))" \
  | gcloud secrets create mindtrack-secret-key --replication-policy=automatic --data-file=-
```

Confirm the stored encryption key is the one your data was encrypted with. Both commands print
only a 12-character fingerprint; they must match (the migration dry run also prints it):

```bash
.venv/Scripts/python.exe -c "from dotenv import dotenv_values; import hashlib; print(hashlib.sha256(dotenv_values('.env')['MINTRACK_ENCRYPTION_KEY'].encode()).hexdigest()[:12])"
gcloud secrets versions access 1 --secret=mindtrack-encryption-key | python -c "import sys,hashlib; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest()[:12])"
```

Keep an offline copy of the encryption key somewhere safe (e.g. a password manager). If it is lost,
encrypted data is unrecoverable.

## 5. Service account for Cloud Run

```bash
gcloud iam service-accounts create mindtrack-run --display-name="MindTrack Cloud Run"
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$RUN_SA" --role=roles/cloudsql.client
for s in mindtrack-secret-key mindtrack-encryption-key mindtrack-db-pass; do
  gcloud secrets add-iam-policy-binding "$s" --member="serviceAccount:$RUN_SA" --role=roles/secretmanager.secretAccessor
done
```

## 6. Migrate the SQLite data (run locally, before the first deploy)

The script `scripts/migrate_sqlite_to_postgres.py`:
- opens `instance/mindtrack.db` **read-only** and is a dry run unless you pass `--execute`;
- checks NOT NULL / length limits / foreign keys that PostgreSQL enforces but SQLite didn't;
- checks every encrypted value decrypts with your key, then copies it **byte-for-byte**;
- refuses to write into a non-empty database, copies in one transaction, resets ID sequences,
  and verifies row counts and checksums for every table.

1. Stop the local app (so the SQLite file doesn't change mid-copy) and make an extra dated copy
   (this does not touch the existing files):
   ```bash
   cp instance/mindtrack.db "instance/mindtrack-premigration-$(date +%Y%m%d).db"
   ```
2. Take an on-demand backup of the empty Cloud SQL instance (gives you a clean restore point):
   ```bash
   gcloud sql backups create --instance="$SQL_INSTANCE"
   ```
3. Start the Cloud SQL Auth Proxy in a separate terminal (download `cloud-sql-proxy` for Windows from
   https://cloud.google.com/sql/docs/postgres/sql-proxy). It uses your `gcloud auth application-default login` credentials:
   ```bash
   gcloud auth application-default login
   ./cloud-sql-proxy "$INSTANCE_CONNECTION_NAME" --port 5432
   ```
4. Dry run, then the real copy:
   ```bash
   export TARGET_DATABASE_URL="postgresql+psycopg://$DB_USER:$(gcloud secrets versions access latest --secret=mindtrack-db-pass)@127.0.0.1:5432/$DB_NAME"
   .venv/Scripts/python.exe scripts/migrate_sqlite_to_postgres.py --source instance/mindtrack.db
   .venv/Scripts/python.exe scripts/migrate_sqlite_to_postgres.py --source instance/mindtrack.db --execute
   unset TARGET_DATABASE_URL
   ```
   Every table must show `checksum=OK`. To redo it, recreate the empty database
   (`gcloud sql databases delete/create`) and run again.

Starting with no data instead? Create the tables with `flask --app run.py init-db` while the proxy is
running and `DATABASE_URL` points at it.

## 7. Deploy to Cloud Run

```bash
gcloud run deploy "$SERVICE" --source . --region="$REGION" \
  --service-account="$RUN_SA" \
  --add-cloudsql-instances="$INSTANCE_CONNECTION_NAME" \
  --set-env-vars="MINDTRACK_ENV=production,INSTANCE_CONNECTION_NAME=$INSTANCE_CONNECTION_NAME,DB_NAME=$DB_NAME,DB_USER=$DB_USER" \
  --set-secrets="SECRET_KEY=mindtrack-secret-key:latest,MINTRACK_ENCRYPTION_KEY=mindtrack-encryption-key:1,DB_PASS=mindtrack-db-pass:latest" \
  --allow-unauthenticated --memory=512Mi --min-instances=0 --max-instances=3
```

- `--source .` uploads this folder (minus `.gcloudignore`: no `.env`, no `instance/`) and builds the `Dockerfile`.
- The encryption key is pinned to **version 1**, so adding a secret version later can never silently swap the key.
- `--allow-unauthenticated` is required for Firebase Hosting to reach the service; MindTrack still requires login for all personal pages.
- With 3 instances × (5 + 2) pooled connections the app uses at most ~21 Cloud SQL connections.

Check the service URL it prints: `https://...run.app/health` should return `OK`, then log in there.

## 8. Connect Firebase Hosting

```bash
firebase projects:addfirebase "$PROJECT_ID"   # only if the GCP project isn't a Firebase project yet
firebase use --add "$PROJECT_ID"              # creates .firebaserc (safe to commit)
firebase deploy --only hosting
```

`firebase.json` rewrites every path (pages and `/static/...`) to the Cloud Run service `mindtrack`
in `asia-south1`. `firebase-public/` is intentionally empty, so nothing is served from Hosting itself.

## 9. After deploying — check on the `web.app` URL

1. `/health` → `OK`; landing page CSS, fonts, images and the floral hero load.
2. Register/log in, then log out and back in (confirms the `__session` cookie and CSRF work through Hosting).
3. Open a migrated Mindy conversation from Reports → it shows readable text (confirms the original key).
4. Write a journal entry, edit it, view Insights, download a PDF report.
5. Times on the Journal page match your local time after one page load (the browser reports its offset once).

If a form says "The CSRF token is missing", confirm the session cookie is named `__session`
(`MINDTRACK_ENV=production` is set) and that you're on one domain (don't switch between web.app and run.app mid-session).

## 10. Rollback

- **App code:** list revisions and send all traffic back to the previous one:
  ```bash
  gcloud run revisions list --service="$SERVICE" --region="$REGION"
  gcloud run services update-traffic "$SERVICE" --region="$REGION" --to-revisions=<PREVIOUS_REVISION>=100
  ```
- **Hosting config:** Firebase console → Hosting → Release history → Roll back.
- **Database:** restore a Cloud SQL backup (overwrites the instance's current data):
  ```bash
  gcloud sql backups list --instance="$SQL_INSTANCE"
  gcloud sql backups restore <BACKUP_ID> --restore-instance="$SQL_INSTANCE"
  ```
- **Last resort:** your local `instance/mindtrack.db` and backups are untouched by every step here,
  but they won't contain anything written in production after the cutover.

## 11. Stopping costs

Cloud SQL bills while the instance exists. To pause: `gcloud sql instances patch "$SQL_INSTANCE" --activation-policy=NEVER`.
To remove everything: delete the Cloud Run service, the Cloud SQL instance (after exporting data), and the secrets.

---

### Verified locally before writing this guide
- Full test suite (`pytest`), including production-config and migration-script tests.
- Production mode in-process: debug off, `__session` cookie with `Secure; HttpOnly; SameSite=Lax`,
  CSRF rejects tokenless posts, register → login → dashboard works, static files `public, max-age=3600`,
  pages `private, no-cache`.
- psycopg driver loads; Cloud SQL socket URLs parse.
- Migration dry run on a copy of `instance/mindtrack.db` (all encrypted values decrypt), and a full
  copy into a scratch SQLite database with matching checksums.

### Not verified (needs the real environment)
- Building the Docker image and running Gunicorn (no Docker locally; Gunicorn doesn't run on Windows).
- A real PostgreSQL / Cloud SQL connection and the PostgreSQL sequence reset.
- Firebase Hosting → Cloud Run forwarding behaviour.
