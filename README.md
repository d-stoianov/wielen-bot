# wielen-bot 🚗

A small Telegram bot that watches your **gaspedaal.nl** car searches and pings you
the moment a new listing appears that matches your filters.

gaspedaal is an aggregator (AutoScout24, Marktplaats, ANWB, dealer sites, …), so
one search covers most of the Dutch used-car market.

## How it works

```
gaspedaal search URL ──▶ fetcher ──▶ normalize ──▶ diff vs. SQLite ──▶ Telegram
        (you)            (apify /     (Listing)     (only new ones)     (you)
                          playwright)
```

Every few minutes the bot fetches each saved search (sorted newest-first),
compares the listings against what it has already seen, and sends a Telegram
message for anything new. The "seen" set is stored in SQLite so restarts don't
re-notify you.

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
cp .env.example .env            # fill in tokens + choose FETCHER
cp config.example.yaml config.yaml   # add your searches
```

In `config.yaml`, paste gaspedaal search URLs. To build one:
1. Go to https://www.gaspedaal.nl, set your filters (merk/model, prijs, bouwjaar,
   km-stand, brandstof, straal + postcode).
2. **Sort by newest first** — add `srt=df-a` to the URL. This is what makes
   new-listing detection timely.
3. Copy the address-bar URL into `config.yaml`.

### 3. Run with Docker (recommended)
```bash
docker compose up -d --build
docker compose logs -f
```
You should get a "🤖 wielen-bot gestart" message in Telegram.

> On the **first** poll of each search the bot silently records all current
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

Searches live in **`config.yaml`** (`name` + `url` per entry).

## Development
```bash
pip install -r requirements-dev.txt
pytest          # 22 tests covering store dedup, notifier diffing, mapping, formatting, config
```

## Project layout
```
src/wielenbot/
  config.py            env + YAML loading
  models.py            Search, Listing
  store.py             SQLite seen-set (dedup, scoped per search)
  telegram.py          message formatting + Bot API delivery
  notifier.py          fetch → diff → notify → persist (per-search error isolation)
  main.py              poll loop, graceful shutdown
  fetchers/
    base.py            Fetcher protocol
    mapping.py         tolerant raw-dict → Listing normalization
    apify_fetcher.py   hosted Apify actor backend
    playwright_fetcher.py  free headless-Chrome backend (captures the page's JSON)
```

## Notes & caveats
- Scraping/aggregating gaspedaal is unofficial; respect their terms and keep poll
  intervals reasonable (the default 5 min is gentle).
- The `playwright` fetcher reads the JSON the page itself loads rather than CSS
  selectors. If gaspedaal changes its data shape, `fetchers/mapping.py` is the one
  place to adjust the field names.
