# FSU4C — Google Chat Intelligence Ingestor

**Chimera Platform | Fractional Services Unit 4C**

FSU4C is the Google Chat data collection FSU for the Chimera platform. It polls registered Google Chat spaces for new messages, stores raw and processed records in its own isolated GCS and Firestore collections, and exposes a queryable registry API for downstream consumers (primarily FSU4, the intelligence processor).

FSU4C is a **pure ingestor** — it does not run AI tagging, send replies, or generate action items. Those responsibilities belong to FSU4.

---

## Architecture

```
Cloud Scheduler (every 5 min)
  → Pub/Sub topic: fsu4c-trigger
    → Cloud Run: FSU4C
      → Chat API: poll registered spaces
        → GCS: chimera-ops-chat-raw
        → Firestore: fsu4c-intelligence
```

FSU4 (the processor) queries FSU4C's `/v1/registry` endpoint using a registered API key to pick up new records for AI tagging and action processing.

---

## GCP Resources

| Resource | Name |
|---|---|
| GCP Project | `chimera-v4` |
| Region | `europe-west2` |
| Cloud Run | `fsu4c` |
| Service Account | `fsu4c-runner@chimera-v4.iam.gserviceaccount.com` |
| GCS Bucket | `chimera-ops-chat-raw` |
| Firestore collection | `fsu4c-intelligence` |
| Firestore spaces | `fsu4c-spaces` |
| Firestore API keys | `fsu4c-api-keys` |
| Pub/Sub topic | `fsu4c-trigger` |
| Pub/Sub subscription | `fsu4c-sub` |

---

## API Endpoints

### System (no auth)
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness probe |
| GET | `/status` | Firestore + registry stats |
| GET | `/version` | FSU version info |

### Ingest
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/v1/ingest/pubsub-push` | None | Pub/Sub push receiver |
| POST | `/v1/ingest/manual` | Key | Force poll a space or all spaces |
| GET | `/v1/ingest/queue` | Key | View pending records |

### Registry
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/v1/registry` | Key | Query collected records |
| GET | `/v1/registry/metrics` | Key | Stats by status / space |
| GET | `/v1/registry/{record_id}` | Key | Fetch single record |

### Spaces
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/v1/spaces` | Key | List registered spaces |
| POST | `/v1/spaces` | Key | Register a space |
| POST | `/v1/spaces/discover` | Key | Discover available spaces from Chat API |
| DELETE | `/v1/spaces/{space_id}` | Key | Deregister a space |

### Config
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/v1/config` | Key | Current processing config |
| PUT | `/v1/config` | Key | Update config |
| GET | `/v1/config/schema` | Key | JSON schema for config |

