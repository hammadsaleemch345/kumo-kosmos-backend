# Silk & Sin — Project Context

Living doc. Update this whenever scope, decisions, or status change, so future sessions don't need to re-read every source file from scratch.

Source files this is built from: `README.md`, `SOW_Silk_and_Sin.docx`, `feature-checklist.md`, `silk-and-sin-prototype.html`, plus decisions made in chat that aren't written down elsewhere yet.

---

## Who and what

- Client: Kumo Kosmos, adult fiction subscription site, migrating off Substack
- Contract: Upwork, signed August 3 2026. Total $4400 across 3 milestones
- Client is new to the technical side and to Upwork itself, keep anything client facing (admin copy, errors, setup instructions) plain, not jargon heavy
- Frontend prototype (`silk-and-sin-prototype.html`) is done and is the behavior spec. `feature-checklist.md` documents what's real UI in it vs what's fully missing. This project is the backend build.
- Backend stack: Python, FastAPI, PostgreSQL (SQLAlchemy + Alembic), not specified by the client, our own technical choice. Code lives in `backend/`.

## Build progress

- **Phase 1 done:** `backend/app/models.py` has the full schema (users, sessions, password reset tokens, tiers, stories, polls, bookmarks, discount codes, payment events), migration in `backend/alembic/versions/0001_initial.py`. Auth in `backend/app/routers/auth.py`: signup, login, logout (real server-side session revocation), `/auth/me`, password reset request/confirm (generic response so it doesn't leak which emails are registered). Email is normalized to lowercase everywhere to prevent case-variant duplicate accounts. Passwords capped at 72 bytes (bcrypt's hard limit), validated on UTF-8 byte length not character count.
- **Phase 2, most of the non-CCBill-blocked work done:**
  - **Substack importer** (`backend/app/importer/`): HTML tier-split parser (`html_parser.py`), posts/subscriber CSV parsers, idempotent DB import (`db_import.py`, matches by email/substack_post_id so re-runs never duplicate), and a ZIP entry point (`zip_import.py`) matching requirement 1 (parse from ZIP, no live scraping). Verified against the actual client export: 111 stories imported, 19 flagged non-story titles for human confirmation, 3 unpublished skipped, 2585 free + 199 veteran subscribers classified correctly, zero parse errors across all 133 posts. Veteran subscribers get email-only import (`is_veteran_sub`, no password/plan data) with a `veteran_outreach_sent_at` field reserved so the future YNOT Mail sending step can guarantee no duplicate outreach on a re-run.
  - **File storage** (`backend/app/storage.py` + `routers/uploads.py`): local disk for now (client hadn't picked S3/Cloudinary/self-hosted, open kickoff question), swappable behind one function. Extension allowlist, 10MB cap, admin/owner-only.
  - **Admin endpoints wired to real data**: story CRUD (`routers/admin_stories.py`) and subscriber list/search (`routers/admin_subscribers.py`), both role-gated to admin/owner via a new `require_role` dependency.
  - **CCBill scaffolding** (`backend/app/ccbill.py` + `routers/ccbill_webhooks.py`): checkout URL builder (CCBill's documented dynamic-pricing digest formula) and a webhook receiver that logs every raw event before acting on it and updates `User.subscription_status`/`role` in a separate step — the SOW's "payment event handling isolated from subscription logic" requirement, built as an actual `PaymentEvent` table plus a dedicated apply-status function, not just a comment. Idempotent on (subscription_id, event_type, timestamp). **Still blocked on the client's real CCBill account details** (client account ID, subaccount, dynamic pricing salt, webhook secret) — checkout builder raises a clear error if used before those are set, rather than silently producing a broken URL.
  - 54 tests passing in `backend/tests/`, including full round-trips against the real client export files.
- **Frontend wiring started:** `silk-and-sin-prototype.html` now has a real login/signup panel on the Account page (`#account-auth-panel`), wired to `/auth/signup`, `/auth/login`, `/auth/logout`, `/auth/me` via `fetch`. Session token persists in `localStorage` and restores on page load. On success it feeds the real role into the prototype's existing `setRole()` so all the prototype's role-gated rendering (Admin tab, paywall, etc.) works off a real session instead of the dev role switcher, without having to rewire every render function individually. CORS added to the backend (`app/main.py`) and a `/uploads` static mount for serving cover images. Verified against a real running `uvicorn` process, not just pytest: signup → `/auth/me` → logout → session correctly revoked → login again, all confirmed via curl replicating the exact requests the browser JS sends, including the CORS preflight. One real deployment gap this surfaced: migrations need to actually be run (`alembic upgrade head`) before the server can serve traffic — obvious in hindsight, but pytest's in-memory DB setup never exercised that path, so it hadn't been verified until now.
  - **Stories are now wired for real, content is actually locked down server-side.** Client (real, non-technical) testing on the live deploy caught that the reading page was showing the same client-side data structure regardless of role, all guest/free/paid text was loaded into the browser for everyone, the paywall was purely a display gate, not real security — a guest could read the full paid text via dev tools. Fixed properly: added `GET /stories/{slug}` (`backend/app/routers/stories.py`), a public endpoint (guests allowed) that truncates `content` server-side using `free_wall_marker`/`paid_wall_marker` based on the caller's actual role (resolved from their session token if present, via a new `get_current_user_optional` dependency in `deps.py` — doesn't 401 on a missing/garbage token, just treats the caller as a guest). The response body itself never contains more than the caller is entitled to. Verified at the raw HTTP level against the live server, not just visually: created a real story with distinct guest/free/paid sections, confirmed via curl with no auth header that the free-subscriber and paid text are genuinely absent from the response bytes, not just hidden in the UI, then confirmed free and paid tokens each get exactly what they should. 6 new tests in `backend/tests/test_stories.py`.
  - Frontend (`silk-and-sin-prototype.html`) `renderRead()` now fetches from this real endpoint first; falls back to the old client-side mock content only for demo stories that don't exist in the real backend yet (nothing to protect there, it's placeholder lorem ipsum). Once a story is actually migrated in (via the Substack importer or admin panel), it's for real, not before.
  - Not yet wired: uploads, subscribers, admin dashboard UI (all built and tested on the backend, just not yet connected to their prototype UI). Stories now the exception, that one's real.
  - **Four prototype bugs client found via real testing, fixed:** (1) login signing out on every refresh — actual cause was a JS ordering bug, the session-restore function referenced a variable before it was declared, silently failing every time; (2) refresh always bounced to the homepage instead of wherever you were — prototype had no URL routing at all, added hash-based routing (`#read/story-id` etc.) site-wide, not just for stories; (3) "Came X" label typo on the reading page stats (left the "CAME X3"-style catalog card badge alone, that's an intentional ×-multiplier notation, different thing); (4) clicking a tag on the reading page did nothing — was wired to the wrong function (one meant for in-page filter toggling on the catalog page). Explicitly told the client only the login bug was covered under the signed SOW (auth is in scope, frontend polish isn't, prototype was handed over "done" before this contract), the other three were done anyway since they're small and the client asked.
