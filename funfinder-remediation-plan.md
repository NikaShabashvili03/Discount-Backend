# funfinder.ge — Security Remediation Plan

**Prepared:** 2026-05-13
**For:** development team
**Scope:** Production hardening of funfinder.ge (React SPA) + base.funfinder.ge (Django API) + admin.funfinder.ge (React admin SPA), all on DigitalOcean droplet `143.198.154.20`

---

## Executive Summary

Adversarial audit identified **17 CRITICAL + 12 HIGH** findings + ~100 secondary vectors. **Root cause: production deployment shipped without security checklist.** No source-code changes required for the majority of fixes — most are configuration (settings.py, nginx, DNS, Google Cloud Console).

**Total effort:** ~4 dev-days (1.5 backend + 1 frontend + 1.5 devops). Can be done in **1 long day** by one full-stack senior or split across the team.

**Order of operations is critical** — fix #1 alone closes ~6 attack paths. Ship Phase 1 in one deploy.

---

## Phase 1 — CRITICAL (ship within 24h)

### Backend (Django) — `base.funfinder.ge`

#### 1.1 — `DEBUG = False`
**File:** `core/settings.py` (or `settings/production.py` if split)
**Severity:** 🔴 CRITICAL
**Time:** 30 seconds + redeploy

```python
# BEFORE
DEBUG = True

# AFTER
DEBUG = False
ALLOWED_HOSTS = ['base.funfinder.ge', 'admin.funfinder.ge']  # adjust per actual hostnames
```

**Why:** Currently every uncaught exception leaks stack trace + environment variables + DB credentials + `SECRET_KEY` to anonymous attackers. Also leaks root URLconf on every 404.

**Verify:**
```bash
curl https://base.funfinder.ge/zzz404probe
# expected: minimal 404 page. MUST NOT contain "DEBUG = True" or "Using the URLconf defined in"
```

---

#### 1.2 — Remove `/test/sendgrid` endpoint
**File:** `core/urls.py` or feature-specific `urls.py`
**Severity:** 🔴 CRITICAL
**Time:** 5 minutes

**Action:** Delete the route entry, delete the view function, delete the import. If kept for dev use, gate it:

```python
# Either delete the line entirely, OR:
from django.conf import settings
if settings.DEBUG:
    urlpatterns += [path('test/sendgrid', test_sendgrid_view)]
```

**Why:** Endpoint currently returns 200 to anonymous GET and sends real email via SendGrid (`from: funfinder.georgia@gmail.com`, captured `to: shabashvilinika07@gmail.com`). Used by attackers for: (a) quota drain, (b) PII harvest, (c) phishing from your legitimate sender domain.

**Verify:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://base.funfinder.ge/test/sendgrid
# expected: 404 (or 403 if gated)
```

---

#### 1.3 — Fix CORS reflection
**File:** `core/settings.py`
**Severity:** 🔴 CRITICAL
**Time:** 10 minutes

```python
# BEFORE (likely current state — reflects arbitrary Origin):
# CORS_ALLOW_ALL_ORIGINS = True
# or custom middleware that echoes request.META['HTTP_ORIGIN']

# AFTER:
CORS_ALLOWED_ORIGINS = [
    'https://funfinder.ge',
    'https://admin.funfinder.ge',
]
CORS_ALLOW_CREDENTIALS = True  # only if you actually need cookies/JWT in cross-origin requests
CORS_ALLOW_ALL_ORIGINS = False  # explicit
# REMOVE any custom CORS middleware that echoes Origin
```

If using `django-cors-headers` package, the above is enough. If a custom middleware echoes `Origin` back, **delete it entirely**.

**Why:** Currently `Origin: https://evil.example.com` is reflected back as `Access-Control-Allow-Origin: https://evil.example.com` with `Allow-Credentials: true`. Any malicious site can ride a logged-in user's session cookie/JWT and call your full API including payment endpoints.

**Verify:**
```bash
curl -s -X OPTIONS https://base.funfinder.ge/api/v5/order/feed \
  -H "Origin: https://evil.example.com" \
  -H "Access-Control-Request-Method: GET" \
  -I | grep -i "access-control"
# expected: NO line matching "evil.example.com". Either header absent or only "https://funfinder.ge"
```

---

#### 1.4 — Verify BOG webhook signature
**File:** view handling `/api/v5/payment/bog/notify` (and `/callback`)
**Severity:** 🔴 CRITICAL
**Time:** 30 minutes

**Action:** Ensure HMAC signature is verified on every BOG callback:

```python
import hmac
import hashlib
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

def bog_notify(request):
    received_signature = request.headers.get('X-BOG-Signature', '')
    body = request.body  # raw bytes, BEFORE json parsing
    expected_signature = hmac.new(
        settings.BOG_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(received_signature, expected_signature):
        return Response({'error': 'invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
    # ... process the notification
```

Adjust algorithm and header name to match BOG's actual documentation (HMAC-SHA256 with `Public-Key` or `Authorization: Bearer` is also common).

