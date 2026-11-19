# Keitaro Campaign Manager

A wrapper around the **Keitaro** tracker Admin API.

1. **Campaign creator**: a name, a geo and an offer give you a Keitaro campaign with two streams:
   * stream 1: visitors from the selected countries → redirect to `google.com`;
   * stream 2: everyone else → the selected offer (100 %).
   Domain, group and traffic source are filled in from defaults (`kylovoa.com`, `FORTESTS`, `FORTESTS`) or can be picked in the form.
2. **Campaign editor**: add, remove and bring back offers in a stream, pin a share manually, rebalance the percentages, publish to Keitaro (*Push*) or discard the draft (*Cancel*).

**Stack:** FastAPI · SQLAlchemy 2 (async) · Alembic · httpx · Pydantic v2 · PostgreSQL / SQLite · React 19 + TypeScript + Vite + Tailwind CSS v4.

![Create campaign](docs/create.png)
![Editor](docs/editor-draft.png)

---

## Quick start

### Option A: Docker (PostgreSQL)

```bash
cp .env.example .env          # set KEITARO_URL and KEITARO_API_KEY
docker compose up --build
```

Open http://localhost:8000 for the UI and http://localhost:8000/docs for Swagger.
The React app is built inside the image and served by FastAPI. Migrations run automatically when the container starts (`alembic upgrade head`).

### Option B: local (SQLite)

Requirements: Python 3.11+, Node.js 20.19+ or 22.12+ (Vite 8).

**Backend** (terminal 1):

```bash
python -m venv .venv
source .venv/bin/activate     # Windows Git Bash: source .venv/Scripts/activate · PowerShell: .venv\Scripts\activate
pip install -r backend/requirements.txt
cp .env.example .env          # set KEITARO_URL and KEITARO_API_KEY

cd backend
alembic upgrade head          # creates backend/adrobot.db
uvicorn app.main:app --reload # http://localhost:8000
```

**Frontend** (terminal 2):

```bash
cd frontend && npm install && npm run dev   # http://localhost:5173; /api, /docs, /openapi.json are proxied to :8000
```

Other scripts: `npm run typecheck` (TypeScript only) and `npm run build` (type check + production build into `frontend/dist`).
To serve the UI from FastAPI instead (single port), run `npm run build`. FastAPI then serves `frontend/dist` at http://localhost:8000.

### Tests

```bash
cd backend
pytest -q        # 54 tests: share allocator, creator, editor, sync, API
```

### Migrations

```bash
cd backend
alembic upgrade head                                  # apply
alembic revision --autogenerate -m "description"      # new migration after changing models
alembic downgrade -1                                  # roll back the last one
```

`DATABASE_URL` is read from `.env`. It defaults to SQLite; Docker uses PostgreSQL.

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `KEITARO_URL` | – | Tracker URL without `/admin_api/v1`, e.g. `https://tlgk.host` |
| `KEITARO_API_KEY` | – | Keitaro admin → Profile → API keys |
| `KEITARO_MOCK` | `false` | `false` → real Keitaro (`client.py`); `true` → in-memory fake tracker (`fake.py`), no key needed |
| `DATABASE_URL` | SQLite `backend/adrobot.db` | e.g. `postgresql+asyncpg://user:pass@localhost:5432/db` |
| `DEFAULT_DOMAIN` | `kylovoa.com` | Default domain (looked up by name) |
| `DEFAULT_GROUP` | `FORTESTS` | Default campaign group (looked up by name) |
| `DEFAULT_TRAFFIC_SOURCE` | `FORTESTS` | Default traffic source (looked up by name) |
| `GEO_REDIRECT_URL` | `https://google.com` | Where visitors from the selected countries are sent |
| `OFFERS_CACHE_TTL_SECONDS` | `600` | Offer autocomplete cache lifetime |

If a default name is not found and the tracker has exactly one domain / group / source, that one is used.

### Demo mode

Set `KEITARO_MOCK=true`. The app then uses an in-memory fake Keitaro with sample offers instead of the real tracker, so you can try the whole UI without an API key and without creating anything in Keitaro. Restart the backend after changing `.env`.

