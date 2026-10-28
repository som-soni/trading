# Public app — specification

*Written 25 October 2026. A plan, not a record: nothing here is built yet.*

**In short**

- A **public, read-only copy** of part of the web app, hosted on Vercel as static files: the
  single-page app in a *public mode*, plus daily JSON snapshots of the API responses its pages need.
  No server, nothing writable, nothing that depends on this machine being awake.
- Snapshots are produced by a new **`site` job in the publish layer**, run at the end of each market's
  `close` routine, and deployed with the Vercel CLI from the same job. One front end serves both the
  private app and the public site; the public build only hides and redirects.
- **v1 publishes** Learn (guides, patterns, glossary), a chosen set of research notes, the Markets
  section (Post-market, Breadth, Sectors, Movers, Earnings, Macro) and each strategy's *How it works*
  tab. It does **not** publish per-stock pages, setups, screens, backtest reports, or anything of
  yours (notes, watchlists, TODO, drawings, themes, System).
- Vercel's limits bound the design: a CLI deployment holds at most 15,000 files and 100 MB on the
  Hobby plan (1 GB on Pro). v1 is about 1,100 files; the only large item is Learn's price series,
  which the job trims to the windows the guides draw.
- Five decisions are left open at the end (home page, which research notes, Learn's Yahoo-sourced
  stock series, themes, the Backtests tab). Everything else is specified.

---

## 1. Shape

```
your Mac                                               Vercel (static hosting)
┌────────────────────────────────────────────┐         ┌──────────────────────────────┐
│ close pipeline … postmarket → ingest → site│  CLI    │ index.html, static/*.js|css  │
│   site = render ──► dist/public ──► deploy ├────────►│ api/manifest.json            │
│           (TestClient against server.app)  │         │ api/**.json  (≈1,100 files)  │
└────────────────────────────────────────────┘         └──────────────────────────────┘
```

