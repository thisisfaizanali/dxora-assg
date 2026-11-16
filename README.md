# Automated Multi-Platform Posting System

A FastAPI service with a single endpoint, `POST /posting`, that takes one message and publishes it to 5 platforms through their official HTTP APIs.
It returns a per-platform result with the posted URL, whether the page is publicly reachable, and a timestamp.

## Features

- Single endpoint: `POST /posting`
- Input validation (length, exactly one CTA link, valid URL)
- 5 platform integrations behind one `Platform` interface
- Automatic posting to all platforms in parallel
- One platform failing never stops the others
- Public access verified by an anonymous GET after posting
- Credentials and settings via environment variables (all optional)
- Tests with mocked HTTP, no network needed

## Platforms

| Platform | API used | Auth | Posted URL | Retention |
|---|---|---|---|---|
| [Telegraph](https://telegra.ph/api) | `POST https://api.telegra.ph/createAccount` + `createPage` | Anonymous token created per run, or `TELEGRAPH_ACCESS_TOKEN` | `telegra.ph/<page>` | Permanent |
| [dpaste](https://docs.dpaste.org/api/) | `POST https://dpaste.org/api/` | None | `dpaste.org/<id>` | 30 days, set by `expires` |
| [paste.rs](https://paste.rs/web) | `POST https://paste.rs/` | None | `paste.rs/<id>` | No stated expiry |
| [ntfy](https://docs.ntfy.sh/publish/) | `POST https://ntfy.sh/<topic>` | None | `ntfy.sh/<topic>` | About 12 hours in the ntfy.sh cache |
| [Rentry](https://github.com/radude/rentry) | `POST https://rentry.co/api/new` | None | `rentry.co/<slug>` | No stated expiry |

### Why these platforms

All five have official, documented HTTP APIs that publish publicly without creating an account, so the project runs end to end with zero credentials.
Account-based platforms (Mastodon, Bluesky, Dev.to, Telegram bots) fit the same `Platform` interface: one extra class each, plus their token in `.env`.
The brief mentions LLM platforms. LLM APIs generate text but do not publish public content, so none is included as a posting target.

## Setup

Requires Python 3.12.

```bash
git clone https://github.com/thisisfaizanali/dxora-assg.git
cd dxora-assg
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Optional: copy `.env.example` to `.env` to change settings (every variable is optional).

Run the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Swagger UI: http://localhost:4000/docs

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `HTTP_TIMEOUT_SECONDS` | `15` | Timeout for every outgoing HTTP request |
| `TELEGRAPH_ACCESS_TOKEN` | empty | Reuse an existing Telegraph account. Empty means a new anonymous account is created on each run |
| `TELEGRAPH_AUTHOR_NAME` | `Automated Posting` | Author name shown on the Telegraph page |
| `NTFY_TOPIC` | `dxora-automated-posting-demo` | ntfy topic the message is published to |

## Usage

curl:

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Automated multi-platform posting demo built with FastAPI. Source: https://github.com/thisisfaizanali/dxora-assg"}'
```

PowerShell:

```powershell
Invoke-RestMethod -Uri http://localhost:4000/posting -Method Post -ContentType "application/json" `
  -Body '{"message": "Automated multi-platform posting demo built with FastAPI. Source: https://github.com/thisisfaizanali/dxora-assg"}'
```

## Sample response

Real output from a live run on 2026-11-16; date and time are UTC.
In this run Telegraph failed with a network error (the connection from the host to telegra.ph could not be established), while the other four platforms succeeded. This shows that one failing platform does not affect the rest.
An earlier live run the same day succeeded on all five platforms, including Telegraph: https://telegra.ph/Automated-multi-platform-posting-demo-built-with-FastAPI-So-11-16

Files: [request](docs/sample-request.json), [response](docs/sample-response.json).

```json
{
  "success": true,
  "results": [
    {
      "platform": "Telegraph",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Network error: ConnectError"
    },
    {
      "platform": "dpaste",
      "status": "success",
      "posted_url": "https://dpaste.org/62hKF",
      "public_access": true,
      "date": "2026-11-16",
      "time": "19:10:43",
      "error": null
    },
    {
      "platform": "paste.rs",
      "status": "success",
      "posted_url": "https://paste.rs/jkGTS",
      "public_access": true,
      "date": "2026-11-16",
      "time": "19:10:43",
      "error": null
    },
    {
      "platform": "ntfy",
      "status": "success",
      "posted_url": "https://ntfy.sh/dxora-automated-posting-demo",
      "public_access": true,
      "date": "2026-11-16",
      "time": "19:10:43",
      "error": null
    },
    {
      "platform": "Rentry",
      "status": "success",
      "posted_url": "https://rentry.co/r4oqs58i",
      "public_access": true,
      "date": "2026-11-16",
      "time": "19:10:43",
      "error": null
    }
  ]
}
```

## Validation

| Rule | Error message |
|---|---|
| Message is empty | `Message must not be empty.` |
| More than 200 characters | `Message must not exceed 200 characters (got <n>).` |
| Not exactly one link | `Message must contain exactly one CTA link (found <n>).` |
| Link has no http:// or https:// scheme | `CTA link must start with http:// or https://.` |
| Link is not a valid URL | `CTA link is not a valid URL.` |
| Link host has no dot | `CTA link must have a valid domain (e.g. example.com).` |

Invalid JSON, a missing `message` field or a non-string value also return 422 in the same `{success, errors[field, message]}` format.

Example (`{"message": "No link in this message"}`), saved in [docs/sample-validation-error.json](docs/sample-validation-error.json):

```json
{
  "success": false,
  "errors": [
    {
      "field": "message",
      "message": "Message must contain exactly one CTA link (found 0)."
    }
  ]
}
```

## Response fields

| Field | Meaning |
|---|---|
| `success` | `true` if at least one platform succeeded |
| `results[].platform` | Platform name |
| `results[].status` | `success` or `failed` |
| `results[].posted_url` | URL of the post, `null` on failure |
| `results[].public_access` | `true` if an anonymous GET confirmed the post is reachable |
| `results[].date` | UTC date of the post (`YYYY-MM-DD`), `null` on failure |
| `results[].time` | UTC time of the post (`HH:MM:SS`), `null` on failure |
| `results[].error` | Error text on failure, `null` on success |

## Error handling

Each platform runs in its own try block, so one failure is reported in its own result and never raises for the whole request.

- HTTP error from a platform: `HTTP <code>: <body excerpt>`
- Timeout: `Request timed out`
- Network error: `Network error: <type>`
- Anything else: `Unexpected error: <type>`

Error messages never include request URLs or tokens.

## Logs

The full server log of the live run is in [docs/sample-run.log](docs/sample-run.log). The posting lines:

```text
2026-11-17 00:40:42,620 WARNING app.posting: Telegraph: failed: Network error: ConnectError
2026-11-17 00:40:43,244 INFO app.posting: Rentry: posted https://rentry.co/r4oqs58i (public=True)
2026-11-17 00:40:43,339 INFO app.posting: dpaste: posted https://dpaste.org/62hKF (public=True)
2026-11-17 00:40:44,553 INFO app.posting: ntfy: posted https://ntfy.sh/dxora-automated-posting-demo (public=True)
2026-11-17 00:40:44,673 INFO app.posting: paste.rs: posted https://paste.rs/jkGTS (public=True)
```

Log timestamps use the host's local time (UTC+5:30); the response uses UTC.

## Project structure

```text
.
├── app/
│   ├── main.py                  # FastAPI app, POST /posting, 422 handler
│   ├── config.py                # Settings from environment variables
│   ├── schemas.py               # Request validation and response models
│   ├── services/
│   │   └── posting_service.py   # Runs all platforms in parallel, builds results
│   └── platforms/
│       ├── __init__.py          # PLATFORMS registry
│       ├── base.py              # Platform interface, PlatformError, ensure_ok
│       ├── telegraph.py
│       ├── dpaste.py
│       ├── paste_rs.py
│       ├── ntfy.py
│       └── rentry.py
├── tests/
│   ├── test_platforms.py        # One test group per platform, mocked HTTP
│   └── test_posting.py          # Endpoint and validation tests
├── docs/                        # Sample request, response and server log
├── .env.example
├── pytest.ini
└── requirements.txt
```

## Running tests

```bash
pytest -q
```

26 tests, all HTTP is mocked, so no network or credentials are needed.

## Limitations

- Public paste services have rate limits and can be down.
- ntfy messages expire after about 12 hours.
- telegra.ph is blocked or unreachable on some networks, so Telegraph can fail with a connection error depending on where the server runs.
- A new anonymous Telegraph account is created on every run unless `TELEGRAPH_ACCESS_TOKEN` is set.
- The endpoint has no auth or rate limiting; it is intended for local use.
- The ntfy public check keeps the last message id on the platform instance, which is fine for one request at a time.
