# Silk & Sin — Feature Checklist
## Prototype vs. full build — for developer handoff

This compares the clickable prototype (`silk-and-sin-prototype.html`) against everything the finished site needs — pulled from the working reference doc, the full build conversation, and standard features of comparable platforms (Substack, NHentai) where relevant. Everything in "In Prototype" has real, testable UI behavior — click it and see. Everything in "Missing Altogether" needs to be built from zero; the prototype gives no head start on it.

---

## ✅ IN PROTOTYPE (UI + working front-end logic, no real backend)

### Public site
- 18+ age gate with a "leave" option and cookie-based re-prompt suppression
- Header: live search with tag autocomplete, Tags shortcut, Subscribe + Account buttons, hamburger menu
- Header, footer, and age-gate all now use your real uploaded logo (embedded directly, plus set as the browser favicon) — no longer a placeholder anywhere; footer logo/name is centered on all screen sizes
- Mobile-specific header behavior (single-row layout, autohide on scroll)
- Front page: hero, weekly poll widget, pinned/hot/new-release rows, storefront highlights, editable announcement bar
- Promo banner with live countdown, click-through to Subscribe, auto-hides after expiry
- Catalog: full story grid, popular-tag quick filters, "browse all tags" link
- Sorting: Popular (composite score), Recent, Hot (with Day/Week/Month sub-filter)
- Search/browse: full-text + tag search, autocomplete, tag exclusion syntax (`-tag`)
- Tag cloud page: word-cloud sized by frequency, click-to-narrow filtering
- Reading page: two-tier paywall (guest wall → free-sub wall), climax/views/rereads/favorites stat block, clickable tags, anthology cross-link, related-stories row, commission CTA
- Reader tools: bookmark (saves an actual highlighted passage), favorite, mark-as-read, 4 reading themes (site/dark/light/sepia) that also recolor the background, font-size control
- Anthology auto-membership: tagging a story with an anthology's tag automatically includes it everywhere (catalog badge, product page, climax/story totals, reading-page cross-link)
- Subscription page: **fully dynamic tiers** — Free and Paid are core/locked, but you can add, edit, or delete custom tiers (e.g. Founder) from the admin panel and the public Subscribe page updates immediately, no code changes
- Win-back offer: anyone who has actually cancelled (not just clicking around) sees a "resubscribe for X% off" prompt instead of the trial offer next time they view Subscribe — discount % is admin-editable
- Monthly/annual billing toggle, trial-aware CTA copy, promo discount stacking correctly with trial pricing
- Storefront + product pages (anthologies, merch)
- Commission page: price/length tiers, pacing/detail selector, testimonials sidebar, request form
- Account page: Billing, Bookmarks, Favorites tabs; Admin tab (role-gated, invisible to non-staff)
- Cancel-subscription flow with retention offer modal

