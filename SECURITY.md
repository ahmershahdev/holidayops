# Security Policy

## Supported versions

HolidayOps has no releases yet. Security fixes go to the `main` branch.

## Reporting a vulnerability

Please don't open a public issue for security problems.

Report it privately through GitHub: open the **Security** tab of this repository and click
**Report a vulnerability**. Include the steps to reproduce, what an attacker could do, and the
affected endpoint or file if you know it.

You should get a reply within 7 days. Once the issue is confirmed, a fix is prepared in a private
advisory and published with credit to you, unless you prefer to stay anonymous.

## Scope

In scope: the API, authentication and API keys, rate limiting, calendar sharing and iCal feeds, and
anything that leaks one organization's data to another.

Out of scope: wrong or missing holiday dates. Those come from the
[holidays](https://github.com/vacanza/holidays) library; report them there or in a normal issue here.