When switching from demo to real mode, reset the local database so cached demo offers are gone:

```bash
cd backend
rm -f adrobot.db && alembic upgrade head
```

---

## Project structure

```
keitaro-campaign-manager/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app, lifespan, error handler, serves the frontend
│   │   ├── core/
│   │   │   ├── config.py               # Settings (pydantic-settings, .env)
│   │   │   └── exceptions.py           # domain errors → HTTP status codes
│   │   ├── db/
│   │   │   ├── base.py                 # DeclarativeBase + naming convention + timestamps
│   │   │   └── session.py              # async engine / session
│   │   ├── models/                     # SQLAlchemy models
│   │   │   ├── campaign.py             # campaign (local mirror of Keitaro)
│   │   │   ├── stream.py               # stream
│   │   │   ├── stream_offer.py         # offer in a stream: draft + published snapshot
│   │   │   └── offer.py                # offer cache for autocomplete
│   │   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── integrations/keitaro/
│   │   │   ├── base.py                 # client Protocol
│   │   │   ├── client.py               # Admin API v1 HTTP client (httpx, Api-Key header)
│   │   │   ├── payloads.py             # JSON builders for the campaign and streams
│   │   │   └── fake.py                 # in-memory Keitaro for tests and demo mode
│   │   ├── services/                   # business logic
│   │   │   ├── share_allocator.py      # pure share-distribution function
│   │   │   ├── campaign_creator.py     # part 1 + rollback on failure
│   │   │   ├── campaign_sync.py        # import / refresh a campaign from Keitaro
│   │   │   ├── stream_editor.py        # part 2: add/remove/restore/pin/push/cancel
│   │   │   ├── offer_catalog.py        # offer sync and search
│   │   │   └── keitaro_meta.py         # domains, groups, sources, defaults by name
│   │   └── api/
│   │       ├── deps.py                 # DI: session, Keitaro client, services
│   │       └── v1/  meta.py · campaigns.py · streams.py · router.py
│   ├── alembic/                        # migrations (async env.py)
│   ├── tests/                          # pytest + httpx ASGITransport + FakeKeitaroClient
│   ├── alembic.ini · pyproject.toml · requirements.txt
├── frontend/                           # React 19 + TypeScript + Vite + Tailwind CSS v4
│   ├── src/
│   │   ├── api/
│   │   │   ├── types.ts                # interfaces mirroring the backend schemas
│   │   │   └── client.ts               # fetch wrapper, one function per endpoint, readable errors
│   │   ├── components/
│   │   │   ├── OfferAutocomplete.tsx   # debounced offer search, ignores stale responses, ↑ ↓ Enter Esc
│   │   │   ├── StreamCard.tsx          # stream + offers table: add / remove / pin, push / cancel
│   │   │   ├── Toast.tsx               # toasts + useAction (busy flag, errors as toasts)
│   │   │   └── ui.tsx                  # Button, Tag, Card, Field
│   │   ├── pages/
│   │   │   ├── CreateCampaign.tsx      # part 1: form + result card
│   │   │   └── CampaignEditor.tsx      # part 2: campaign list + stream cards
│   │   ├── format.ts                   # filter text, stream ordering
│   │   ├── App.tsx                     # top bar, tabs, /meta, demo-mode banner
│   │   └── main.tsx · index.css        # entry point; index.css only imports Tailwind
│   ├── vite.config.ts                  # Tailwind plugin, dev proxy /api · /docs · /openapi.json → :8000
│   ├── tsconfig.json                   # strict mode
│   └── package.json                    # dev · build · preview · typecheck
├── Dockerfile (multi-stage: node build → python) · docker-compose.yml · .env.example
```

The code is split into layers: **API** (validation, HTTP) → **services** (logic, transactions) → **integrations** (Keitaro) / **models** (database). The Keitaro client is injected through DI as a `Protocol`. Tests replace it with a fake, so no HTTP mocking is needed.

---

## How it works

### Part 1: creating a campaign

`POST /api/v1/campaigns`

