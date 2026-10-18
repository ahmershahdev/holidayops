# Security policy

HolidayOps holds company calendars, API keys and personal data such as email addresses. We take
reports seriously and fix confirmed issues quickly.

## Supported versions

HolidayOps has no versioned releases yet. Security fixes go to the `main` branch and are deployed
from there.

| Version | Supported |
|---|---|
| `main` | Yes |
| Anything else | No |

## Reporting a vulnerability

**Please don't open a public issue, pull request or discussion for a security problem.**

Report it privately, in either of these ways:

1. **GitHub (preferred):** open the
   [Security tab](https://github.com/ahmershahdev/holidayops/security/advisories/new) of this
   repository and choose **Report a vulnerability**.
2. **Email:** write to [support@ahmershah.dev](mailto:support@ahmershah.dev) with "Security" in the
   subject.

Include as much of this as you can:

- the affected endpoint, page or file,
- steps to reproduce, or a proof of concept,
- what an attacker could do with it,
- any logs, requests or screenshots that help.

## What happens next

| When | What |
|---|---|
| Within 7 days | We confirm we received the report and give a first assessment |
| As soon as possible | We fix the issue in a private advisory and keep you updated |
| After the fix ships | We publish the advisory and credit you, unless you prefer to stay anonymous |

If a report turns out not to be a vulnerability, we'll explain why.

## Scope

In scope:

- the REST API, authentication, sessions and CSRF,
- API keys, quotas and rate limiting,
- organization isolation (any way to read or change another organization's data),
- invites, iCal feed links and digest unsubscribe links,
- webhooks, including server-side request forgery,
- the web app and the public pages (XSS, injection, CSP bypass),
- secrets or personal data exposed in logs, responses or the repository.

Out of scope:

- wrong or missing holiday dates: they come from the
  [holidays](https://github.com/vacanza/holidays) library, so report them there or in a normal issue,
- denial of service by sheer traffic volume,
- findings from automated scanners without a demonstrated impact,
- missing best-practice headers that don't lead to an exploit,
- social engineering, and attacks that need physical access to a device.

## Safe harbour

We won't take action against good-faith research that follows this policy. While testing:

- use your own accounts and organizations, and never access or change other people's data,
- don't degrade the service for others,
- give us reasonable time to fix an issue before you disclose it.

## How HolidayOps is protected

The design is documented in [docs/security.md](docs/security.md): Argon2 passwords, hashed API keys
and tokens, tenant isolation tested on every endpoint, per-IP, per-key and per-organization rate
limits, an SSRF guard for webhooks, a strict Content Security Policy, and exact-pinned dependencies
checked by Dependabot, pip-audit and CodeQL.