### Auth / API Key Management
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/v1/auth/keys` | Key | Issue a new API key |
| GET | `/v1/auth/keys` | Key | List all issued keys (masked) |
| GET | `/v1/auth/keys/{key_id}` | Key | Get key detail |
| DELETE | `/v1/auth/keys/{key_id}` | Key | Revoke a key |

**Auth header:** `X-Chimera-API-Key: <key>`

Two key types are accepted:
1. **Master key** — stored in Secret Manager as `fsu4c-chimera-api-key`
2. **Generated service key** — issued via `POST /v1/auth/keys`, stored hashed in Firestore

---

## CI/CD

Push to `main` on `github.com/charles-ascot/fsu4c` → Cloud Run Connect Repo auto-deploys.

The frontend (`frontend/`) deploys to Cloudflare Pages at `fsu4c.thync.online`.

---

---

## Annex A — Source Integration Methodology

This annex documents the standard procedure for connecting a new data source to FSU4C (Google Chat). It applies to all FSUs in the Chimera platform and should be updated whenever the integration methodology changes.

### A.1 Overview

Every FSU has exactly one data source. FSU4C's source is **Google Chat**, accessed via the Google Chat REST API v1 using OAuth 2.0 user credentials for the `chimera.data.in@gmail.com` account.

The integration model is **polling**, not push. Cloud Scheduler fires a trigger on a regular interval; FSU4C polls all registered spaces for new messages since the last poll cursor. This approach is used because Google Chat event subscriptions (push delivery) require Google Workspace, whereas `chimera.data.in` is a personal Gmail account.

### A.2 Google Account Setup

The account used for Chat ingestion is `chimera.data.in@gmail.com`. This is the same account used by FSU4 for Gmail ingestion.

**Why the same account?**
Using a single Google account avoids OAuth cross-domain issues. The same OAuth client registered in GCP project `chimera-v4` can request both Gmail and Chat API scopes. Separate tokens are stored for each FSU:
- FSU4: `gmail-token` secret (Gmail scopes)
- FSU4C: `chat-token` secret (Chat API scopes)

### A.3 OAuth Scopes Required

FSU4C requires the following OAuth 2.0 scopes for the `chimera.data.in` account:

```
https://www.googleapis.com/auth/chat.messages.readonly
https://www.googleapis.com/auth/chat.spaces.readonly
```

These are read-only scopes. FSU4C never sends Chat messages or modifies Chat data.

### A.4 OAuth Client Setup Procedure

1. In GCP Console → APIs & Services → Credentials, open the existing OAuth 2.0 client "FSU4 - Chimera Email Ingest" (or create a new client named "FSU4C - Chimera Chat Ingest" of type **Web application**).

2. Enable the **Google Chat API** in the GCP project:
   ```
   gcloud services enable chat.googleapis.com --project chimera-v4
   ```

3. Run the one-time OAuth consent flow locally to obtain a `chat-token`:
   ```python
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_secrets_file(
       'client_secret.json',
       scopes=[
           'https://www.googleapis.com/auth/chat.messages.readonly',
           'https://www.googleapis.com/auth/chat.spaces.readonly',
       ]
   )
   creds = flow.run_local_server(port=0)
   # Save creds.token, creds.refresh_token, etc. to Secret Manager
   ```
   Sign in as `chimera.data.in@gmail.com` when the browser opens.

4. Store the resulting token JSON in Secret Manager:
   ```
   Secret ID: chat-token
   Value:     {"token": "...", "refresh_token": "...", "token_uri": "https://oauth2.googleapis.com/token"}
   ```

5. Store the client credentials JSON in Secret Manager:
   ```
   Secret ID: chat-oauth-credentials
   Value:     {"client_id": "...", "client_secret": "...", "token_uri": "https://oauth2.googleapis.com/token"}
   ```

### A.5 Chat Space Registration

Google Chat spaces are not automatically monitored. Each space must be explicitly registered with FSU4C before it will be polled.

**Step 1 — Add `chimera.data.in` to the Chat space**
The `chimera.data.in` Google account must be a member of any space you want to monitor. A human administrator must add it manually via Google Chat.

**Step 2 — Discover available spaces**
```
POST /v1/spaces/discover
X-Chimera-API-Key: <master-key>
```
Returns all Chat spaces that `chimera.data.in` is a member of, with a flag indicating whether each is already registered.

**Step 3 — Register the space**
```
POST /v1/spaces
X-Chimera-API-Key: <master-key>
Content-Type: application/json

{
  "space_resource_name": "spaces/AAAA1234",
  "description": "Optional description"
}
```
FSU4C will fetch the space's display name and type from the Chat API and store it in Firestore (`fsu4c-spaces` collection). From the next poll cycle onward, messages from this space will be ingested.

### A.6 Cloud Scheduler Setup

FSU4C is triggered by a Cloud Scheduler job that publishes to the `fsu4c-trigger` Pub/Sub topic:

```
Schedule:   */5 * * * *   (every 5 minutes)
Target:     Pub/Sub topic projects/chimera-v4/topics/fsu4c-trigger
Payload:    {"trigger": "scheduler"}
```

The Pub/Sub subscription `fsu4c-sub` delivers this message to:
```
https://fsu4c-<HASH>-ew.a.run.app/v1/ingest/pubsub-push
```

To create the scheduler job:
```bash
gcloud scheduler jobs create pubsub fsu4c-poll \
  --schedule="*/5 * * * *" \
  --topic=fsu4c-trigger \
  --message-body='{"trigger":"scheduler"}' \
  --location=europe-west2 \
  --project=chimera-v4
