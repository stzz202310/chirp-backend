# Chirp — Backend

A production-deployed, Twitter-style backend built with Django — service decoupling, async task fanout, multi-layer caching, and containerized deployment, end-to-end.

**Live app:** https://chirp-app.dev/  
**Live API:** https://chirp-app.dev/api/users/1/ — see [API Overview](#api-overview) for all endpoints  
**Frontend repo:** [chirp-frontend](https://github.com/stzz202310/chirp-frontend)

**Demo accounts** (log in to explore — browse the newsfeed, post a tweet, like and comment, follow / unfollow each other, edit your profile):

| Username | Password |
|---|---|
| `dog_husky` | `test1234` |
| `cat_siamese` | `test1234` |

---

## Architecture

```
                          ┌─────────────────────────────┐
                          │     Browser (HTTPS)         │
                          └───────────────┬─────────────┘
                                          │
                          ┌───────────────▼────────────────┐
                          │  Nginx (EC2 host, port 443)    │
                          │  Let's Encrypt TLS termination │
                          └───────┬───────────────┬────────┘
                   /api/, /admin/ │               │ /, /static/
                          ┌───────▼───────┐  ┌────▼───────────┐
                          │  Gunicorn     │  │ React build    │
                          │  (2 workers)  │  │ (static files) │
                          └───────┬───────┘  └────────────────┘
                                  │
                          ┌───────▼────────┐
                          │  Django (DRF)  │
                          └─┬────┬────┬────┘
                            │    │    │
                   ┌────────┘    │    └─────────┐
              ┌────▼───┐   ┌─────▼────┐   ┌─────▼─────┐
              │ MySQL  │   │  Redis   │   │ Memcached │
              └────────┘   └─────┬────┘   └───────────┘
                                 │
                          ┌──────▼──────┐
                          │   Celery    │
                          │  (fanout)   │
                          └─────────────┘

              Media (avatars, photos) → AWS S3 (IAM Role, no static keys)
              HBase (dev) → alternative newsfeed/friendship storage, see below
```

All services run as Docker containers on a single EC2 instance, fronted by Nginx for TLS termination, static file serving, and reverse proxying. GitHub Actions deploys on every push to `main`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django + Django REST Framework |
| Async tasks | Celery + Redis (broker) |
| Caching | Memcached + Redis |
| Database | MySQL |
| Wide-column store | HBase + custom Django-style ORM |
| Storage | AWS S3 (IAM Role) |
| Web server | Gunicorn behind Nginx |
| Deployment | Docker Compose on EC2 |
| CI/CD | GitHub Actions |

---

## Key Engineering Decisions

**1. Newsfeed fanout via Celery, not synchronous writes.** When a user posts a tweet, fanning the tweet out to every follower's timeline at write time would block the request on however many followers that user has. Instead, the tweet write returns immediately and a Celery task (`fanout_newsfeeds_main_task` → batched `fanout_newsfeeds_batch_task`) pushes the tweet into followers' newsfeeds asynchronously, queued through Redis.

**2. Two-tier caching.** Memcached handles single-object reads (user profiles, tweets) and rate-limit counters — flat TTL, no structure needed, fast. Redis is used where structure matters — the newsfeed and per-user tweet lists (`RedisHelper` keeps them as length-capped, time-ordered Redis lists), likes/comments counters, and the Celery broker — because it supports atomic increments and list/queue operations that Memcached doesn't.

**3. Same-origin deployment over CORS.** Frontend and backend are served from the same Nginx instance under `chirp-app.dev`, avoiding cross-origin cookie and CSRF complications entirely. This was a deliberate trade-off: the existing frontend used a dev-server proxy (not `django-cors-headers`), so same-origin was the path of least friction, and it produces a tighter, more defensible Nginx configuration to discuss.

**4. Rate limiting and abuse guards.** Read endpoints are throttled per user-or-IP and writes carry per-second / per-minute / per-day caps (`django-ratelimit`). Since the live demo is open to anyone, tweet uploads are size-capped at the Nginx layer and an S3 lifecycle rule auto-expires demo media.

---

## HBase: a Django-style ORM for a wide-column store

[`django_hbase/`](django_hbase/) gives HBase Django-like ergonomics (`Meta.row_key`, typed fields, `.create()` / `.get()` / `.filter()`) on top of a store with no SQL, no secondary index, and no ORM — just one sorted **row key**. Every design choice below follows from that single constraint.

```python
class HBaseNewsFeed(models.HBaseModel):
    user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()
    tweet_id = models.IntegerField(column_family='cf')

    class Meta:
        row_key = ('user_id', 'created_at')
```

**1. Shaping the row key — even distribution *and* queryability (`newsfeeds`).**
Take the `newsfeeds` table above. HBase spreads rows across machines by row-key order, so a monotonic key (id, timestamp) sends every new write to one region — a hotspot. `reverse` flips the leading field's digits to scatter sequential IDs evenly; padding to a fixed 16-digit width keeps lexicographic order numeric (`"2" < "10"`) and `reverse` lossless. The composite `(user_id, created_at)` then serves the only two patterns the feed needs — exact match and exact-prefix + time range — so `.filter(prefix=(user_id,), limit=20, reverse=True)` is effectively `WHERE user_id = X ORDER BY created_at DESC LIMIT 20`.

**2. No secondary index → one table per access pattern (`friendships`).**
MySQL answers "who A follows" and "who follows A" from one table with two composite indexes. HBase has none, so friendship is two mirrored tables — `HBaseFollowing (from_user_id, created_at)` and `HBaseFollower (to_user_id, created_at)`. The cost: a follow writes both with no transaction (drift reconciled by a periodic job), and "is A following B?" — answerable by neither — is served from a Redis set (`SISMEMBER`, O(1)).

**3. Swappable with MySQL via GateKeeper.**
A [`GateKeeper`](gatekeeper/) percentage flag flips the backend gradually (0% MySQL → 100% HBase). Serializers are decoupled from the ORM (plain `Serializer` with manual `create()` / `update()`) so one API serves either store; since HBase bypasses Django signals, cache invalidation is triggered explicitly at each write.

**Why these two fit HBase:** `newsfeeds` and `friendships` are high-volume and write-heavy (one tweet → many fanout writes), with a dead-simple schema and only append + range-scan-by-time access — exactly where HBase wins and MySQL's joins/indexes pay off least. Production runs MySQL; HBase is the dev-environment alternative, switchable via GateKeeper.

---

## Local Development

This project supports two local environments, switched via `local_settings.py`:

```bash
# Vagrant (full stack including HBase)
vagrant up && vagrant ssh
python manage.py runserver 0.0.0.0:8000

# Docker (matches production topology)
make build
make up

# API available at `http://localhost:8000`
```

---

## Production Deployment

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Differences from the development compose file:

| | Development | Production |
|---|---|---|
| App server | `runserver` (single-threaded) | Gunicorn, 2 workers |
| Code delivery | Volume-mounted, hot-reloads | Baked into the image at build time |
| Static files | Served by Django | `collectstatic` → Nginx serves directly |
| Media storage | Local filesystem | S3 (`S3Boto3Storage`) |
| `DEBUG` | `True` | `False` |

**Deploy flow** — every push to `main` runs [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml):

1. **CI/CD**: SSH into EC2 → `git pull` → `docker compose -f docker-compose.prod.yml up -d --build`

Then the `chirp` container's startup command (in `docker-compose.prod.yml`) runs:

2. `migrate`
3. `collectstatic`
4. start Gunicorn

---

## API Overview

| Endpoint | Description |
|---|---|
| `/api/accounts/` | Signup, login, logout, login status |
| `/api/users/` | List users, retrieve by id |
| `/api/profiles/` | Update avatar and bio |
| `/api/tweets/` | Create tweet (with images), list by user, retrieve single |
| `/api/newsfeeds/` | Personalized timeline via Celery fanout (cursor-paginated) |
| `/api/comments/` | Create / update / delete / list by tweet |
| `/api/likes/` | Like or cancel like on tweets and comments |
| `/api/friendships/` | Follow / unfollow, followers / followings list |
| `/api/notifications/` | Unread count, mark-as-read, list |
| `/admin/` | Django admin |

Full endpoint list: [`docs/api.md`](docs/api.md)

---

## Testing

```bash
make test
# or, inside the container:
python manage.py test
```

Test suite covers model logic, API endpoints, and Celery task behavior across all apps (`accounts`, `tweets`, `comments`, `likes`, `friendships`, `newsfeeds`, `gatekeeper`).
