# Chirp API — Endpoint Reference

**Base URL:** `https://chirp-app.dev/api/`

---

## 1. Accounts & Users

| # | Description | Method | Endpoint | Request Body |
|---|---|---|---|---|
| 1-1 | List all users | GET | `/api/users/` | — |
| 1-2 | Retrieve user by id | GET | `/api/users/{user_id}/` | — |
| 1-3 | Login | POST | `/api/accounts/login/` | `{ username, password }` |
| 1-4 | Logout | POST | `/api/accounts/logout/` | — |
| 1-5 | Signup | POST | `/api/accounts/signup/` | `{ username, password, email }` |
| 1-6 | Check login status | GET | `/api/accounts/login_status/` | — |
| 1-7 | Update profile | PUT | `/api/profiles/{user_id}/` | `{ nickname, avatar }` |

---

## 2. Comments

| # | Description | Method | Endpoint | Request Body |
|---|---|---|---|---|
| 2-1 | Create comment | POST | `/api/comments/` | `{ tweet_id, content }` |
| 2-2 | Update comment | PUT | `/api/comments/{comment_id}/` | `{ content }` |
| 2-3 | Delete comment | DELETE | `/api/comments/{comment_id}/` | — |
| 2-4 | List comments for a tweet | GET | `/api/comments/?tweet_id={tweet_id}` | — |

---

## 3. Notifications

| # | Description | Method | Endpoint | Request Body |
|---|---|---|---|---|
| 3-1 | List notifications (read + unread) | GET | `/api/notifications/` | — |
| 3-1b | List unread notifications only | GET | `/api/notifications/?unread=True` | — |
| 3-2 | Unread notification count | GET | `/api/notifications/unread-count/` | — |
| 3-3 | Mark all notifications as read | POST | `/api/notifications/mark-all-as-read/` | — |
| 3-4 | Update a notification (read / unread) | PUT | `/api/notifications/{notification_id}/` | `{ unread }` |

---

## 4. Likes

| # | Description | Method | Endpoint | Request Body |
|---|---|---|---|---|
| 4-1 | Like a tweet or comment | POST | `/api/likes/` | `{ content_type, object_id }` |
| 4-2 | Cancel a like | POST | `/api/likes/cancel/` | `{ content_type, object_id }` |

---

## 5. Friendships

| #   | Description | Method | Endpoint | Request Body |
|-----|---|---|---|---|
| 5-1 | Follow a user | POST | `/api/friendships/{user_id}/follow/` | — |
| 5-2 | Unfollow a user | POST | `/api/friendships/{user_id}/unfollow/` | — |
| 5-3 | List followers of a user | GET | `/api/friendships/{user_id}/followers/` | — |
| 5-4 | List followings of a user | GET | `/api/friendships/{user_id}/followings/` | — |

---

## 6. Tweets & Newsfeed

| #   | Description | Method | Endpoint | Request Body |
|-----|---|---|---|---|
| 6-1 | List tweets by user (paginated) | GET | `/api/tweets/?user_id={user_id}` | — |
| 6-2 | Personalized newsfeed (paginated) | GET | `/api/newsfeeds/` | — |
| 6-3 | Retrieve single tweet | GET | `/api/tweets/{tweet_id}/` | — |
| 6-4 | Create tweet (with images) | POST | `/api/tweets/` | `{ content, files: [] }` (multipart) |

**Infinite scroll pagination** (cursor-based on `created_at`):

| Action | Endpoint |
|---|---|
| First page | `/api/newsfeeds/` |
| Pull-to-refresh (newer) | `/api/newsfeeds/?created_at__gt={created_at}` |
| Load more (older) | `/api/newsfeeds/?created_at__lt={created_at}` |

**Same pattern applies to `/api/tweets/?user_id={user_id}`, `/api/friendships/{user_id}/followers/`, `/api/friendships/{user_id}/followings/`**  
`created_at` is the timestamp of the last item in the current list — used as a cursor to fetch the next page without offset pagination.

---