**Why:** Without signature verification, an attacker can POST a forged "paid" notification to your webhook for any order, marking unpaid orders as paid and getting free tickets. If they can also intercept the real callback by changing the URL in admin (#16 finding), they can route real payments away.

**Verify:**
```bash
# Send bogus payload — must reject
curl -s -X POST https://base.funfinder.ge/api/v5/payment/bog/notify \
  -H "Content-Type: application/json" \
  -d '{"order_id":"test","status":"paid"}'
# expected: 401 or 403, NOT 200
```

---

#### 1.5 — Tighten `^uploads/(?P<path>.*)$` regex
**File:** `core/urls.py` or static-files config
**Severity:** 🔴 CRITICAL
**Time:** 15 minutes

The current regex `(?P<path>.*)$` accepts any string including `../../etc/passwd`. Replace with whitelist:

```python
# BEFORE
re_path(r'^uploads/(?P<path>.*)$', serve_upload)

# AFTER — restrict to known subdirs and known extensions only
re_path(
    r'^uploads/(?P<subdir>service_images|slider_images|category_images|profile_pictures)/(?P<filename>[\w\-]+\.(?:jpg|jpeg|png|webp|gif))$',
    serve_upload
)
```

Also in the view, harden file resolution:
```python
import os
from django.http import Http404, FileResponse

def serve_upload(request, subdir, filename):
    base = os.path.realpath(settings.UPLOADS_ROOT)
    target = os.path.realpath(os.path.join(base, subdir, filename))
    if not target.startswith(base + os.sep):
        raise Http404
    if not os.path.isfile(target):
        raise Http404
    return FileResponse(open(target, 'rb'))
```

**Why:** The current `.*$` lets attackers request `/uploads/../../../../etc/passwd` or any path on disk. nginx + Django combined make this exploitable depending on `X-Accel-Redirect` setup.

**Verify:**
```bash
# These must all 404
curl -s -o /dev/null -w "%{http_code}\n" "https://base.funfinder.ge/uploads/../etc/passwd"
curl -s -o /dev/null -w "%{http_code}\n" "https://base.funfinder.ge/uploads/%2e%2e/etc/passwd"
curl -s -o /dev/null -w "%{http_code}\n" "https://base.funfinder.ge/uploads/random_dir/x.exe"
```

Also enforce server-side upload validation:
```python
# In upload view:
ALLOWED_MIME = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
MAX_SIZE = 5 * 1024 * 1024  # 5MB

def upload_view(request):
    f = request.FILES['file']
    if f.size > MAX_SIZE:
        return JsonResponse({'error': 'file too large'}, status=413)
    if f.content_type not in ALLOWED_MIME:
        return JsonResponse({'error': 'invalid type'}, status=400)
    # Use python-magic to verify ACTUAL content matches claimed MIME:
    import magic
    mime = magic.from_buffer(f.read(2048), mime=True)
    f.seek(0)
    if mime not in ALLOWED_MIME:
        return JsonResponse({'error': 'mime mismatch'}, status=400)
    # ...save
```

This closes SVG XSS (no SVG in allowlist), polyglot files (magic-byte mismatch), image bombs (size limit), and DoS (size limit).

---

#### 1.6 — Auth-gate Django admin + API docs
**File:** `core/urls.py`, `core/settings.py`, nginx config
**Severity:** 🔴 CRITICAL
**Time:** 20 minutes

**Step A — nginx IP-allowlist on `/admin/` and `/docs/`:**

```nginx
# /etc/nginx/sites-available/base.funfinder.ge.conf
location /admin/ {
    allow YOUR_OFFICE_IP;       # replace with real IPs
    allow YOUR_VPN_IP;
    allow 127.0.0.1;
    deny all;
    proxy_pass http://localhost:8000;
    # ... rest of proxy headers
}

location ~ ^/docs/(admin|customer|staff) {
    allow YOUR_OFFICE_IP;
    allow YOUR_VPN_IP;
    deny all;
    proxy_pass http://localhost:8000;
}
```

**Step B — additional Django admin URL randomization:**

```python
# core/urls.py
urlpatterns = [
    path('admin-x9k2-prod/', admin.site.urls),  # not /admin/
    # ...
]
```

**Why:** Currently `/admin/login/` is reachable from any IP. `/docs/admin`, `/docs/customer`, `/docs/staff` are 22KB+ of API documentation publicly readable.

**Verify after deploy:**
```bash
# From an unallowed IP / public WiFi:
curl -s -o /dev/null -w "%{http_code}\n" https://base.funfinder.ge/admin/
# expected: 403 (nginx deny) or 404
curl -s -o /dev/null -w "%{http_code}\n" https://base.funfinder.ge/docs/admin
# expected: 403 or 404
```

---

#### 1.7 — Add per-object permission checks (close IDOR)
**File:** `views.py` for order/event/booking endpoints
**Severity:** 🔴 CRITICAL (assumed — needs verification)
**Time:** 1-2 hours

Check every endpoint that returns user-owned data. Replace `permission_classes = [IsAuthenticated]` with explicit ownership check:

```python
# permissions.py
from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id

# views.py
class OrderDetailView(RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    # IMPORTANT: must use get_object() which triggers has_object_permission
    # If using a custom .retrieve(), explicitly call self.check_object_permissions(request, obj)
```

**Why:** Default `IsAuthenticated` lets ANY logged-in user fetch ANY order/booking by ID. Sequential IDs make enumeration trivial.

**Verify (manual, requires 2 test accounts):**
```bash
# Account A creates order 100. Account B logs in and tries:
curl -H "Authorization: Bearer $TOKEN_B" https://base.funfinder.ge/api/v5/order/details/100
# expected: 403 or 404, NOT 200 with A's data
```

---

#### 1.8 — Install rate limiting
**File:** `requirements.txt`, `settings.py`, auth views
**Severity:** 🔴 CRITICAL
**Time:** 30 minutes

```bash
pip install django-ratelimit
```

```python
# views.py
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def login_view(request):
    # ...

@ratelimit(key='ip', rate='3/h', method='POST', block=True)
def password_reset_view(request):
    # ...

@ratelimit(key='ip', rate='10/m', method='POST', block=True)
def signup_view(request):
    # ...
```

Also expose `RateLimit-*` headers so honest clients can backoff:
```python
def add_ratelimit_headers(response, request):
    # use django-ratelimit's internal counters
    response['RateLimit-Limit'] = '5'
    response['RateLimit-Remaining'] = str(...)
    return response
```

**Why:** Currently auth surface has zero rate-limit signals. Credential stuffing has no backpressure. Combined with #1.5 IDOR potential, attacker can enumerate user accounts and brute-force passwords at full network speed.

**Verify:**
```bash
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code} " -X POST https://base.funfinder.ge/api/auth/login/ \
    -d 'email=test@test.com&password=wrong'
done
# expected: first 5 return 401, then 429 for the rest
```

---

#### 1.9 — Django session/CSRF cookie security
**File:** `core/settings.py`
**Severity:** 🟡 HIGH
**Time:** 5 minutes

```python
# Add these:
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # Django needs JS access on this; HttpOnly breaks SPA flow
CSRF_COOKIE_SAMESITE = 'Strict'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True  # if behind nginx, may need SECURE_PROXY_SSL_HEADER
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

**Verify:**
```bash
curl -sI https://base.funfinder.ge/ | grep -iE "strict-transport|x-frame|x-content"
# expected: HSTS + X-Frame-Options DENY + X-Content-Type-Options nosniff
```

---

### Frontend (React) — `funfinder.ge` and `admin.funfinder.ge`

#### 1.10 — Disable source maps in production
**File:** `package.json` (both main and admin React projects)
**Severity:** 🔴 CRITICAL
**Time:** 10 minutes per project

```json
// package.json
{
  "scripts": {
    "build": "GENERATE_SOURCEMAP=false react-scripts build"
  }
}
```

On Windows dev machines:
```json
"build": "cross-env GENERATE_SOURCEMAP=false react-scripts build"
```

After build, **verify the build/static/js/ folder has no `*.map` files**. If `.map` files are still produced (some CRA forks ignore the flag), delete them before deploy:

```bash
# In CI/CD or deploy script:
find build/static -name "*.map" -delete
```

Also add nginx 404 for any leaked `.map`:

```nginx
location ~* \.map$ {
    return 404;
}
```

**Why:** Currently `/static/js/main.718bc69b.js.map` (7.1MB) and admin `main.fdd48e23.js.map` (5.5MB) are publicly readable. Full un-minified source = competitor copies your business logic in 30 seconds, and attackers find XSS sinks 10× faster.

**Verify:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://funfinder.ge/static/js/main.718bc69b.js.map
curl -s -o /dev/null -w "%{http_code}\n" https://admin.funfinder.ge/static/js/main.fdd48e23.js.map
# both expected: 404
```

---

#### 1.11 — Migrate auth token from localStorage to HttpOnly cookie
**File:** Frontend auth flow + backend auth endpoint
**Severity:** 🟡 HIGH (defer to Phase 2 if time-pressed)
**Time:** 4-6 hours (requires coordinated frontend + backend change)

**Why:** Bundle shows `localStorage.setItem('token', ...)`. Any XSS = instant token theft. HttpOnly cookie is JS-inaccessible.

**Approach:**
- Backend: on login, set `Set-Cookie: token=...; HttpOnly; Secure; SameSite=Strict; Path=/`
- Frontend: remove `localStorage.setItem('token', ...)`. Remove `Authorization: Bearer ...` header — cookie is sent automatically with `credentials: 'include'` (which now requires #1.3 CORS whitelist).
- Backend: read token from `request.COOKIES.get('token')` instead of `Authorization` header (or support both during transition).

If full migration is too costly now, **mitigate** in Phase 1 by adding CSP (#1.13) which dramatically reduces XSS impact even with localStorage.

---

#### 1.12 — Remove keyword-stuffing meta tag
**File:** `public/index.html` (main SPA)
**Severity:** 🟡 HIGH (SEO)
**Time:** 5 minutes

Currently `<meta name="keywords" content="..."` is ~6KB of repeated keywords. Google's spam classifier penalizes this. **Delete the entire `<meta name="keywords">` tag** (Google has not used `meta keywords` for ranking since 2009; only the spam signal remains).

Rebuild meta head:
```html
<meta name="description" content="Funfinder — Georgia's adventure & event booking platform. Find rafting, paragliding, yacht tours, and more across Tbilisi, Batumi, Kazbegi, and beyond." />
<meta property="og:title" content="Funfinder — Adventures in Georgia" />
<meta property="og:description" content="..." />
<meta property="og:image" content="https://funfinder.ge/og-image.jpg" />
<meta property="og:url" content="https://funfinder.ge/" />
<meta property="og:type" content="website" />
<meta name="twitter:card" content="summary_large_image" />
```

---

### DevOps — nginx, DNS, Cloud Console

#### 1.13 — nginx security headers (frontend + admin)
**File:** `/etc/nginx/sites-available/funfinder.ge.conf` and `admin.funfinder.ge.conf`
**Severity:** 🔴 CRITICAL
**Time:** 30 minutes

```nginx
server {
    listen 443 ssl http2;
    server_name funfinder.ge;

    # === Security headers ===
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(self), camera=(), microphone=(), payment=(self)" always;
    add_header Cross-Origin-Opener-Policy "same-origin" always;

    # CSP — adjust script-src per actual third-party scripts in use
    add_header Content-Security-Policy "default-src 'self'; \
        script-src 'self' 'unsafe-inline' \
            https://www.googletagmanager.com \
            https://www.google-analytics.com \
            https://connect.facebook.net \
            https://maps.googleapis.com \
            https://maps.gstatic.com \
            https://pay.google.com \
            https://www.googleadservices.com \
            https://counter.top.ge; \
        style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; \
        font-src 'self' https://fonts.gstatic.com; \
        img-src 'self' data: blob: https:; \
        connect-src 'self' \
            https://base.funfinder.ge \
            https://maps.googleapis.com \
            https://www.google-analytics.com \
            https://www.facebook.com; \
        frame-src https://pay.google.com https://*.bog.ge; \
        frame-ancestors 'none'; \
        form-action 'self' https://*.bog.ge; \
        upgrade-insecure-requests;" always;

    # === Compression ===
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 256;
    gzip_types
        application/atom+xml
        application/javascript
        application/json
        application/ld+json
        application/manifest+json
        application/rss+xml
        application/vnd.api+json
        application/xml
        application/wasm
        font/eot
        font/otf
        font/ttf
        image/svg+xml
        text/css
        text/javascript
        text/plain
        text/xml;

    # brotli — requires nginx-extras or ngx_brotli module
    brotli on;
    brotli_comp_level 6;
    brotli_static on;
    brotli_types
        application/javascript
        application/json
        application/wasm
        application/xml
        font/eot
        font/otf
        font/ttf
        image/svg+xml
        text/css
        text/javascript
        text/plain;

    # === Cache hashed assets aggressively ===
    location ~* ^/static/(js|css|media)/.+\.[0-9a-f]{8,}\.(js|css|woff2?|ttf|otf|eot|png|jpg|jpeg|webp|svg|gif|ico)$ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        # Security headers must be repeated here because add_header doesn't inherit
        add_header X-Content-Type-Options "nosniff" always;
        access_log off;
    }

    # === HTML never cached ===
    location = / {
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        add_header Pragma "no-cache" always;
        try_files $uri /index.html =404;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }

    # === Block sourcemaps ===
    location ~* \.map$ {
        return 404;
    }

    # === Block hidden files / common scanner targets ===
    location ~ /\.(?!well-known) {
        deny all;
    }
    location ~* \.(env|git|sql|sqlite|bak|swp|log)$ {
        deny all;
    }

    # === Slowloris hardening ===
    client_body_timeout 10s;
    client_header_timeout 10s;
    send_timeout 10s;
    keepalive_timeout 30s 30s;
    client_max_body_size 10M;
    large_client_header_buffers 2 1k;

    # === Hide nginx version (already done — verify) ===
    server_tokens off;

    # SSL
    ssl_certificate /etc/letsencrypt/live/funfinder.ge/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/funfinder.ge/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;
    ssl_stapling on;
    ssl_stapling_verify on;
}

# Redirect HTTP -> HTTPS
server {
    listen 80;
    server_name funfinder.ge admin.funfinder.ge base.funfinder.ge;
    return 301 https://$host$request_uri;
}
```

Apply same hardening (with admin-specific CSP) to `admin.funfinder.ge.conf` and `base.funfinder.ge.conf` (backend gets a stricter CSP because no third-party scripts).

**Test config and reload:**
```bash
sudo nginx -t && sudo systemctl reload nginx
```

**Verify:**
```bash
curl -sI https://funfinder.ge/ | sort
# expected headers: Strict-Transport-Security, X-Frame-Options DENY, X-Content-Type-Options nosniff,
# Referrer-Policy, Content-Security-Policy, Permissions-Policy
curl -sI -H "Accept-Encoding: gzip, br" https://funfinder.ge/static/js/main.718bc69b.js | grep -i content-encoding
# expected: Content-Encoding: br or gzip
```

---

#### 1.14 — Add SPF and DMARC DNS records
**Service:** DigitalOcean DNS (or wherever DNS is hosted)
**Severity:** 🔴 CRITICAL
**Time:** 15 minutes (DNS propagation 1-24h)

Currently funfinder.ge has only a Google site-verification TXT. **Without SPF, anyone can send email from `@funfinder.ge` to your customers and it won't be marked as spam.**

**Add these TXT records:**

| Name | Type | Value |
|------|------|-------|
| `funfinder.ge` | TXT | `v=spf1 include:_spf.google.com include:sendgrid.net -all` |
| `_dmarc.funfinder.ge` | TXT | `v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@funfinder.ge; ruf=mailto:dmarc-reports@funfinder.ge; fo=1; adkim=s; aspf=s; pct=100` |

Adjust the SPF `include:` chain to match actually-used senders (Google Workspace, SendGrid, Mailgun, AWS SES, etc.). Start with DMARC `p=quarantine` for 2 weeks, monitor reports, then move to `p=reject`.

**DKIM** — needs SendGrid + Google Workspace setup:
- SendGrid: Settings → Sender Authentication → Domain Authentication → adds 3 CNAME records
- Google Workspace: Admin Console → Apps → Google Workspace → Gmail → Authenticate email → DKIM → generate + add TXT record

**Verify:**
```bash
nslookup -type=TXT funfinder.ge
nslookup -type=TXT _dmarc.funfinder.ge
# expected: SPF and DMARC records present
# Or via DoH:
curl -s "https://dns.google/resolve?name=funfinder.ge&type=TXT" | grep -o '"data":"v=spf1[^"]*"'
curl -s "https://dns.google/resolve?name=_dmarc.funfinder.ge&type=TXT" | grep -o '"data":"v=DMARC1[^"]*"'
```

Use https://www.mail-tester.com to verify deliverability after changes.

---

#### 1.15 — Restrict Google Maps API key
**Service:** Google Cloud Console
**Severity:** 🔴 CRITICAL
**Time:** 2 minutes

1. Open https://console.cloud.google.com/apis/credentials
2. Find the API key `AIzaSyDKQvLYHEywVvYX913V223qVoHTqk_2tJA`
3. Click → "Edit API key"
4. Application restrictions → "HTTP referrers (web sites)"
5. Add referrers:
   - `https://funfinder.ge/*`
   - `https://www.funfinder.ge/*`
   - `https://admin.funfinder.ge/*`
6. API restrictions → "Restrict key" → enable only:
   - Maps JavaScript API
   - (and whichever Maps APIs you actually use)
7. Save

8. **Set billing alert:**
   - Billing → Budgets & alerts → Create budget
   - Threshold: $50 daily / $500 monthly (whatever fits your scale)
   - Alert email to owner

**Verify:**
```bash
# This should fail (different referer):
curl -s -H "Referer: https://evil.example.com/" "https://maps.googleapis.com/maps/api/js?key=AIzaSyDKQvLYHEywVvYX913V223qVoHTqk_2tJA" | head -1
# expected: error about referer not allowed, NOT actual JS content
```

---

#### 1.16 — Set up Cloudflare (free tier)
**Service:** Cloudflare
**Severity:** 🟡 HIGH (defense-in-depth, also enables many other fixes)
**Time:** 30 minutes

1. Register account at cloudflare.com (free)
2. Add `funfinder.ge` → Cloudflare scans existing DNS
3. Verify all records imported correctly (especially SPF/DMARC from #1.14, MX for Google Workspace, A records for subdomains)
4. Change nameservers at your registrar to Cloudflare's two NS
5. Wait for DNS propagation (1-24h)
6. Once active, enable:
   - **SSL/TLS** → "Full (strict)" mode
   - **SSL/TLS → Edge Certificates** → Always Use HTTPS ON
   - **SSL/TLS → Edge Certificates** → Automatic HTTPS Rewrites ON
   - **SSL/TLS → Edge Certificates** → Minimum TLS Version: 1.2
   - **Security → WAF** → enable Cloudflare Managed Rules (free tier)
   - **Security → Bots** → "Bot Fight Mode" ON
   - **Security → DDoS** → "DDoS Protection" already on by default
   - **Caching** → set page rules to NOT cache `/api/*` and `/admin/*`
   - **Rules → Transform Rules** → consider stripping `Server` header

7. Submit to HSTS preload list at https://hstspreload.org once HSTS is confirmed live for 1 week.

**Why:** Currently `143.198.154.20` is directly exposed. One L7 DDoS (paid botnet $50-200/day) takes the site down. Cloudflare absorbs DDoS at network edge, provides WAF, and hides origin IP.

**After Cloudflare DNS is active, restrict origin to Cloudflare IPs only:**
```bash
# On the DigitalOcean droplet:
sudo ufw allow from 173.245.48.0/20 to any port 443
sudo ufw allow from 103.21.244.0/22 to any port 443
# ... add all Cloudflare IP ranges from https://www.cloudflare.com/ips/
sudo ufw delete allow 443/tcp  # remove the generic rule
```

---

## Phase 2 — HIGH priority (within 1 week)

### Backend hardening

#### 2.1 — Audit `requirements.txt` for known CVEs
```bash
pip install pip-audit
pip-audit -r requirements.txt
# Update Django, djangorestframework, pillow, requests, urllib3 if any CVE found
```

#### 2.2 — Move secrets to environment variables (not in code)
Audit `settings.py` and all files for hardcoded credentials. Move to `.env` (gitignored) loaded via `python-decouple` or `os.environ`:
```python
from decouple import config
SECRET_KEY = config('SECRET_KEY')
DATABASES = {
    'default': {
        # ...
        'PASSWORD': config('DB_PASSWORD'),
    }
}
BOG_WEBHOOK_SECRET = config('BOG_WEBHOOK_SECRET')
SENDGRID_API_KEY = config('SENDGRID_API_KEY')
```

If `SECRET_KEY` is hardcoded in repo and ever committed, **rotate it** (generate new with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`).

#### 2.3 — DRF mass-assignment audit
For every `ModelSerializer`, explicitly list `fields` (whitelist) or use `read_only_fields` to lock down sensitive attributes:
```python
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = ['id', 'email', 'is_staff', 'is_superuser', 'date_joined']
```

Never use `fields = '__all__'` on user-controllable serializers.

#### 2.4 — Audit `raw()` / `extra()` / `cursor.execute()` for SQL injection
```bash
grep -rn -E "\.raw\(|\.extra\(|cursor\.execute\(" --include="*.py" .
```
Every match must use parameterized queries, NEVER string formatting.

#### 2.5 — Decommission old API versions (v1, v2)
Map which clients still use v1/v2. Set a deprecation date (e.g., 30 days), add `Sunset:` and `Deprecation:` HTTP response headers, then remove. Fewer endpoints = smaller attack surface.

#### 2.6 — Audit log for admin actions
```bash
pip install django-simple-history
# or django-auditlog
```
Add history tracking to critical models: `ServiceProvider` (IBAN), `User` (role/staff), `BOGConfig`, `WebhookConfig`. Surface a "recent admin actions" dashboard.

#### 2.7 — Add email confirmation for IBAN changes
On `/staff/company/update/` when IBAN field changes:
1. Save change as `pending`
2. Send confirmation email to owner (separate from staff)
3. Require click on email link OR 2nd staff approval before applying

---

### Frontend hardening

#### 2.8 — Code-split with React.lazy()
```jsx
// BEFORE
import AdminDashboard from './AdminDashboard';

// AFTER
const AdminDashboard = React.lazy(() => import('./AdminDashboard'));

// Wrap in Suspense
<Suspense fallback={<Spinner />}>
  <AdminDashboard />
</Suspense>
```
Apply to every top-level route. Should reduce main bundle from 1.55MB to ~400KB.

#### 2.9 — Self-host fonts
Replace Google Fonts CDN with self-hosted `font-display: swap` WOFF2 files. Removes 2 preconnect roundtrips + 1 third-party dependency.

#### 2.10 — Add `prerender` for SEO
```bash
npm install --save-dev react-snap
```
Add to `package.json`:
```json
{
  "scripts": {
    "postbuild": "react-snap"
  },
  "reactSnap": {
    "include": [
      "/", "/about", "/tickets", "/water-activities", "/parachute",
      "/yacht", "/rafting", "/sea-moto", "/land-activities",
      "/quad-tours", "/moto-tours", "/hiking", "/jeep-tours", "/bicycles"
    ]
  }
}
```

Each route now ships pre-rendered HTML for Googlebot.

#### 2.11 — Cookie consent banner
Install `react-cookie-consent` or use Klaro:
```bash
npm install react-cookie-consent
```
**Gate ALL trackers (GA, Meta Pixel, top.ge, Google Ads) behind user consent.** Update `public/index.html`:
- Remove unconditional `fbq("track","PageView")`
- Remove unconditional `gtag("event","conversion",...)`
- Replace with conditional initialization triggered after consent banner returns true.

#### 2.12 — Add OpenGraph + Twitter Card + schema.org
Install `react-helmet-async`:
```bash
npm install react-helmet-async
```
Per-route meta tags. For event pages, emit schema.org `Event` JSON-LD:
```jsx
<script type="application/ld+json">
{JSON.stringify({
  "@context": "https://schema.org",
  "@type": "TouristAttraction",
  "name": event.title,
  "description": event.description,
  "image": event.image,
  "address": { ... },
  "offers": {
    "@type": "Offer",
    "price": event.price,
    "priceCurrency": "GEL",
    "availability": "https://schema.org/InStock"
  }
})}
</script>
```

---

### DevOps hardening

#### 2.13 — nginx config: rate limiting at edge
```nginx
http {
    limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
}

server {
    location /api/auth/ {
        limit_req zone=auth burst=5 nodelay;
        # ...
    }
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        # ...
    }
}
```

#### 2.14 — fail2ban for repeated probes
```bash
sudo apt install fail2ban
```
Create `/etc/fail2ban/jail.d/nginx-funfinder.conf`:
```ini
[nginx-404]
enabled = true
filter = nginx-404
logpath = /var/log/nginx/access.log
maxretry = 30
findtime = 60
bantime = 3600
action = iptables-multiport[name=nginx, port="http,https"]
```

#### 2.15 — Automated backups
```bash
# /etc/cron.daily/backup-funfinder
#!/bin/bash
TIMESTAMP=$(date +%F)
pg_dump -U funfinder funfinder_db | gzip > /backups/db-$TIMESTAMP.sql.gz
# Sync to off-server location:
rsync /backups/db-$TIMESTAMP.sql.gz user@backup-server:/funfinder-backups/
# Or use DigitalOcean Spaces:
s3cmd put /backups/db-$TIMESTAMP.sql.gz s3://funfinder-backups/
# Retention: 30 days
find /backups -name "db-*.sql.gz" -mtime +30 -delete
```

Test restore quarterly.

#### 2.16 — Monitoring + alerting
Set up at least one of:
- **Uptime monitoring**: UptimeRobot, BetterUptime (free tier — alerts when site down)
- **Error tracking**: Sentry (free tier — backend exceptions + JS errors)
- **Server metrics**: DigitalOcean Monitoring (built-in, free) — CPU, RAM, disk alerts

Page the owner via SMS or Telegram for:
- 5xx error rate > 1%
- Disk usage > 80%
- Failed login rate > 50/min (credential stuffing in progress)
- Successful admin login from unusual IP

---

## Phase 3 — MEDIUM priority (within 2 weeks)

### Compliance & legal

#### 3.1 — GDPR Article 17 (Right to be Forgotten) endpoint
User-facing: `/profile/delete-account` button → soft-delete with 30-day window → hard delete after.
Backend: anonymize email/phone/name in `User`, `Order`, `BookingLog`; preserve aggregate analytics only.

#### 3.2 — Privacy policy + Terms of Service review
Make sure policy matches actual data flow:
- Disclose third-party trackers (GA, Meta Pixel, top.ge, Google Ads)
- Disclose data sharing with BOG, SendGrid, DigitalOcean
- Provide opt-out mechanism for marketing emails

#### 3.3 — Cookie consent records
For GDPR audit: store who consented when, what they consented to. The `react-cookie-consent` library doesn't do this — extend with server-side log.

#### 3.4 — PCI DSS scope determination
Verify the BOG iPay checkout flow:
- **Pure redirect** (customer enters card on BOG.ge): you are out of PCI DSS scope. Good.
- **Iframe/popup with card form on funfinder.ge**: you're in PCI scope. Need at minimum SAQ A-EP self-assessment.

Confirm with BOG account manager and document in `/security/PCI-scope.md`.

---

### Defense-in-depth

#### 3.5 — Web Application Firewall rules (Cloudflare or nginx)
Beyond Cloudflare's default WAF, add custom rules:
- Block requests with `..` in path
- Block requests with `<script` in query string
- Block known scanner User-Agents (nuclei, sqlmap, nikto)
- Block Tor exit nodes if no legitimate Tor traffic expected

#### 3.6 — Subdomain monitoring
Set up monitoring for dangling DNS:
```bash
# Weekly cron
for sub in admin api base www staging dev test; do
  echo "$sub.funfinder.ge -> $(dig +short ${sub}.funfinder.ge)"
done | mail -s "Subdomain inventory" owner@funfinder.ge
```

#### 3.7 — Bug bounty / responsible disclosure
Create `/.well-known/security.txt`:
```
Contact: mailto:security@funfinder.ge
Expires: 2027-12-31T23:59:59.000Z
Acknowledgments: https://funfinder.ge/security/hall-of-fame
Preferred-Languages: ka, en
Canonical: https://funfinder.ge/.well-known/security.txt
```

#### 3.8 — Penetration test (after Phase 1+2 complete)
Schedule annual pentest with a Georgian security firm or via Bugcrowd/HackerOne. Budget: $2-5K/year.

---

## Phase 4 — Post-deploy verification

After each phase deploy, run this complete probe set. **Save output, compare to baseline.**

```bash
#!/bin/bash
# verify-funfinder.sh

echo "=== HTTP -> HTTPS redirect ==="
curl -sI http://funfinder.ge/ | head -3

echo "=== Security headers (frontend) ==="
curl -sI https://funfinder.ge/ | grep -iE "strict-transport|x-frame|x-content|referrer|permissions|content-security"

echo "=== Security headers (backend) ==="
curl -sI https://base.funfinder.ge/ | grep -iE "strict-transport|x-frame|x-content|referrer"

echo "=== DEBUG=False ==="
curl -s https://base.funfinder.ge/zzz404probe | grep -i "DEBUG = True" && echo "FAIL: DEBUG still True" || echo "PASS"

echo "=== /test/sendgrid removed ==="
curl -s -o /dev/null -w "Code: %{http_code}\n" https://base.funfinder.ge/test/sendgrid

echo "=== CORS not reflecting evil origin ==="
curl -sI -X OPTIONS https://base.funfinder.ge/api/v5/order/feed \
  -H "Origin: https://evil.example.com" \
  -H "Access-Control-Request-Method: GET" | grep -i "access-control-allow-origin"

echo "=== Sourcemap blocked ==="
curl -s -o /dev/null -w "main.js.map: %{http_code}\n" https://funfinder.ge/static/js/main.718bc69b.js.map
curl -s -o /dev/null -w "admin main.js.map: %{http_code}\n" https://admin.funfinder.ge/static/js/main.fdd48e23.js.map

echo "=== Compression active ==="
curl -sI -H "Accept-Encoding: gzip, br" https://funfinder.ge/static/js/main.718bc69b.js | grep -i content-encoding

echo "=== Cache-Control on hashed asset ==="
curl -sI https://funfinder.ge/static/js/main.718bc69b.js | grep -i cache-control

echo "=== SPF record present ==="
curl -s "https://dns.google/resolve?name=funfinder.ge&type=TXT" | grep -o '"data":"v=spf1[^"]*"'

echo "=== DMARC record present ==="
curl -s "https://dns.google/resolve?name=_dmarc.funfinder.ge&type=TXT" | grep -o '"data":"v=DMARC1[^"]*"'

echo "=== Admin reachable from public? ==="
curl -s -o /dev/null -w "/admin/: %{http_code}\n" https://base.funfinder.ge/admin/

echo "=== API docs blocked? ==="
curl -s -o /dev/null -w "/docs/admin: %{http_code}\n" https://base.funfinder.ge/docs/admin
curl -s -o /dev/null -w "/docs/staff: %{http_code}\n" https://base.funfinder.ge/docs/staff

echo "=== Maps key restricted? ==="
curl -s -H "Referer: https://evil.example.com/" "https://maps.googleapis.com/maps/api/js?key=AIzaSyDKQvLYHEywVvYX913V223qVoHTqk_2tJA" | head -1
```

**Expected outputs after Phase 1 complete:**
- HTTP→HTTPS: 301
- Security headers: HSTS + X-Frame-Options DENY + nosniff + CSP all present
- DEBUG check: "PASS"
- /test/sendgrid: 404
- CORS evil origin: NOT reflected
- Both sourcemaps: 404
- Content-Encoding: `br` or `gzip`
- Cache-Control: `public, max-age=31536000, immutable`
- SPF: present
- DMARC: present
- /admin/: 403 (denied for non-allowed IP)
- /docs/*: 403
- Maps key: error response, not JS

---

## Phase 5 — Code review items (require source access)

These need a developer with source code in front of them. **I could not verify externally.** Each is a HIGH or CRITICAL risk if confirmed vulnerable:

### Backend (Django/DRF)
- [ ] JWT signing: confirm `algorithm='HS256'` (not `none`); secret length >= 32 chars
- [ ] OAuth: confirm `redirect_uri` strict match (not wildcard); confirm `state` parameter generated + validated
- [ ] Password reset token: confirm entropy >= 128 bits, expires < 1h
- [ ] Email template (`order_confirmation.html`): confirm no `|safe` filter on user-controlled data → SSTI possible if present
- [ ] Celery config: confirm `serializer='json'` (NOT `pickle`)
- [ ] Login response timing: confirm constant-time check (existing email vs new email returns same time)
- [ ] Logout endpoint: confirm server-side token invalidation (not just client localStorage clear)
- [ ] Refund endpoint: confirm destination is always original card, never arbitrary IBAN
- [ ] Server-side amount validation on `/api/v5/payment/bog/initiate`: confirm amount is re-computed from `booking_id`, not taken from request body
- [ ] Idempotency keys on payment-initiate: confirm same booking can't be charged twice via concurrent requests
- [ ] Apple Pay merchant validation: confirm Apple's CA cert is verified, not client-supplied payload

### Frontend
- [ ] Confirm `dangerouslySetInnerHTML` usage (grep) — every instance must sanitize first with DOMPurify
- [ ] Confirm no auth token written to `localStorage` or `sessionStorage` (grep `setItem`)
- [ ] Confirm Service Worker scope is narrow (not `/*`)
- [ ] Confirm `target="_blank"` links have `rel="noopener noreferrer"` (tab nabbing)

### Infrastructure
- [ ] nginx version: `nginx -v` → if < 1.25.3, vulnerable to CVE-2023-44487 HTTP/2 rapid reset
- [ ] Django version: `python -c "import django; print(django.VERSION)"` → must be current LTS (5.0+) or 4.2 LTS
- [ ] DigitalOcean droplet: confirm SSH key-only login (no password), no root SSH, ufw enabled
- [ ] PostgreSQL: confirm `listen_addresses = 'localhost'` (not exposed publicly)
- [ ] Database backups: confirm exist, confirm tested restore quarterly
- [ ] `.env` file: confirm NOT in git history (`git log --all --full-history -- '*.env'`)

---

## Estimated total effort

| Phase | Items | Backend-days | Frontend-days | DevOps-days |
|-------|-------|--------------|---------------|-------------|
| Phase 1 (CRITICAL) | 1.1-1.16 | 1.5 | 0.5 | 1.0 |
| Phase 2 (HIGH) | 2.1-2.16 | 1.0 | 1.5 | 1.0 |
| Phase 3 (MEDIUM) | 3.1-3.8 | 0.5 | 0.5 | 0.5 |
| Phase 5 (code review) | source audit | 1.0 | 0.5 | — |
| **TOTAL** | | **4 days** | **3 days** | **2.5 days** |

**Grand total: ~9-10 dev-days.** At 100-200 GEL/hour Georgian market rate, this is **1500-3000 GEL of fix work** to prevent a $20K-$100K incident (40-200× ROI).

If splitting across team in parallel: **Phase 1 ships in 1 calendar day.**

---

## Deployment order (recommended)

**Day 1 (morning):** Phase 1 backend (1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 1.9) + nginx headers (1.13)
- Single deploy. All non-breaking. Backend restart required.

**Day 1 (afternoon):** Frontend rebuild + redeploy (1.10, 1.12) + Maps key restriction (1.15) + DNS records (1.14)
- Frontend builds with no sourcemaps; Maps key updated in Cloud Console; DNS records propagate over 1-24h.

**Day 2:** Phase 1.4 BOG signature verification + Phase 1.7 IDOR fixes (require careful testing, separate deploy).

**Day 3-4:** Cloudflare migration (1.16). DNS cutover. Test all flows on staging first if possible.

**Week 1:** Phase 2 hardening.

**Week 2-3:** Phase 3 compliance + monitoring.

**Quarterly:** Re-run verification script (`Phase 4`). Schedule annual pentest.

---

## References

- OWASP Top 10 (2021): https://owasp.org/Top10/
- Django security checklist: https://docs.djangoproject.com/en/5.0/topics/security/
- Django deployment checklist: https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/
- CRA production deployment: https://create-react-app.dev/docs/production-build/
- nginx security: https://nginx.org/en/docs/http/ngx_http_headers_module.html
- Mozilla Observatory (test results target: A+): https://observatory.mozilla.org/analyze/funfinder.ge
- securityheaders.com (test results target: A): https://securityheaders.com/?q=funfinder.ge
- HSTS preload list: https://hstspreload.org/
- Mail Tester (after SPF/DMARC): https://www.mail-tester.com/

---

**Document version:** 1.0
**Audit date:** 2026-05-13
**Prepared by:** funfinder.ge owner adversarial security review

For questions on any specific item, refer back to the original audit findings document or contact the owner directly.