- **Deployment set up, switched from Fly.io to DigitalOcean.** Fly.io was built first, then dropped: the client themselves flagged that Fly's terms have language against sexually explicit content (they remembered this correctly from earlier research), and we had no written confirmation it was actually fine. Rather than chase that confirmation, switched to DigitalOcean, which explicitly allows legal adult content, no ambiguity. Client has since created a DigitalOcean account.
  - `backend/Dockerfile`: multi-stage, uses `uv` for fast installs, pinned to Python 3.12 not 3.14 (3.14 is too new for stable wheels of several deps, confirmed the hard way in local dev). `backend/start.sh` runs `alembic upgrade head` before starting the app on every container start (DigitalOcean has no Fly-style `release_command`, so migrations run this way instead, safe since it's a no-op once already current). `backend/docker-compose.yml` runs the app plus a self-hosted Postgres container together on one Droplet — deliberately not DigitalOcean's managed Postgres product, which alone costs more than the whole hosting budget quoted to the client (~$15/mo vs the ~$6/mo Droplet).
  - `infra/`: Terraform (DigitalOcean provider) provisions a Droplet (Docker pre-installed via cloud-init), a firewall (only 22 and 8080 open, Postgres never exposed publicly), an SSH key, and a private container registry for the built image. Full deploy sequence in `infra/README.md`.
  - **Live and deployed for real, not just planned.** Client invited the developer into their DigitalOcean account and added a card. `terraform apply` ran successfully: Droplet, firewall, SSH key, and container registry all provisioned. Image built for `linux/amd64` specifically (built locally on arm64 first, which silently produced an incompatible image on the x86_64 Droplet — real bug, caught immediately when the pull failed with a manifest platform mismatch, fixed with `docker buildx build --platform linux/amd64`). Deployed via `docker compose` on the Droplet with app + self-hosted Postgres. Confirmed externally, not just from inside the Droplet: `curl http://165.22.187.71:8080/health` and a full signup → `/auth/me` round trip both work from outside, against real infrastructure.
  - **The earlier Fly.io attempt (and this DO deploy) caught a real production bug that would've hit regardless of host:** `User.role` and `User.subscription_status` are SQLAlchemy enum columns. Postgres enforces its enum type strictly; SQLite doesn't. SQLAlchemy was inserting the Python enum member's NAME (`"FREE"`) while the Postgres enum type holds lowercase VALUES (`"free"`) — every signup would have 500'd in production despite all 54 tests passing, since the test suite only ever ran against SQLite. Fixed with `values_callable` on both enum columns, verified against real Postgres. Exactly why testing against real Postgres before launch matters, not just trusting the SQLite-backed test suite.
  - **Domain routing and real HTTPS, both done and verified.** Client got Namecheap DNS access, added `@`, `api`, and `www` records (A/A/CNAME) all pointing to `165.22.187.71`, confirmed resolving at the authoritative nameserver and via public resolvers. Reverse proxy switched from plain nginx to **Caddy** (`backend/Caddyfile`, replacing the deleted `nginx-proxy.conf`) specifically so HTTPS could be added with zero manual certificate work — Caddy auto-provisions and auto-renews real Let's Encrypt certificates just from the domain names listed, no certbot, no renewal cron job to maintain. `docker-compose.yml`'s `proxy` service now runs `caddy:alpine`, publishes both 80 and 443, persists certs in a `caddy_data` volume so they survive container restarts. Firewall opened 443 (`infra/main.tf`).
  - Routing: `api.kumokosmos.com` → the FastAPI app, `kumokosmos.com`/`www.kumokosmos.com` → the frontend. Frontend's `API_BASE` now `https://api.kumokosmos.com`. `app`/`frontend` containers still don't publish ports directly, only reachable through the proxy over the internal Docker network.
  - **Verified for real, not assumed:** watched Caddy's logs obtain all three certificates live against the actual Let's Encrypt ACME server (not staging), confirmed valid `CN=` matching each domain via `curl -v`, confirmed HTTP→HTTPS redirect (308) works, confirmed `www` resolves via CNAME and gets its own valid cert. Site is genuinely live over HTTPS on the real domain now, not just the testing IP.
- **Large round of client-reported feedback fixed (2026-08-14), all deployed and verified live.** Client did real click-through testing on the live HTTPS site and reported 9 issues/asks in one message. Went through each:
  - **Bookmarks and favorites now actually persist** (`backend/app/models.py` — new `Favorite` table; `backend/app/routers/me.py` — `/me/bookmarks`, `/me/favorites`, all real per-user, tested for cross-user isolation). Previously pure in-memory JS state, gone on every refresh, exactly what the client reported. Frontend reading page now checks login + fetches real state; falls back to old local-only behavior for demo (non-backend) stories only.
  - **Bookmark UX changed as requested:** no more full-passage bright yellow highlight — now a small marker icon at the start of the bookmarked line. Added a floating "🔖 Bookmark" prompt that appears when you select text in a story, instead of requiring the separate toolbar button. Fixed a real logic bug found while building this: the popup could have silently *deleted* an existing bookmark instead of moving it to a new selection — now it always sets, never toggles.
  - **Static pages (About/FAQ/Terms/Contact) are now real and admin-editable** (`backend/app/models.py` — `SiteContentPage`; `backend/app/routers/pages.py` — public read + admin write). Seeded live with the client's exact provided text for all four pages, including a new Contact page (email + phone) that didn't exist before. The existing plain-textarea admin editor (client explicitly said this was fine, no rich WYSIWYG needed yet) now actually saves for real via this endpoint instead of an in-memory object.
  - **Fixed the actual footer routing bug** the client found: About/FAQ/Terms all landed on the same content because `go()` had a hardcoded `renderStatic('about')` regardless of which tab was selected. Root-caused and fixed, not just patched around — the about-page tabs are now driven by the URL param like every other page.
  - **New posts now actually persist** — client correctly guessed this was pending backend wiring. Post editor's Publish/Save Draft now call the real `/admin/stories` endpoints (already built and tested from earlier), converting the editor's guest/free/paid buckets into the single content string + wall-marker-offset format the rest of the system already uses (matches the Substack importer's format exactly). Known follow-up, not yet done: newly published real posts don't yet show up in the catalog/browse pages, since those still render from local demo data — separate wiring task, same category as the already-tracked "admin dashboard UI not yet wired."
  - **Added a "+ New post" button** to the top nav for admin/owner, toggled by the same role check as the Admin tab.
  - **Answered and built for the re-import question:** confirmed re-running the import never duplicates (matches by email/substack_post_id, already tested). Split it into two independently-triggerable endpoints per the client's actual need — `/admin/import/full` (ZIP, posts + subs) and `/admin/import/subscribers` (just the CSV) — since posts only need importing once but subscribers may need re-importing any time as a backup path. Both tested including the specific re-run scenarios.
  - **Stripped the dev-only floating role/viewport switcher** ("Owns Anthology II" checkbox included), since the client explicitly tied this to when they message CCBill for review. Found and fixed a real bug this would have caused: `renderRead` had a non-null-safe reference to the now-removed `role-select` element that would have thrown on every story page load. Left the separate, permanent "Preview site as" control inside the real Admin tab alone — that one's meant to stay per the original feature spec, not a testing artifact.
  - All backend changes tested (79 tests passing, up from 60), then deployed for real: new Postgres migration applied live via `alembic upgrade head` against the already-running production database (couldn't just edit the old migration file anymore like early in the project, since real data now exists — this is the first real schema change since going live), image rebuilt and pushed, containers restarted, static pages seeded via the live API, footer/dev-bar changes confirmed live via curl against `kumokosmos.com`.
- **Not started yet:** admin revenue stats (needs live CCBill), veteran discount-at-checkout wiring (needs live CCBill), win-back campaign emails and the rest of YNOT Mail (client hasn't found the SPF/DKIM record values in their YNOT Mail dashboard yet), catalog/browse pages still rendering from local demo data instead of real backend stories, Segpay backup integration (quoted separately, $450, waiting on client's go-ahead / Segpay account setup), an actual admin panel button for the Substack importer (backend works, no UI yet — client wants self-serve repeat subscriber imports). See Build Plan below for order.

## Milestones and status

| Milestone | Trigger | Amount | Status |
|---|---|---|---|
| Upfront | Contract signed | $1320 | Paid |
| Midpoint | Login + CCBill sandbox working | $1760 | Activated, next payment trigger, current priority |
| Launch | Site is live | $1320 | Not started |

- Client has a CCBill merchant application in progress
- Client set up a YNOT Mail account, still waiting on verification
- Timeline: 4 to 6 weeks, contingent on early CCBill sandbox access. If CCBill is delayed, keep building everything not dependent on it in parallel
- 30 days free bug coverage after launch for anything that doesn't work as scoped. New features after that are quoted separately
- Weekly updates promised, plus immediate notice of any blocker

## In scope (signed SOW)

- User auth: signup, login, logout, password reset, sessions
- Real database: subscribers, stories, polls, bookmarks, discount codes (currently browser memory only in prototype)
- CCBill integration: checkout, webhooks, recurring billing, subscription state (active, past due, cancelled, chargeback). Payment event handling kept isolated from subscription logic on purpose, deliberate architecture choice for manageable webhook retries/failed renewals
- YNOT Mail integration: transactional emails, post notifications, trial reminders, win back campaigns, bulk campaigns, double opt in
- File storage for uploads (currently base64 previews in prototype)
- Wire existing admin dashboard to real backend data
- Substack import tool (see below)
- Strip all dev/testing only elements before launch: role switcher, mobile/desktop viewport toggle, "Owns Anthology II" test checkbox, any other dev bars. Client confirmed directly, required launch step

## Explicitly NOT in scope

- Story tag migration (Substack doesn't export tags, confirmed by inspecting the actual export)
- Image migration from Substack (client handling manually, confirmed, so few they'll do it themselves)
- CCBill/YNOT Mail account setup itself (client's side)
- Legal review or drafting of ToS/Privacy/Refund Policy content
- Dedicated multi-device QA pass (client quoted $350–500, declined). Instead: check core flows on one device per type (phone/tablet/desktop) as built, client does own pre-launch check
- Anything not listed as in scope above — flag and ask before building, don't assume

## Launch bar

Launch means everything under "In scope" works as described. Anything visible in the prototype but not explicitly listed is not guaranteed production ready unless separately scoped/priced. Example: prototype search is a client-side array scan, fine for launch, real full-text search was never scoped or priced.

## Substack import tool — full spec

Export inspected directly (137 posts, 4 static pages, 2785 subscriber rows). Confirmed findings:

- `posts.csv`: post_id, post_date, is_published, email_sent_at, inbox_sent_at, type, audience, title, subtitle, podcast_url. `audience` (everyone/only_paid/only_free) reflects EMAIL distribution, not in-post paywall structure, don't conflate. 4 rows are `type: page` (About/FAQ style), exclude from story import.
- `email_list*.csv`: email, active_subscription, expiry, plan, email_disabled, created_at, first_payment_at. This is the FULL subscriber list including paid subscribers with plan/payment info, not just a free list.
- Each post's HTML has a genuine three-way split embedded as detectable markers: non-subscriber preview, free-subscriber section, paid-subscriber section. Not the standard single-marker Substack paywall, don't assume Steady/WordPress-plugin importer logic applies. Two marker patterns found in practice: `paywall-jump` (everything after is paid) on ~16 posts, explicit `data-dynamic-audiences="paid_sub,..."` wrapper on ~76 posts. Parser needs both code paths.
- Story tag data is NOT anywhere in the export (not HTML, not CSV). Confirmed by direct inspection, not an assumption.
- Images are only linked to Substack's S3 storage in the HTML, not bundled as files.

Requirements for the importer (from SOW + chat decisions):

1. Parse from the ZIP export, not live URL scraping (ruled out as unreliable)
2. Detect the three-tier split per post, map onto the site's existing free-wall/paid-wall marker system in the post editor
3. Exclude `type: page` rows. No tags column exists anywhere, so separating story posts from misc posts (polls, Q&A, announcements) needs another signal, e.g. title pattern. Confirm with client before excluding anything not obviously a static page
4. Skip images entirely, confirmed with client, they're handling those manually
5. From the subscriber CSV: import free subscribers normally. Anyone with paid history (has a plan/payment record) gets ONLY their email imported, into a separate "veteran subs" segment. Do NOT import payment or plan data itself — client explicit about this, partly legal risk around payment data
6. Veteran subs who later sign up as paid on the new site get a one-time discount automatically applied at CCBill checkout. Client's current number is 40% off first couple months, treat as their current thinking not fixed. Discount % and duration must be editable from the admin panel, not hardcoded. Needs to be wired against the client's actual CCBill account setup, confirm CCBill account details before building the checkout side
7. Whole import must be safely re-runnable: match by email, no duplicate subscribers, no duplicate/resent veteran outreach emails on a second run. Client will keep posting on Substack during the build and will re-run this periodically

**Note:** `feature-checklist.md`'s own Substack section (CSV `name,email,tier` format, manual copy-paste migration) is now outdated / superseded by the above. Don't build off that section, the SOW is the current source of truth per its own conflict clause.

## Frontend status (from feature-checklist.md)

- Everything under "IN PROTOTYPE" in the checklist is real, clickable, testable UI/logic (no real backend behind it). Treat as a behavior spec, not starting code, especially anything touching auth, payments, or data storage.
- Everything under "MISSING ALTOGETHER" is scope to estimate/build from zero — matches the SOW's "In scope" list above.
- Two checklist items are flagged "still needed" but are NOT in the signed SOW: Founder tier name credits, launch promo setup (banner/CTA/cohort tracking for a limited-time discount). Per SOW's own rule, these need separate scoping/quoting if the client still wants them, not silently included.
- Dev-only elements confirmed for removal pre-launch: role switcher, mobile/desktop viewport toggle, "Owns Anthology II" checkbox.

## Build Plan

Ordered by real dependency, not by SOW list order. Two things block everything: the database and auth. Past that, work splits into what can run in parallel and what genuinely has to wait on CCBill being functional.

### Phase 1 — Foundation, blocks everything else

- Real database schema: subscribers, stories, polls, bookmarks, discount codes
- Auth: signup, login, logout, password reset, sessions

### Phase 2 — Parallel once Phase 1 is done, none of these block each other

- CCBill sandbox integration: checkout, webhooks, subscription state (kept isolated from subscription logic per the SOW's architecture note, this is what Milestone 2 is paid on)
- File storage for uploads, replacing base64 previews
- Admin dashboard wired to real data, the parts with no CCBill dependency: subscriber lists, posts, polls, storefront, site settings
- Substack importer, data side only: parse ZIP, detect the three-tier split, exclude pages, import free subscribers, build the veteran segment (emails only, no payment data)
- YNOT Mail integration: transactional emails, notifications, double opt-in, campaign sending. Gated only on the client finishing domain + DNS setup (SPF/DKIM), not on CCBill, so this doesn't need to wait in line behind Phase 2's CCBill work

### Phase 3 — Depends on Phase 2's CCBill work being functional

- Veteran subscriber one-time discount, wired into CCBill checkout, % and duration editable in admin
- Admin revenue stat cards and growth chart, sourced from real billing events
- Win-back campaign emails (needs both YNOT Mail and real subscription/cancellation state)

### Phase 4 — Pre-launch

- Strip dev-only elements: role switcher, viewport toggle, "Owns Anthology II" checkbox. Deliberately last, these are actively used to test auth/role gating and mobile behavior while building everything above
- One-device-per-type QA pass (phone/tablet/desktop), per the SOW's agreed scope, not a full multi-device pass
- Swap CCBill + YNOT Mail from sandbox to production credentials

### Fallback if CCBill approval is delayed past Phase 1

Keep going on Phase 2's non-CCBill items, file storage, admin data wiring, Substack importer data side, YNOT Mail, per the SOW's own instruction to keep building in parallel rather than blocking.

### Known false-parallel traps, already accounted for above, noting so they don't get re-introduced

- "Admin wired to real data" is not one atomic task, the discount and revenue-stat parts need CCBill live, the rest doesn't
- The Substack importer's checkout-discount piece (requirement 6) needs CCBill live even though the data-import piece (requirements 1-5, 7) doesn't
- YNOT Mail does NOT need to wait on CCBill, only on DNS setup (domain now in hand: `kumokosmos.com`, SPF/DKIM records still need to be added)

## Open questions / pending on client

- CCBill account details still needed before building checkout/discount wiring — in active review as of 2026-09-10, CCBill asked for footer/policy additions (now done) before proceeding, still no merchant credentials yet
- Whether client wants to proceed with the $450 Segpay backup integration, or wait and see if CCBill comes through first
- SPF/DKIM record values from the client's YNOT Mail dashboard, still not found/shared — blocks starting YNOT Mail work
- Whether client wants the Substack importer's admin UI button built now or closer to launch
- Whether Founder tier name credits and launch promo setup should be quoted as add-ons
- ~~Domain purchase and DNS (SPF/DKIM) setup pending on client~~ — domain purchased, resolved below
- ~~DigitalOcean account invite and card on file~~ — done, live test deploy running at `165.22.187.71`

## Decision log (chronological, chat-sourced)

- Client confirmed: no image export/migration needed, they'll do it manually, too few images to bother automating
- Client confirmed: veteran list = emails only, explicitly not payment/plan data, partly for legal reasons
- Client confirmed: wants automatic one-time discount for veteran subs on first paid signup, admin-editable %, wired through CCBill
- Client confirmed: wants re-import to be idempotent (safe to re-run without duplicating subs or resending veteran outreach)
- Client confirmed payment processor: CCBill (not yet fully set up, merchant application in progress)
- Client purchased the domain and set up the business email: domain `kumokosmos.com`, email `contact@kumokosmos.com`. Shared with us the day before this was logged. Still need to add SPF/DKIM DNS records on this domain to authorize YNOT Mail sending, that's on us once we have DNS access, not blocked on the client anymore
- Client tested the live deploy directly and reported 5 real issues: login signing out on refresh, refresh losing your place in a story, a stray "Came X" typo, tags on the reading page not linking to browse, and (biggest) noticed the site could theoretically leak paid content to guests. Told client only the login bug was covered under the signed SOW (auth) — client explicitly said to fix all of them anyway rather than risk someone else touching the code, confirmed as goodwill/out-of-scope work, not silently absorbed
- Client's own account (`kumokosmos.writing@gmail.com`) promoted to Owner role directly in the production database on request (2026-08-14) — was sitting on the default Free role from when they signed up during testing. Takes effect on next login/refresh, roles are checked fresh each request, not cached in the session token
- Client says they'll message CCBill and send them the site for review once they're free (busy moving as of 2026-08-14) — this is what's expected to unblock the CCBill account details, the main open blocker on Milestone 2
- CCBill review dragged out for weeks (2026-08-18 through 2026-08-31): client emailed/called repeatedly, CCBill kept saying they were busy, slow to respond even after client sent requested info. As of 2026-08-31 client asked about adding Segpay as a backup processor in case CCBill keeps stalling
- Segpay researched directly (not assumed): they offer two integration paths — a hosted checkout page (card data never touches our server, same PCI-light model as CCBill's FlexForms) and a raw XML gateway (requires our server to handle actual card numbers, much heavier PCI burden). Decision: use their hosted page, same shape as the existing CCBill integration. Their webhook equivalent is called "Event Notifications," form-encoded POST, IP-allowlist verified instead of a shared secret — maps cleanly onto the existing isolated `PaymentEvent` architecture, this is additive, not a rebuild
- Quoted client $450 for the Segpay integration (client's own final number, my estimate at their stated $35/hr rate was closer to $350) — explicitly separate from the current milestone, not in original SOW scope. Framed as insurance: if CCBill comes through first, Segpay work isn't needed and nothing's lost
- 2026-09-10: CCBill got back to the client and asked for several additions before they'll approve, client relayed as a list, handled in order:
  1. Human trafficking notice in the footer — added verbatim, live site-wide (footer sits outside all page divs)
  2. Contact page — updated with the client's business address (Beckley, WV), email, phone, and CCBill's own support line
  3. Complaints/Content Removal Policy — CCBill requires this on every page with content. Client chose to just use CCBill's own hosted complaints form link (added to the global footer with `rel="nofollow"`) rather than draft a custom policy page, satisfies the requirement directly through CCBill's own accepted option
  4. Appeals Policy (takedown process for anyone claiming to be depicted in content) — client asked me to draft this myself based on CCBill's stated requirements rather than wait on CCBill's clarification. Wrote a real page (`/pages/appeals`) covering request process, 5-business-day review window, neutral third-party dispute resolution at Kumo's expense, and possible outcomes. Added to the admin static-page editor and linked in the global footer, same visibility requirement as the complaints link
  - All four verified live against the real deployed site after pushing, not just assumed from the diff
- Client asked whether the Substack importer is actually usable — flagged honestly that the backend logic is built and tested (already run once against the real export), but there's no admin panel button yet to trigger it, it currently only runs if manually called via the API. Offered to add that UI piece before launch since the client wants to be able to re-import subscribers on their own repeatedly, not just once — not yet built, pending client's go-ahead on timing
- Project moved into git and pushed to GitHub (`https://github.com/hammadsaleemch345/kumo-kosmos-backend`), so it can be worked on from a second laptop — this had never been version controlled before, everything was edited directly on disk. Repo is **public**: the raw Substack export (`posts.csv`, `email_list.kumokosmos.csv`, `posts/`, ~2785 real subscriber emails plus the client's paid content) was deliberately excluded via `.gitignore` rather than pushed, flagged this risk before pushing rather than assuming it was fine
