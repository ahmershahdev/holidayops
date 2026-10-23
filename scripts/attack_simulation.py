"""Simulated users and attackers against a running production image. Docs: docs/security.md,
"Attack simulation".

    docker compose -f docker-compose.prod.yml -f docker/simulation.yml up --build -d
    python scripts/attack_simulation.py            # SIM_PASSWORD is made up if not set

Six accounts (owner, admin, member, viewer, an outsider with an organization of their own, and a
target for password guessing) plus anonymous clients and API-key clients go through the product
and then try to break it. Every check prints PASS or FAIL; the exit code is the number of
failures. Standard library only, so it runs from any Python 3.12."""

import argparse
import base64
import hashlib
import hmac
import http.cookiejar
import json
import os
import secrets
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

COMPOSE = ["docker", "compose", "-f", "docker-compose.prod.yml", "-f", "docker/simulation.yml"]
XSS = '<script>alert(1)</script><img src=x onerror="alert(2)">'
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{f'  ({detail})' if detail and not ok else ''}")


class Client:
    """A browser: its own cookies and CSRF token, or an API key."""

    def __init__(self, base: str, key: str | None = None, agent: str = "Simulation") -> None:
        self.base = base
        self.key = key
        self.agent = agent
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar), NoRedirect()
        )

    def csrf(self) -> str:
        for cookie in self.jar:
            if cookie.name == "csrftoken":
                return cookie.value
        self.call("GET", "/api/v1/auth/csrf/")
        return next((c.value for c in self.jar if c.name == "csrftoken"), "")

    def call(
        self,
        method: str,
        path: str,
        body: Any = None,
        csrf: bool = True,
        headers: dict[str, str] | None = None,
        raw: bytes | None = None,
    ) -> tuple[int, Any, dict[str, str]]:
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        request = urllib.request.Request(self.base + path, data=data, method=method)  # noqa: S310
        request.add_header("User-Agent", self.agent)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if self.key:
            request.add_header("Authorization", f"Bearer {self.key}")
        if csrf and method not in {"GET", "HEAD"} and not self.key:
            request.add_header("X-CSRFToken", self.csrf())
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        try:
            with self.opener.open(request, timeout=30) as response:
                return response.status, _body(response.read()), dict(response.headers)
        except urllib.error.HTTPError as error:
            return error.code, _body(error.read()), dict(error.headers)

    def login(self, email: str, password: str) -> int:
        # Django rotates the CSRF token on login; the cookie jar picks up the new one.
        return self.call("POST", "/api/v1/auth/login/", {"email": email, "password": password})[0]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


def _body(raw: bytes) -> Any:
    try:
        return json.loads(raw)
    except ValueError:
        return raw.decode(errors="replace")


def totp(secret: str, offset: int = 0) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8))
    step = int(time.time() // 30) + offset
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    start = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[start : start + 4])[0] & 0x7FFFFFFF
    return f"{number % 10**6:06d}"