### Admin panel (account → Admin tab, staff roles only)
- **Preview site as** control built into the real Admin tab itself — separate from the floating test-only role switcher, this is meant to survive into the real site so you (or any admin/owner) can see exactly what a guest/free/paid reader sees without logging out. Fixed since the last version: previewing a lower role no longer hides your own Admin tab or any real permission — content-gating simulates the picked role, but your actual access stays intact, with a status line confirming preview is on.
- **Tiers management**: add/edit/delete subscription tiers beyond Free and Paid (e.g. a Founder tier at a custom price with its own perks) — the public Subscribe page renders whatever's active, live, with every tier (including custom ones) sharing the same monthly/annual toggle and card styling, no special "custom" labeling
- Dashboard: subscriber/revenue stat cards, growth chart with series (paid/free/trial) and period (7d/30d/90d/1y) toggles
- Posts: full table sortable by climax, views, rereads, favorites, bookmarks, paid/free subs, release date; working Edit/Pin/Delete
- Post editor: rich-text toolbar (bold, italic, headers, dividers, links), Google-Docs-safe paste (keeps bold/italic, strips fonts/colors/spacing), draggable free-wall/paid-wall markers, cover image upload with live preview, CTA/tag-list templates, sticky toolbar, autosave indicator, working Publish/Save Draft/Schedule
- Subscribers: paid/free lists with working gift, cancel, remove, and move-between-tiers actions; live search; **real CSV export (downloads an actual file) and CSV import (reads a real file and adds rows)**
- Gifts & Discounts: create/deactivate discount codes, send gift subscriptions (1 week/month/3 months/year/infinite) — all reflected in real lists
- Polls: build a concept question + a variant sub-poll per concept option, launched simultaneously; multi-select (approval-style) voting; automatic winner computation per question; paid-vote-weight setting with plain-English explanation; auto-close on a set duration *and* a manual "test close now" button; results show unique-voter counts (not inflated by multi-select) plus paid/free vote split
- Storefront: create/edit/delete items, per-item image upload
- Site Settings: banner text/countdown/on-off, announcement text, logo/favicon upload (real, functional), About/FAQ/ToS inline editor, win-back discount %, Google Analytics measurement ID field (placeholder — see Missing section)
- Basic SEO scaffolding: per-page browser tab title, meta description, and Open Graph tags now update dynamically as you navigate (see Missing section for what this doesn't cover)
- Team: promote/revoke admin access, with promotion strictly limited to the Owner role (regular admins can't create other admins)
- Toast notifications and custom confirm/edit dialogs throughout (built to route around a native-dialog reliability issue found during testing)

### Testing/dev tools (not for production — strip before launch)
- Role switcher (Guest/Free/Paid/Admin/Owner) to preview any access level instantly
- Mobile/Desktop viewport toggle
- "Owns Anthology II" checkbox to test purchase-unlock behavior

---

## ❌ MISSING ALTOGETHER (no code exists — full build required)

### Core infrastructure
- **Real user accounts** — signup, login, logout, password reset, session/auth tokens. Right now "logging in" is a dropdown that pretends.
- **Real database** — every list (subscribers, stories, polls, bookmarks, discount codes) lives in browser memory and vanishes on refresh. Nothing persists.
- **Payment processing (CCBill/Segpay)** — no checkout, no webhook handling, no real billing cycles. Every "Subscribe"/"Buy now" button is a placeholder.
- **Email sending (YNOT Mail or equivalent)** — no post notifications, no segmented sends, no transactional email (password reset, receipts) of any kind.
  - **Post notifications**: Send new story alerts to free/paid subscribers (segmented by tier, configurable preview length)
  - **Transactional emails**: Password reset, purchase receipt, subscription confirmation
  - **Trial/engagement**: Trial-expiration reminders (day 1, day 5, day 6)
  - **Win-back campaigns**: Resubscription offer emails to churned users (discount % is admin-editable)
  - **Bulk campaigns**: Admin-initiated announcements to specific segments (all paid, all free, by tag interest, etc.)
  - **Double opt-in**: Email confirmation for new signups
- **File/image hosting** — uploads in the prototype are browser-only previews (base64), never actually stored or served anywhere.

### Content & discovery
- Real full-text search (current search is a client-side array scan — fine at 12 stories, breaks at scale)
- **Real SEO** — the prototype now updates page title/meta description/OG tags client-side as a starting point, but that's not enough on its own: crawlers need server-rendered tags (not JS-injected), plus sitemap.xml, robots.txt, structured data (schema.org), and per-story OG images
- **Real Google Analytics** — there's a field in Site Settings for a measurement ID now, but it's a placeholder; nothing is actually tracked until a dev wires up the real script
- RSS feed *(this one's excluded on purpose per your spec, not an oversight — flagging for completeness only)*

### Migrating in existing data
- **Substack content import** — flagging this one clearly: Substack doesn't offer a public API for pulling post content and engagement stats out programmatically. Manual path: creator will export posts from Substack as a ZIP, manually upload cover images to CDN, and paste content into site's post editor. Not automated. Estimated effort: ~2-4 hours per 50 posts depending on formatting cleanup needed.
- **Substack subscriber list import** — creator will export free subscriber list from Substack as CSV. **Important note:** Substack does NOT export paid subscriber data (those relationships live only in Substack's billing system and are legally restricted). The CSV importer (Admin → Subscribers) reads `name,email,tier` format. Dev needs to handle cases where imported subs are marked "free" and may need manual tier-reassignment for anyone who was previously paid on Substack but is now migrating to the new site.
- General subscriber CSV export/import *is* built and working in the prototype (see above) — it's specifically the Substack-shaped import that still needs real mapping work.

### Business features — resolved or still needed

**Resolved (custom tiers now handle these):**
- ~~Founder tier~~ — no longer a separate missing item. The new Tiers system in Admin lets you create this (or any custom tier) yourself, right now, in the prototype.
- ~~Fan art contest~~ — removed from scope per your last note, no longer tracked here.
- ~~"Resub for a free month" offer~~ — superseded by the win-back discount feature, now built.

**Still needed:**
- **Founder tier name credits** — active Founder tier members' names automatically appear as a credits line at the end of every story (e.g., "✦ Founder members this month: [Name1], [Name2], [Name3]"). On tier non-renewal, member's name auto-removes from all posts. Backend needs template logic to render this dynamically per-post based on current active Founder subscribers. Names reset monthly (so it shows "this month" not lifetime).
- **Launch promo setup** — ability to configure a limited-time first-month discount (e.g., $15 instead of $20) with an expiration date and auto-disable after launch period ends. Discount system exists in Admin, but launch-specific application (banner, CTA copy, tracking which users are launch-discount cohorts) needs scoping.

### Trust, safety & compliance
- Cookie consent banner (if you're subject to GDPR/CCPA)
- Real Terms of Service / Privacy Policy legal text (the prototype's About/FAQ/ToS are editable placeholders, not counsel-reviewed policy)
- CAN-SPAM-compliant one-click unsubscribe in real emails
- Rate limiting / bot protection on forms (commission requests, discount codes, etc.)
- Data export/deletion tooling if required by your users' jurisdictions

### Engineering baseline
- Automated/persistent analytics (views, rereads, favorites are session-only right now — they reset for every visitor, not tracked per real person)
- Error handling — no real 404 page, no error boundaries, no logging
- Accessibility pass (screen reader support, ARIA labels, keyboard navigation — untested and likely incomplete)
- Cross-browser/device QA (built and reasoned about, never verified on real devices/browsers)
- Performance work (image optimization, lazy loading, caching, CDN)
- Backups / disaster recovery
- **Multi-processor support** — infrastructure to support CCBill as primary processor, with documented path for Segpay/Epoch as backup processors if needed later. (Nice-to-have architecture note; not urgent for launch but worth scoping to avoid processor lock-in.)

---

## How to use this with your developer

Everything in the top section ("IN PROTOTYPE") is a **behavior spec** — "this is exactly what should happen when a user does X." Nothing in that section is production code; treat all of it as reference, not a starting codebase, especially anything touching auth, payments, or data storage. Everything in the bottom section ("MISSING ALTOGETHER") is scope they should estimate and build from scratch.

**How to present this:**
1. Share this document + the working `silk-and-sin-prototype.html` file together
2. Tell them: "The prototype is a clickable behavior spec. Everything in 'IN PROTOTYPE' should work exactly like it does when you click through it."
3. Walk through the prototype together, pointing out the features you care about most
4. Use this checklist to set scope and timeline expectations

---

## Developer Kickoff Questions

Before the developer starts work, get clarity on these:

1. **Payment processor onboarding**: Will you handle CCBill account setup and sandbox testing, or should the creator set up a CCBill account first and provide API keys?

2. **Email service setup**: Same question for YNOT Mail (or equivalent) account setup and API key configuration.

3. **File hosting**: Where should user uploads (covers, profile images) be stored? (Options: AWS S3, Cloudinary, self-hosted, etc.) Who manages CDN setup?

4. **Substack migration logistics**: For the manual post migration, will you provide a template/tool to ease the copy-paste process, or is the creator handling all content reformatting?

5. **Launch timeline**: If you're hired in [specific month], what's your realistic launch date? Will the site be ready before or after the creator's West Virginia move (Aug 15, 2026)?

6. **Post-launch support**: What's included in your scope post-launch vs. what's billed separately? (E.g., bug fixes, feature tweaks, server maintenance, etc.)

7. **Analytics integration**: Will you handle Google Analytics setup, or just provide the field to paste in a measurement ID?

8. **Subscriber data backups**: How often should the site automatically back up the subscriber database? What's the recovery procedure if data is lost?