```json
{ "name": "test_rasulzade_campaign1", "geo": "AU, MX", "offer_id": 18813 }
```

1. The geo is normalized: `mx, au` → `["MX","AU"]`, duplicates are removed and every code is checked as ISO-3166 alpha-2.
2. The offer is checked (cache first, then Keitaro). Domain, group and source come from the request, or are looked up by the names set in `.env`.
3. `POST /campaigns` with `type: position`, `cost_type: CPC` and `cost_auto: true` (cost taken from the `cost` parameter).
4. `POST /streams` for stream 1: `schema: redirect`, `action_type: http`, `action_payload: https://google.com`,
   `filters: [{name: "country", mode: "accept", payload: [...]}]`.
5. `POST /streams` for stream 2: `schema: landings`, `offers: [{offer_id, share: 100, state: "active"}]`.
6. If step 4 or 5 fails, the campaign is deleted in Keitaro so no half-built campaign is left behind. The client gets a 502 with the error message.

### Part 2: the editor

Every edit goes into a **local draft** first (the `stream_offers` table). Nothing is sent to Keitaro until *Push*.
Each offer keeps its draft (`share`, `status`, `is_pinned`) next to a published snapshot (`published_share`, `published_status`).

**Share rules** (`services/share_allocator.py`):
* active shares always sum to exactly 100;
* a pinned offer keeps the value that was typed in;
* the rest is split evenly between unpinned offers, and the remainder goes to the first ones: 3 offers → 34 / 33 / 33;
* every active offer gets at least 1 %. If there is no room for that, the API returns 422 and nothing changes.

| Action | What happens |
|---|---|
| Add offer | a new active offer is added and shares are rebalanced |
| Type a % | the offer is pinned with that value and the others are rebalanced |
| 📌 | toggles the pin |
| Remove | a published offer is marked `removed` (0 %, can be brought back); a draft offer is deleted |
| Bring back | restores a removed offer and rebalances |
| Push to Keitaro | validates the stream (at least 1 offer, sum is 100), then `PUT /streams/{id}` with the active offers |
| Cancel | draft offers are deleted; the rest go back to their published values |
| Fetch from Keitaro | reloads the streams; the draft is replaced with what the tracker has |

The editor can open **any** campaign in Keitaro, not only the ones created here. A campaign is imported the first time it is opened.

### API

| Method | Path | |
|---|---|---|
| GET | `/api/v1/meta` | domains, groups, sources + defaults |
| GET | `/api/v1/offers?q=` | offer autocomplete (by name or ID) |
| POST | `/api/v1/offers/sync` | refresh the offer cache |
| POST | `/api/v1/campaigns` | create a campaign |
| GET | `/api/v1/campaigns?q=` | list Keitaro campaigns |
| GET | `/api/v1/campaigns/{id}` | campaign with its streams |
| POST | `/api/v1/campaigns/{id}/sync` | reload from Keitaro |
| POST | `/api/v1/streams/{id}/offers` | add an offer |
| DELETE | `/api/v1/streams/{id}/offers/{offer_id}` | remove an offer |
| POST | `/api/v1/streams/{id}/offers/{offer_id}/restore` | bring an offer back |
| PATCH | `/api/v1/streams/{id}/offers/{offer_id}` | `{"share": 60}` pins, `{"share": null}` unpins |
| POST | `/api/v1/streams/{id}/push` | publish to Keitaro |
| POST | `/api/v1/streams/{id}/cancel` | discard the draft |

Every editor endpoint returns the whole stream (`offers`, `total_share`, `is_dirty`), so the frontend just replaces that stream in its state.

---

## Notes on the test tracker

- The test API key can see only one offer (`18813`). Other offers return 403, so in the editor they are shown as `Offer #ID`. The editor can be fully tested in demo mode (`KEITARO_MOCK=true`).
- The tracker is shared between candidates. During testing the `FORTESTS` traffic source was deleted by someone; the app then refuses to create a campaign and shows a clear error instead of creating a half-configured one.
- Test campaigns are named with a personal prefix, e.g. `test_rasulzade_campaign1`.