```

### A.7 Service Account IAM Roles

The Cloud Run service account `fsu4c-runner@chimera-v4.iam.gserviceaccount.com` requires the following roles:

| Role | Purpose |
|---|---|
| `roles/secretmanager.secretAccessor` | Read OAuth credentials and API key from Secret Manager |
| `roles/datastore.user` | Read/write Firestore collections |
| `roles/storage.objectAdmin` | Read/write GCS bucket `chimera-ops-chat-raw` |
| `roles/pubsub.subscriber` | Receive Pub/Sub push messages |
| `roles/logging.logWriter` | Write Cloud Logging entries |
| `roles/cloudtrace.agent` | Write Cloud Trace spans |

Grant all roles:
```bash
SA="fsu4c-runner@chimera-v4.iam.gserviceaccount.com"
PROJECT="chimera-v4"
for ROLE in secretmanager.secretAccessor datastore.user storage.objectAdmin pubsub.subscriber logging.logWriter cloudtrace.agent; do
  gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:$SA" \
    --role="roles/$ROLE"
done
```

### A.8 GCS Bucket Setup

```bash
gcloud storage buckets create gs://chimera-ops-chat-raw \
  --location=europe-west2 \
  --project=chimera-v4 \
  --uniform-bucket-level-access
```

Storage layout:
```
chimera-ops-chat-raw/
  raw/{year}/{month}/{day}/{space_slug}/{message_slug}/
    message.json          ← raw Chat API message payload
  processed/{record_id}/
    record.json           ← complete ChatRecord
  index/
    daily_manifest_{YYYY-MM-DD}.json
```

### A.9 API Key Registry Protocol

Every service that needs to call FSU4C's protected endpoints must register and obtain an API key. The key is issued once and never stored in plaintext — only its SHA-256 hash is kept in Firestore.

**Issuing a key (admin, using master key):**
```
POST /v1/auth/keys
X-Chimera-API-Key: <master-key>

{
  "service_name": "fsu4-processor",
  "description": "FSU4 polling FSU4C registry for new Chat records"
}
```

Response includes `api_key` in plaintext — **store it immediately** in Secret Manager. It will not be shown again.

**Key registry fields:**
`key_id`, `service_name`, `key_prefix` (for display), `issued_by`, `created_at`, `last_used_at`, `active`

**Revoking a key:**
```
DELETE /v1/auth/keys/{key_id}
X-Chimera-API-Key: <master-key>
```

The future AI conductor will manage this registry across all FSUs using a key registered with each FSU's `/v1/auth/keys` endpoint.

### A.10 Environment Variables

FSU4C uses no runtime environment variables. All configuration is loaded from:
- **GCP Secret Manager** — credentials (loaded once at startup, cached with `@lru_cache`)
- **Firestore** — processing config (document `chimera-fsu-config/fsu4c-config`)

The only deployment-time configuration is the Cloud Run service URL, which is used by the Pub/Sub subscription push endpoint and the Cloudflare Pages `VITE_API_URL` environment variable.

### A.11 Adding a New FSU (Standard Procedure)

When adding any new FSU to the Chimera platform, follow this checklist:

- [ ] Create new GCP service account `fsuXY-runner@chimera-v4.iam.gserviceaccount.com`
- [ ] Grant required IAM roles (see A.7 as template)
- [ ] Create source-specific GCS bucket
- [ ] Create Pub/Sub topic and subscription for the FSU
- [ ] Store OAuth/API credentials in Secret Manager
- [ ] Create Cloud Scheduler job to trigger the FSU
- [ ] Create Cloud Run service, connected to GitHub repo
- [ ] Issue a master API key (`fsuXY-chimera-api-key`) in Secret Manager
- [ ] Issue a service key from each other FSU that will call this one
- [ ] Register the service key in the calling FSU's API key registry
- [ ] Add FSU entry to the Chimera platform registry (managed by AI conductor)
- [ ] Deploy Cloudflare Pages frontend at `fsuXY.thync.online`
- [ ] Document source integration in this FSU's README Annex A