- **Render** calls the existing FastAPI endpoints in-process (`fastapi.testclient.TestClient` on
  `swing_screener.web.server.app`), so the public site shows exactly what the private app computes,
  from one implementation. It crawls from a few roots (markets, the research list, the strategy list,
  the Learn guides' chart fences) and writes each response to a file; a **manifest** maps every exact
  request URL to its file.
- **Public mode** of the front end is one flag set by the public `index.html`. In that mode `api()`
  resolves a URL through the manifest instead of fetching `/api/...`, every non-GET throws "read-only",
  the section registry drops the private sections, the router sends private routes home, and controls
  marked private are hidden. A URL missing from the manifest renders "Not part of the public site"
  rather than a broken page.
- **Deploy** uploads `dist/public` with `npx vercel deploy --prod --archive=tgz`. The directory is a
  linked Vercel project (`dist/public/.vercel/`, kept across runs, never committed). The token lives in
  `scripts/.env` as `VERCEL_TOKEN`, beside the Postgres credentials.

The data boundary stays where it is: the job reads stored data only (it runs inside
`cache.offline()`); the one network action is the upload, which is why the job is marked `network=True`.

## 2. What is public

| Section | Pages in v1 | Hidden in public mode |
|---|---|---|
| Learn | hub, every topic, every guide, every drawn pattern, Glossary | — |
| Library → Research | the allow-listed notes (§7, decision B) | Notes, TODO; the rest of the research list |
| Markets | Post-market (Summary · Sectors · Stocks), Breadth, Sectors (sector · industry · sub), Movers, Earnings, Macro | Post-market's *Your lists* tab; Sectors' *Themes* level and *New theme*; the *Rebuild* and *wait* polling |
| Strategies | the list, each strategy's *How it works* tab | *Candidates*, *Backtests* (decision E), the *Backtest …* button, archive |
| Header | market selector, ⌘K (pages and Learn only), theme and density, "data through" badge from `meta.json` | stock search, Status link, *Load reports* |

Not in v1, and why — so the list is a decision, not an omission:

| Not published | Reason |
|---|---|
| Chart, Fundamentals, News, VCP boxes, live patterns, stage analysis, S/R and S/D zones | per-stock raw bars from Yahoo (redistribution terms); on-demand compute; 17,000 symbols × files would exceed Vercel's file limit |
| Today, Today's setups, strategy Candidates, Screener picks | entry/stop/target levels published to readers — a research-analyst activity under SEBI's rules in India; the strategies are still being refined (the same reason Learn never cites them) |
| Screens, screen builder, Quality | live queries over the snapshot; saved screens are yours |
| Backtest reports, figures, trades, funnels | 215 runs × tables and 1,545 figures; in-sample results read like verified ones — see decision E |
| Watchlists, Notes, TODO, drawings, themes, quality watch | yours |
| System (Status, Runs, Schedules, Reports archive, Sub-industries) | operational, and the write endpoints behind them |

## 3. Endpoint inventory

Every request a public page makes, with the parameter values the job enumerates. "Files" is the
count the job writes today (both markets); the manifest is the authority at run time.

### 3.1 App shell

| Endpoint | Parameters | Values | Files | Note |
|---|---|---|---|---|
| `GET /api/markets` | — | — | 1 | the market selector, currencies, the index pickers' `indices` |
| *(new)* `api/meta.json` | — | — | 1 | `generated_at`, per market the latest price and post-market dates, the git commit; replaces `/api/status` for the header badge |
| *(new)* `api/manifest.json` | — | — | 1 | `{ "<exact url>": "<file>" }` for every entry below |

### 3.2 Markets

| Endpoint | Parameters | Values | Files | Note |
|---|---|---|---|---|
| `GET /api/postmarket` | `market`, `date?` | latest, then every date in the response's `history` (≤ 400 per market; 72 stored today) | ≈ 146 | the job **removes `watchlists` and `screener`** from each payload (analytics/postmarket.py line 343) and keeps `earnings`; the *Your lists* tab is hidden |
| `GET /api/breadth` | `market` | — | 2 | |
| `GET /api/sectors` | `market`, `level` | `sector`, `industry`, `sub` (`theme` only if decision D says so) | 6 | |
| `GET /api/sectors/group` | `market`, `level`, `group` | every `groups[].name` of each level's response | ≈ 500 | ≈ 11 sectors + ≈ 135 industries + the sub-industries per market |
| `GET /api/movers` | `market`, `period`, `universe`, `limit` | `period` ∈ `MOVER_PERIODS` (1D 1W 1M 3M 6M YTD 1Y), `universe` ∈ liquid, all, `limit=25` | 28 | the page's *US + India* view is two requests |
| `GET /api/earnings-season` | `market`, `basis`, `quarter?` | `basis` ∈ yoy, qoq; latest, then every `quarters[].quarter` of the latest response | ≈ 80 | |
| `GET /api/macro` | `market` | — | 2 | |
| `GET /api/macro/analysis` | `market` | — | 2 | the Today-style tiles reused on Macro |
| `GET /api/rates` | `market` | — | 2 | |
| `GET /api/indicators` | `market` | — | 2 | |
| `GET /api/flows` | — | — | 1 | India only; the page asks without a market |
| `GET /api/fpi-sectors` | `market`, `fortnights` | the page sends only `market` (server default 24) | 2 | |
| `GET /api/prices` | `market`, `symbol`, `tf=D`, `bars=100000` | every `indices[].symbol` of `/api/markets`, for Macro's *compare with an index* picker | ≈ 20 | index series only; see §5 for the trim |

### 3.3 Library

| Endpoint | Parameters | Values | Files | Note |
|---|---|---|---|---|
| `GET /api/reports?kind=research` | `kind=research` | — | 1 | **filtered** to the allow-list (§7 B): learn pages, the Research page and ⌘K all read it |
| `GET /api/reports/{id}` | `id` | every id in the filtered list (90 guides + the allowed notes) | ≈ 95 | markdown; `tables` is empty for research docs |
| `GET /api/breadth-series` | `market`, `field` | from the guides' fences: `us:breadth.pct50`, `.hl`, `.adline`; `india:breadth.pct50` | 4 | |
| `GET /api/fund-series` | `market`, `symbol`, `field` | 24 refs in the guides (`fund.<symbol>.<field>`) | 24 | filings data (SEC, NSE) |
| `GET /api/group-rs-series` | `market`, `level`, `grp` | 8 refs in the guides (`grs.<level>.<group>`) | 8 | |
| `GET /api/prices` | `market`, `symbol`, `tf=D`, `bars=100000` | 116 refs in the guides: indices and macro series (`^NSEI`, `NIFTY50_TR`, `DXY`, `GOLD`, `CASH_YIELD` …) and about 70 individual stocks | 116 | **decision C**: the stocks are Yahoo bars |

The fence references are found the way the front end finds them: parse every ```` ```series ````
block of every published document, take each `line:` expression's `market:symbol` references
(before any `@transform`), over the allow-listed documents only (the `app-guide-*` manual has one fence but is not published). Patterns (```` ```pattern ````)
and payoff diagrams (```` ```payoff ````) are drawn client-side from `learn.js` and need no data.

### 3.4 Strategies

| Endpoint | Parameters | Values | Files | Note |
|---|---|---|---|---|
| `GET /api/strategies` | — | — | 1 | `backtests` counts stay (they are numbers) |
| `GET /api/taxonomy` | — | — | 1 | |
| `GET /api/strategies/{key}` | `key` | every key of the list (≈ 20) | ≈ 20 | the payload's `backtests[]`, `versions`, `stages` and `screens` ride along; only the *How it works* tab is shown (decision E) |

### 3.5 Never published — the job refuses to write these

`/api/status`, `/api/status/run/*`, `/api/queue*`, `/api/jobs/*`, `/api/worker/*`, `/api/schedules*`,
`/api/wait`, `/api/ingest`, `/api/notes*`, `/api/todo*`, `/api/watchlists*`, `/api/drawings/*`,
`/api/quality*`, `/api/screens*`, `/api/screen-fields`, `/api/setups*`, `/api/screening/*`,
`/api/portfolio-selection/*`, `/api/subindustries*`, `/api/themes*` (write), `/api/symbols`,
`/api/symbol-context`, `/api/company*`, `/api/fundamentals*`, `/api/news/*`, `/api/vcp/*`,
`/api/patterns*`, `/api/stage-analysis/*`, `/api/sr-levels/*`, `/api/sd-zones/*`, `/api/trade-runs`,
`/api/reports` of any kind but `research`, `/api/reports/*/figures|tables|funnel|trade-anatomy|archive`.
A test asserts that no manifest URL matches this list (§8).

**Total today: about 1,100 files.** Growth is slow: one post-market file per market per trading day,
a handful per earnings quarter.

## 4. `dist/public` layout

```
dist/public/
  index.html                  public build: data-public="1", asset URLs stamped with a content hash
  vercel.json                 headers (§6); no build step, no rewrites (hash routing)
  static/                     app.js, style.css, learn.js, studies.js, drawings.js, glossary.js, vendor/
  api/
    manifest.json             exact request URL -> file path, for every file below
    meta.json                 generated_at, per-market data dates, commit
    markets.json
    postmarket/us/latest.json, postmarket/us/2026-10-23.json, …
    breadth/us.json
    sectors/us/industry.json, sectors/us/industry/<slug>.json, …
    movers/us/1D-liquid.json, …
    earnings/us/yoy-latest.json, earnings/us/yoy-2026-06-30.json, …
    macro/us.json, macro/analysis/us.json, rates/us.json, indicators/us.json, flows.json, fpi-sectors/us.json
    prices/us/<slug>.json                 (index series for Macro; guide series)
    series/breadth/us-pct50.json, series/fund/us-NVDA-eps_g.json, series/grs/us-industry-<slug>.json
    research/index.json, research/<id>.json
    strategies/index.json, strategies/taxonomy.json, strategies/<key>.json
  .vercel/                    project link, written once by `vercel link`; never committed
```

File names are for humans; the front end never derives them. It looks the exact URL up in the
manifest, so a renamed file or a changed query order cannot break a page, and a request the job did
not publish fails with one clear message instead of a 404 inside a chart.

`dist/` is added to `.gitignore` next to `reports/` and `logs/`.

## 5. Size and the Vercel limits

| Limit (Vercel CLI deployment) | Hobby | Pro | v1 today |
|---|---|---|---|
| files | 15,000 | 15,000 | ≈ 1,100 |
| upload size | 100 MB | 1 GB | see below |

Everything but the price series is small (a few MB in total). A full stored history for one symbol is
up to 600 KB of candles, so 136 untrimmed series could be 50–80 MB — too close to the Hobby cap. The
job therefore **trims each series to the union of the windows the fences draw it in**, keeping 260
bars before the earliest `from` for the longest transform warm-up (`@sma200`, `@ema`, `@rsi14` …),
and drops `high`/`low`/`volume` unless a fence uses a transform that needs them (`@atr`, `@vol`,
`@rvol`, `@dist`). Expected result: under 10 MB. Macro's index overlays keep their full history: they
are about 20 index series, not stocks.

The job **fails before deploying** when the rendered tree exceeds 10,000 files or 90 MB
(`SITE_MAX_FILES`, `SITE_MAX_BYTES` in the module), naming the largest directories, so a quiet growth
never turns into a failed upload at 23:00.

## 6. Vercel

- **Project**: one Vercel project, Hobby plan (personal, non-commercial — a free educational site
  qualifies; anything paid or sponsored means Pro). Linked once by hand:
  `cd dist/public && npx vercel link`. The CLI is run through `npx vercel@<pinned>`; Node 24 is
  installed, the CLI is not.
- **Deploy**: `npx vercel deploy --prod --yes --archive=tgz --token "$VERCEL_TOKEN"` from
  `dist/public`. Prebuilt output is not needed: a directory with no framework is a static deployment.
- **`vercel.json`**:
  - `api/**`: `Cache-Control: public, max-age=300, must-revalidate` — a reader never sees yesterday's
    page more than five minutes after a run;
  - `static/**`: `Cache-Control: public, max-age=31536000, immutable` — asset URLs carry a content
    hash in the public build (the private server stamps mtimes instead);
  - `index.html`: `no-cache`;
  - `cleanUrls: false`, no rewrites (the app routes on `#/`).
- **Domain**: Vercel's default URL first; a custom domain is a later, independent step.
- **Secrets**: `VERCEL_TOKEN` in `scripts/.env` (already gitignored). Nothing else is needed; the
  project id is in `dist/public/.vercel/project.json`.

## 7. The job

```python
# jobs/registry.py — publish layer
Job("site", "publish",
    "public site: render the public pages' data to dist/public and deploy it to Vercel",
    "daily", True, _site, per_market=False, after=("postmarket", "sectors", "breadth", "ingest"),
    expand=_site_steps)      # render → check → deploy, each its own step on System → Runs
```

| Aspect | Decision |
|---|---|
| Module | `scripts/swing_screener/web/public.py`: `render(out_dir) -> Manifest`, `check(out_dir)`, `deploy(out_dir)`; the registry function is a thin wrapper, as `_ingest` is |
| Options | `--no-deploy` (render and check only, for a local look with `python -m http.server`), `--out DIR` (default `dist/public`), `--force` (ignore the "nothing changed" skip) |
| Skip rule | with `only_new` (as `report` and `ingest` use it): skip when no `postmarket`, `sectors`, `breadth`, `ingest` or `group_research` step finished since the last successful `site` run |
| Pipelines | appended to `close` after `ingest` (so each market's close publishes that market's day) and to `monthly` after `ingest` (the group-strength study and re-classification) |
| Lane | main (it uploads; `FAST_JOBS` is for seconds-long stored-data jobs). Not in `RESEARCH_JOBS`. `CLASH_EXEMPT` gains `site` for the same reason `ingest` is there: a close routine ending in it must not wait behind a backtest that also ends in `ingest`. Then run `tests.test_job_lanes` |
| Data rule | `render` runs inside `cache.offline()` and reads through the same endpoints the private app uses; it downloads nothing. The endpoints that *could* start a top-up in a subprocess (`breadth`, `screens`) are called with top-ups disabled for the duration — a public snapshot must never trigger work |
| Determinism | files are written sorted, JSON with sorted keys and no timestamps except `meta.json`, so a re-render with unchanged data is byte-identical and the step can report "no change" |
| Step detail | `1,104 files · 8.2 MB · 2 markets · post-market 2026-10-23 / 2026-10-23 · deployed https://…vercel.app` |
| Failure | a 5xx from any endpoint fails the render step (the previous deployment stays live); the check step fails on the size guard or a forbidden URL; a deploy failure is reported with the CLI's last lines |

Allow-list for research notes (`PUBLIC_RESEARCH` in `web/public.py`, decision B):
every `learn-*`, plus `chart-pattern-spec`, `minervini-backtest-spec`, `index-investing-research`,
`group-strength-study`. Excluded by default: `README`, the `app-guide-*` manual (names pages the public
site does not have), `momentum-trend-research` and the `minervini-spec-sensitivity-*` ledgers (the
owner's backtests), `sector-analysis-playbook` (your routine), `sector-taxonomy`, `fno-scope`,
`snapshot-freshness`, `selection-vs-drag`, `crwd-gap-studies`, and this document.

## 8. The public build of the front end

One front end, one flag. The public `index.html` sets `<html data-public="1">`; everything else reads
`PUBLIC` from it.

| Where | Change |
|---|---|
| `api()` / `_fetchJson` | in public mode: a non-GET throws `read-only`; a GET looks the exact URL up in `api/manifest.json` (loaded once, before the first page) and fetches the file; a miss throws `not part of the public site`, which pages already render as their empty state |
| `SECTIONS` | filtered by a `PUBLIC_SECTIONS` set: Learn first, then Markets, Strategies, Research. Today, Chart, Watchlists, Notes, System are dropped, so ⌘K, Alt+N and the nav never show them |
| `route()` | a route outside the public set goes home. Home is decision A |
| `PM_TABS`, Sectors levels | *Your lists* and *Themes* removed in public mode |
| Controls marked `data-private` | *Backtest …*, archive, *Rebuild*, *New theme*, *Load reports*, *+ note*, quality *Watch*: one CSS rule hides them; the handlers never run because every write throws |
| Header | `refreshStatusDot` reads `api/meta.json`; the badge links nowhere; `/api/wait` polling and `staleBanner` are off |
| ⌘K | pages and Learn items only; the symbol search branch is skipped |
| Footer | one line on every page: data sources, "educational, not advice", and the generated time from `meta.json` |
| Build | the job copies `static/` and writes `index.html` with content-hashed asset URLs; no bundler |

Everything above is additive and guarded by the flag, so the private app does not change.

## 9. Tests

- `tests/test_public_site.py` (new): renders into a temporary directory with `TestClient` and asserts
  (1) every manifest URL returned 200 and parses as JSON; (2) no manifest URL matches the forbidden list
  of §3.5; (3) no post-market file contains `watchlists` or `screener`; (4) the research index holds
  only allow-listed names; (5) the size guard trips on a deliberately oversized tree; (6) every
  `line:` reference in every published fence has a manifest entry — the check that catches a new
  guide's chart before a reader does.
- `tests/test_job_lanes.py` — after the registry change.
- `tests/test_learn_guides.py` — unchanged, still the gate for a new guide.
- By hand, once: `python -m jobs run site --no-deploy`, then `python -m http.server -d dist/public`
  and open every public section in both markets, light and dark.

## 10. Order of work

1. Public mode in the front end (§8), testable against a hand-written manifest.
2. `web/public.py`: render, manifest, trims, checks; the test file.
3. The job, pipelines, lanes; README and `scripts/README.md` job tables; a line in `CLAUDE.md`'s jobs
   paragraph that the public site is a publish-layer job.
4. Vercel: link, token, first deploy by hand, then from the job; `vercel.json`.
5. Revisit the "later" tier with the site live: backtests (decision E), then per-stock pages only if
   the data question is settled.

## 11. Decisions to take

| | Question | Default if you say nothing |
|---|---|---|
| A | Home page: the Learn hub ("Start here"), or Post-market? | Learn hub |
| B | Which research notes beyond the guides (§7 allow-list)? | the four named |
| C | Learn's ≈ 70 individual-stock series are Yahoo daily bars. Publish them trimmed to the guides' windows, rebase them to 100 (shape only, no prices), or swap those examples for index and ETF series? | trimmed, as the guides draw them — but this is the data-terms exposure, so decide it knowingly |
| D | Sectors' *Themes* level: your theses, read-only — publish or hide? | hide |
| E | Strategies' *Backtests* tab lists runs with stage labels; the report pages behind it are not published. Show the list (links dead-ended), hide the tab, or publish the report pages too (215 runs, 1,545 figures, within Pro's 1 GB but not Hobby's 100 MB)? | hide the tab; the *How it works* head still shows the measured outcome and its stage |
