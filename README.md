# wielen-bot 🚗

A small Telegram bot that watches your **gaspedaal.nl** car searches and pings you
the moment a new listing appears that matches your filters.

gaspedaal is an aggregator (AutoScout24, Marktplaats, ANWB, dealer sites, …), so
one search covers most of the Dutch used-car market.

## How it works

```
watch (make/model/year/…) ─▶ fetcher ─▶ normalize ─▶ filter ─▶ diff vs SQLite ─▶ Telegram
   (you, via /add)          (apify /    (Listing)   (year/    (only new ones)    (you)
                             playwright)             price/km/
                                                     fuel)
```

You create **watches** by chatting with the bot (`/add`). Each watch is a named
filter — make, model, build-year range, max price, max mileage, fuel. Every few
minutes the bot fetches each watch (newest-first), keeps only listings that pass
its filters, compares against what it has already seen, and Telegrams anything
new. The "seen" set is stored in SQLite so restarts don't re-notify you.

## Bot commands

Manage everything from Telegram — no file editing:

| Command | What it does |
|---------|--------------|
| `/add` | Create a watch via a short Q&A (name → make → model → year → price → km → fuel; send `/skip` for any optional step). |
| `/list` | Show all your watches and their filters. |
| `/remove <name>` | Delete a watch by name. |
| `/language` | Switch between English (default) and Dutch. |
| `/start` | Show the welcome / help message. |

> Each watch's name labels its notifications, so you can tell which car a hit is
> for. Want to follow two different cars? Just `/add` twice with different names.

## ⚠️ Read this first: gaspedaal is bot-protected

gaspedaal sits behind DPG Media's **Akamai WAF / Bot Manager**. A plain HTTP
request returns `403 — blocked by WAF`, even with perfect browser headers,
because Akamai fingerprints the TLS handshake and requires a JS challenge.

That's why there are two fetchers — pick one with the `FETCHER` env var:

| `FETCHER`    | Cost | Works from a VPS (datacenter IP)? | Notes |
|--------------|------|-----------------------------------|-------|
| `apify`      | Paid | ✅ Yes | Hosted scraper gets past the WAF for you. Easiest reliable option on a VPS. |
| `playwright` | Free | ⚠️ Usually blocked unless you add a residential proxy | Real headless Chrome. Works great from a **home/Raspberry-Pi (residential) IP**. On a VPS set `PLAYWRIGHT_PROXY` to a cheap residential proxy. |

**Apify is optional and swappable** — it's just one backend behind a common
interface. The bot's logic (filtering, dedup, Telegram) is identical either way.

### Choosing an Apify actor (`APIFY_ACTOR_ID`)

| Actor | Pricing | Best when |
|-------|---------|-----------|
| `unfenced-group/gaspedaal-nl-scraper` *(default)* | **pay-per-result** (~$1.50 / 1,000 results), free WAF bypass | You poll **infrequently** (and stay within Apify's free monthly credit). Set `APIFY_USE_PROXY=false`. |
| `stealth_mode/gaspedaal-cars-search-scraper` | **flat ~$20/mo** + usage | You poll **frequently** — a flat rate beats per-result at high volume. Set `APIFY_USE_PROXY=true`. |

> 💡 **Cost math for pay-per-result:** cost ≈ `searches × MAX_ITEMS_PER_SEARCH ×
> polls-per-month × $1.50/1000`. Polling is what runs up the bill, so for the
> `unfenced-group` actor keep `MAX_ITEMS_PER_SEARCH` small (8–10) and
> `POLL_INTERVAL_SECONDS` generous (1800s+). If you want minute-fresh alerts on
> many searches, the flat-rate `stealth_mode` actor is cheaper overall.

### Which should I use?
- **Home server / Raspberry Pi** → `FETCHER=playwright`, no proxy needed. Free.
- **VPS / cloud, want zero fuss** → `FETCHER=apify`.
- **VPS / cloud, want free** → `FETCHER=playwright` + a residential proxy in
  `PLAYWRIGHT_PROXY` (a few €/mo, much cheaper than Apify).

## Setup

### 1. Create your Telegram bot
1. In Telegram, message **@BotFather** → `/newbot` → follow prompts → copy the **token**.
2. Send any message to your new bot (so it can message you back).
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy
   the `"chat":{"id":...}` value — that's your `TELEGRAM_CHAT_ID`.

### 2. Configure
```bash
cp .env.example .env   # fill in tokens + choose FETCHER
```
That's all the file config you need — watches are created later from Telegram.
(`config.yaml` is optional; only for pinning raw gaspedaal URLs — see
`config.example.yaml`.)

### 3. Run with Docker (recommended)
```bash
docker compose up -d --build
docker compose logs -f
```
You'll get a "wielen-bot started" message in Telegram.

### 4. Add your cars
In Telegram, send **`/add`** and answer the prompts (make, model, year, price,
km, fuel — `/skip` any you don't care about). Repeat for each car you want to
follow. Use `/list` to review and `/remove <name>` to delete.

> On the **first** poll of each new watch the bot silently records all current
> listings (so you don't get a burst of dozens of messages). From then on you
> only hear about genuinely new ones. Set `NOTIFY_ON_FIRST_RUN=true` to be told
> about everything currently matching on first run.

## Run locally (without Docker)
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
playwright install chromium        # only needed for FETCHER=playwright
PYTHONPATH=src python -m wielenbot.main
```

## Configuration reference

All runtime config is via environment variables — see **`.env.example`** for the
annotated list. Highlights:

- `FETCHER` — `apify` or `playwright`
- `POLL_INTERVAL_SECONDS` / `POLL_JITTER_SECONDS` — how often to check (default 5 min ±1 min)
- `MAX_ITEMS_PER_SEARCH` — listings pulled per search per cycle (default 25)
- `NOTIFY_ON_FIRST_RUN` — notify about existing listings on cold start (default false)
- `SEND_STATUS_MESSAGES` — send startup + error pings to Telegram (default true)

Watches live in SQLite (`DB_PATH`) and are managed via the bot's `/add`, `/list`,
and `/remove` commands. The optional **`config.yaml`** only holds raw-URL searches
for power users.

## Development
```bash
pip install -r requirements-dev.txt
pytest          # store dedup, notifier filtering, mapping, i18n, watches, commands
```

## Project layout
```
src/wielenbot/
  config.py            env + optional YAML loading
  models.py            Search, Listing, Watch
  watches.py           Watch → gaspedaal URL + client-side filtering + summary
  i18n.py              English/Dutch translations
  store.py             SQLite: SeenStore (dedup) + SettingsStore + WatchStore
  telegram.py          message formatting + Bot API (send + long-poll)
  commands.py          /add wizard, /list, /remove, /language listener
  notifier.py          fetch → filter → diff → notify → persist (per-watch error isolation)
  main.py              poll loop + command-listener thread, graceful shutdown
  fetchers/
    base.py            Fetcher protocol
    mapping.py         tolerant raw-dict → Listing normalization
    apify_fetcher.py   hosted Apify actor backend (per-actor input builders)
    playwright_fetcher.py  free headless-Chrome backend (captures the page's JSON)
```

## Notes & caveats
- Scraping/aggregating gaspedaal is unofficial; respect their terms and keep poll
  intervals reasonable (the default 5 min is gentle).
- The `playwright` fetcher reads the JSON the page itself loads rather than CSS
  selectors. If gaspedaal changes its data shape, `fetchers/mapping.py` is the one
  place to adjust the field names.