def seed(run: str, password: str) -> None:
    subprocess.run(  # noqa: S603 - fixed argv, run by the developer
        [
            *COMPOSE,
            "exec",
            "-T",
            "-e",
            f"SIM_PASSWORD={password}",
            "web",
            "python",
            "manage.py",
            "simulation_users",
            run,
        ],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    # 127.0.0.1, not localhost: on Windows "localhost" tries IPv6 first and stalls ~2 s a request.
    parser.add_argument("--base", default="http://127.0.0.1:8080")
    parser.add_argument("--skip-seed", action="store_true", help="accounts already exist")
    parser.add_argument("--run", default=secrets.token_hex(3))
    args = parser.parse_args()
    base = args.base.rstrip("/")
    password = os.environ.get("SIM_PASSWORD") or secrets.token_urlsafe(18)
    if not args.skip_seed:
        seed(args.run, password)
    email = {
        role: f"{role}-{args.run}@simulation.test"
        for role in ("owner", "admin", "member", "viewer", "outsider", "target")
    }
    users = {role: Client(base, agent=f"Simulation {role}") for role in email}
    anon = Client(base)

    status, _b, headers = anon.call("GET", "/")
    policy = headers.get("Content-Security-Policy", "")
    check("public pages allow no script", "script-src 'none'" in policy, policy)
    check("frames are denied", headers.get("X-Frame-Options") == "DENY")
    check("nosniff is set", headers.get("X-Content-Type-Options") == "nosniff")
    check("Permissions-Policy is set", "camera=()" in headers.get("Permissions-Policy", ""))
    nonces = set()
    for _ in range(2):
        _s, _b, h = anon.call("GET", "/signup", headers={"Accept": "text/html"})
        app_policy = h.get("Content-Security-Policy", "")
        nonces.add(app_policy.split("'nonce-")[1].split("'")[0] if "'nonce-" in app_policy else "")
    check("the web app has a fresh nonce per response", len(nonces) == 2 and "" not in nonces)
    check("signed-out /auth/me/ is 204", anon.call("GET", "/api/v1/auth/me/")[0] == 204)

    status, _b, _h = anon.call(
        "POST", "/api/v1/auth/login/", {"email": email["owner"], "password": password}, csrf=False
    )
    check("login without a CSRF token is refused (login CSRF)", status == 403, str(status))

    for role, client in users.items():
        status = client.login(email[role], password)
        check(f"{role} signs in", status == 200, str(status))

    owner, admin, member, viewer, outsider = (
        users[r] for r in ("owner", "admin", "member", "viewer", "outsider")
    )
    status, _b, _h = owner.call("POST", "/api/v1/orgs/", {"name": "Acme"}, csrf=False)
    check("a session write without a CSRF token is refused", status == 403, str(status))

    status, org, _h = owner.call("POST", "/api/v1/orgs/", {"name": f"Acme {XSS}"})
    check("owner creates an organization", status == 201, str(status))
    slug = org["slug"]
    for role in ("admin", "member", "viewer"):
        status, _b, _h = owner.call(
            "POST", f"/api/v1/orgs/{slug}/members/", {"email": email[role], "role": role}
        )
        check(f"owner adds the {role}", status == 201, str(status))
    calendar_body = {"name": XSS, "sources": [{"country": "PK"}], "is_public": False}
    status, calendar, _h = owner.call("POST", f"/api/v1/orgs/{slug}/calendars/", calendar_body)
    check("owner creates a calendar", status == 201, str(status))
    cal = f"/api/v1/orgs/{slug}/calendars/{calendar['id']}"
    status, other_org, _h = outsider.call("POST", "/api/v1/orgs/", {"name": "Elsewhere"})
    check("outsider creates their own organization", status == 201, str(status))

    status, data, headers = owner.call("GET", f"{cal}/")
    check(
        "names come back as JSON text, never HTML",
        headers.get("Content-Type", "").startswith("application/json") and data["name"] == XSS,
    )
    status, feed, _h = owner.call("POST", f"{cal}/feeds/", {"label": XSS})
    feed_path = urllib.parse.urlparse(feed.get("url", "")).path if status == 201 else ""
    if feed_path:
        _s, _b, headers = anon.call("GET", feed_path, headers={"Accept": "text/calendar"})
        check(
            "iCal feeds are served as text/calendar",
            headers.get("Content-Type", "").startswith("text/calendar"),
        )
    else:
        check("owner creates a feed", False, str(status))

    day = {"date": "2027-03-01", "name": "Offsite", "kind": "closure"}
    check("viewer can't add a day off", viewer.call("POST", f"{cal}/custom-days/", day)[0] == 403)
    check("member adds a day off", member.call("POST", f"{cal}/custom-days/", day)[0] == 201)
    check(
        "member can't create API keys",
        member.call("POST", f"/api/v1/orgs/{slug}/api-keys/", {"name": "x"})[0] == 403,
    )
    check(
        "admin can't create API keys (owners only)",
        admin.call("POST", f"/api/v1/orgs/{slug}/api-keys/", {"name": "x"})[0] == 403,
    )
    check("viewer can't delete the calendar", viewer.call("DELETE", f"{cal}/")[0] == 403)
    check(
        "admin can't make anyone an owner",
        admin.call(
            "POST", f"/api/v1/orgs/{slug}/members/", {"email": email["outsider"], "role": "owner"}
        )[0]
        == 403,
    )

    for label, method, path in (
        ("read the organization", "GET", f"/api/v1/orgs/{slug}/"),
        ("read the calendar", "GET", f"{cal}/"),
        ("change the calendar", "PATCH", f"{cal}/"),
        ("list days off", "GET", f"{cal}/custom-days/"),
        ("list members", "GET", f"/api/v1/orgs/{slug}/members/"),
        ("read the audit log", "GET", f"/api/v1/orgs/{slug}/audit-log/"),
        ("list API keys", "GET", f"/api/v1/orgs/{slug}/api-keys/"),
    ):
        status = outsider.call(method, path, {"name": "pwned"} if method == "PATCH" else None)[0]
        check(f"outsider can't {label} (404)", status == 404, str(status))
    wrong = f"/api/v1/orgs/{other_org['slug']}/calendars/{calendar['id']}/"
    check("a calendar id under another org's slug is 404", outsider.call("GET", wrong)[0] == 404)

    for url in (
        "http://127.0.0.1/",
        "https://127.0.0.1/",
        "https://169.254.169.254/latest/",
        "https://localhost/",
        "https://10.0.0.5/",
        "https://[::1]/",
        "https://db:3306/",
    ):
        status = admin.call(
            "POST", f"/api/v1/orgs/{slug}/webhooks/", {"url": url, "events": ["calendar.updated"]}
        )[0]
        check(f"webhook to {url} is refused", status == 400, str(status))

    def make_key(n: int) -> int:
        return owner.call("POST", f"/api/v1/orgs/{slug}/api-keys/", {"name": f"race {n}"})[0]

    with ThreadPoolExecutor(8) as pool:
        created = sum(1 for status in pool.map(make_key, range(8)) if status == 201)
    _s, keys, _h = owner.call("GET", f"/api/v1/orgs/{slug}/api-keys/")
    check(
        "8 parallel key requests create exactly the plan's 3 keys",
        len(keys) == 3,
        f"{created} created, {len(keys)} active",
    )
    revoked = [
        owner.call("DELETE", f"/api/v1/orgs/{slug}/api-keys/{row['id']}/")[0] for row in keys
    ]
    check("owner revokes the keys", set(revoked) <= {204}, str(revoked))
    status, made, _h = owner.call("POST", f"/api/v1/orgs/{slug}/api-keys/", {"name": "sim"})
    check("owner creates a key", status == 201, f"{status} {made}")
    if status != 201:
        return 1
    key = made["key"]
    status, made2, _h = outsider.call(
        "POST", f"/api/v1/orgs/{other_org['slug']}/api-keys/", {"name": "theirs"}
    )
    their_key = made2.get("key", "")
    check_path = "/api/v1/business-days/check/?date=2027-03-01&calendar="
    check(
        "a key reads its own org's calendar",
        Client(base, key=key).call("GET", check_path + calendar["id"])[0] == 200,
    )
    status = Client(base, key=their_key).call("GET", check_path + calendar["id"])[0]
    check("another org's key can't read the calendar", status in {400, 403, 404}, str(status))
    check(
        "a made-up key is refused",
        Client(base, key="hops_abcdefgh_" + "x" * 40).call("GET", "/api/v1/countries/")[0] == 401,
    )
    owner.call("DELETE", f"/api/v1/orgs/{slug}/api-keys/{made['id']}/")
    check(
        "a revoked key is refused",
        Client(base, key=key).call("GET", "/api/v1/countries/")[0] == 401,
    )
    burst = Client(base, key=their_key)
    statuses = [burst.call("GET", "/api/v1/countries/")[0] for _ in range(130)]
    check("the per-key rate limit answers 429", 429 in statuses)

    _s, setup, _h = owner.call("POST", "/api/v1/auth/2fa/setup/")
    secret = setup.get("secret", "")
    check(
        "owner turns on two-factor",
        owner.call("POST", "/api/v1/auth/2fa/confirm/", {"code": totp(secret)})[0] == 200,
    )
    time.sleep(31 - time.time() % 30)
    code = totp(secret)
    first = Client(base)
    check("password alone waits for the code", first.login(email["owner"], password) == 202)
    check(
        "the code signs in",
        first.call("POST", "/api/v1/auth/2fa/verify/", {"code": code})[0] == 200,
    )
    replay = Client(base)
    replay.login(email["owner"], password)
    status = replay.call("POST", "/api/v1/auth/2fa/verify/", {"code": code})[0]
    check("the same code can't be used twice", status == 400, str(status))

    _s, rows, _h = owner.call("GET", "/api/v1/auth/sessions/")
    check("owner sees their signed-in devices", len(rows) >= 2, str(len(rows)))
    other = next((r for r in rows if not r["current"]), None)
    if other:
        status = outsider.call("DELETE", f"/api/v1/auth/sessions/{other['id']}/")[0]
        check("outsider can't sign out the owner's device", status == 404, str(status))
    check(
        "owner signs out other devices",
        owner.call("POST", "/api/v1/auth/sessions/others/")[0] == 200,
    )
    check("the other device is signed out", first.call("GET", "/api/v1/auth/me/")[0] == 204)

    for query in (
        "country=PK'%20OR%20'1'='1&year=2027",
        "country=PK&year=2027%3BDROP%20TABLE",
        "country=../../etc/passwd&year=2027",
    ):
        status = anon.call("GET", f"/api/v1/holidays/?{query}")[0]
        check(f"hostile query is a 400, not a 500 ({query[:20]})", status == 400, str(status))
    status = anon.call("POST", "/api/v1/auth/login/", raw=b"x" * 600_000)[0]
    check("a 600 KB body is refused with 413", status == 413, str(status))

    taken = anon.call(
        "POST",
        "/api/v1/auth/signup/",
        {"email": email["viewer"], "password": "a-long-sim-passphrase-1"},
    )
    fresh = anon.call(
        "POST",
        "/api/v1/auth/signup/",
        {"email": f"new-{args.run}@simulation.test", "password": "a-long-sim-passphrase-1"},
    )
    check(
        "sign-up answers the same for a taken address",
        taken[0] == fresh[0] == 202 and taken[1] == fresh[1],
    )

    attacker = Client(base)
    statuses = [attacker.login(email["target"], f"guess-{n}") for n in range(12)]
    check("10 wrong passwords lock the account", statuses[-1] == 429, str(statuses[-2:]))
    check(
        "the right password waits out the lock too",
        Client(base).login(email["target"], password) == 429,
    )

    flood = [anon.call("GET", "/api/v1/countries/")[0] for _ in range(70)]
    check("anonymous calls are limited per IP", 429 in flood)
    spoofed = anon.call("GET", "/api/v1/countries/", headers={"X-Forwarded-For": "203.0.113.9"})
    check("a forged X-Forwarded-For doesn't reset the limit", spoofed[0] == 429, str(spoofed[0]))

    failed = [name for name, ok, _d in results if not ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    print(
        "Now read the security log: docker compose -f docker-compose.prod.yml logs web | "
        "grep holidayops.security"
    )
    return len(failed)


if __name__ == "__main__":
    sys.exit(main())
