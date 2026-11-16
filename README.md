# Automated Posting

A small FastAPI service that takes one short message with a CTA link and publishes it to six platforms at the same time.

`POST /posting` validates the message, posts it to every platform concurrently and returns a per-platform result. If one platform fails (bad token, rate limit, timeout), the others still go through.

## Platforms

| Platform | API used | What gets created | Public |
|---|---|---|---|
| Telegram | [Bot API `sendMessage`](https://core.telegram.org/bots/api#sendmessage) | Message in a public channel | Yes |
| Mastodon | [`POST /api/v1/statuses`](https://docs.joinmastodon.org/methods/statuses/#create) | Public toot | Yes |
| Bluesky | [AT Protocol `createSession` + `createRecord`](https://docs.bsky.app/docs/advanced-guides/posts) | Post with a clickable link facet | Yes |
| GitHub Gist | [`POST /gists`](https://docs.github.com/en/rest/gists/gists#create-a-gist) | Public gist | Yes |
| Dev.to | [Forem `POST /api/articles`](https://developers.forem.com/api/v1#tag/articles/operation/createArticle) | Published article | Yes |
| Discord | [Webhook `?wait=true`](https://discord.com/developers/docs/resources/webhook#execute-webhook) | Message in a server channel | No (members only) |

A few notes from the research:

- **Bluesky** doesn't auto-detect links. You have to send a "facet" with the link's position, and the positions are UTF-8 **byte** offsets, not character indexes. That's why `link_facet()` encodes the text first; otherwise any emoji before the link breaks it.
- **Telegram** only gives a public `t.me/<channel>/<id>` link for public channels. For a private channel the message is sent but reported as failed, because there is no public URL to return.
- **Discord** webhooks return nothing unless you pass `wait=true`. The message link needs the server (guild) ID, which the webhook response doesn't include, so it's a config value. Discord messages are only visible to server members, so `public_access` is `false`.
- **Dev.to** needs a title. It's built from the message with the link stripped out. Dev.to rate-limits article creation fairly hard, so posting twice in quick succession returns a 429. That's a handy way to see the "one fails, the rest continue" behaviour.

## Validation

- Message can't be empty and can't be longer than 200 characters (after trimming whitespace).
- It must contain **exactly one** `http(s)://` link.
- The link must be a valid URL with a real host (`https://localhost` or `https://foo` are rejected).
- Trailing punctuation is ignored, so `...visit https://example.com.` works.

Invalid input returns `422` with the reason.

Platforms are picked by the app (everything in `PLATFORMS` in `app/services/posting_service.py`), not by the request.

## Project layout

```text
app/
  main.py                  FastAPI app and the /posting route
  schemas.py               request validation and response models
  config.py                credentials loaded from .env
  platforms/
    base.py                Platform base class
    telegram.py  mastodon.py  bluesky.py
    github_gist.py  devto.py  discord.py
  services/
    posting_service.py     concurrent posting and error handling
tests/
  test_posting.py
```

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/muffaddal/automated-posting.git
cd automated-posting
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`. Any platform left blank is reported as `failed` with `missing credentials`, and the app still runs.

| Variable | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL` | Create a bot with [@BotFather](https://t.me/BotFather), make a public channel, add the bot as an admin. Channel is `@channelname`. |
| `MASTODON_BASE_URL`, `MASTODON_ACCESS_TOKEN` | Your instance > Preferences > Development > New application, scope `write:statuses`. |
| `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | Settings > Privacy and security > App passwords. Don't use your main password. |
| `GITHUB_TOKEN` | GitHub > Settings > Developer settings > Personal access tokens, with the `gist` scope. |
| `DEVTO_API_KEY` | dev.to > Settings > Extensions > DEV Community API Keys. |
| `DISCORD_WEBHOOK_URL`, `DISCORD_GUILD_ID` | Channel settings > Integrations > Webhooks. Guild ID: enable Developer Mode, right-click the server > Copy Server ID. |

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Swagger docs: http://localhost:4000/docs

## Sample request

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

### Response with no credentials configured

```json
{
  "success": false,
  "results": [
    {"platform": "Telegram", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "missing credentials"},
    {"platform": "Mastodon", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "missing credentials"},
    {"platform": "Bluesky", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "missing credentials"},
    {"platform": "GitHub Gist", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "missing credentials"},
    {"platform": "Dev.to", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "missing credentials"},
    {"platform": "Discord", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "missing credentials"}
  ]
}
```

### Validation error

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "two links https://a.com https://b.com"}'
```

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "message"],
      "msg": "Value error, message must contain exactly one CTA link, found 2",
      "input": "two links https://a.com https://b.com",
      "ctx": {"error": {}}
    }
  ]
}
```

## Logs

Each platform result is logged:

```text
INFO:     Uvicorn running on http://0.0.0.0:4000 (Press CTRL+C to quit)
2026-11-16 16:55:18,950 WARNING posting: Telegram skipped: missing credentials
2026-11-16 16:55:18,950 WARNING posting: Mastodon skipped: missing credentials
2026-11-16 16:55:18,950 WARNING posting: Bluesky skipped: missing credentials
2026-11-16 16:55:18,950 WARNING posting: GitHub Gist skipped: missing credentials
2026-11-16 16:55:18,950 WARNING posting: Dev.to skipped: missing credentials
2026-11-16 16:55:18,950 WARNING posting: Discord skipped: missing credentials
INFO:     127.0.0.1:61026 - "POST /posting HTTP/1.1" 200 OK
INFO:     127.0.0.1:61028 - "POST /posting HTTP/1.1" 422 Unprocessable Entity
```

## Tests

```bash
pytest -q
```

The tests don't touch the network. They cover the validation rules, the "one fails, others continue" behaviour, missing credentials, Bluesky byte offsets, and each platform's URL building against mocked API responses (`httpx.MockTransport`).

## Response fields

| Field | Meaning |
|---|---|
| `platform` | Platform name |
| `status` | `success` or `failed` |
| `posted_url` | Link to the published content |
| `public_access` | Whether anyone can open the link without logging in |
| `date`, `time` | When it was posted (UTC) |
| `error` | Why it failed, e.g. `HTTP 401: ...`, `request timed out`, `missing credentials` |

The top-level `success` is `true` if at least one platform worked.
