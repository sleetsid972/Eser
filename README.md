# Eser — Setup Guide

Stripe + Braintree + Shopify card checker.  
Two processes run together on the same VPS:

| Process | File | Role |
|---------|------|------|
| **API** | `autoshopify.py` | Flask server — handles Shopify GraphQL checkouts |
| **Bot** | `bot.py` | Telegram bot — user interface, mass checking, site management |

---

## Requirements

- Python **3.11+**
- Linux VPS (Ubuntu 22.04 recommended) — minimum 2 vCPU / 4 GB RAM
- A Telegram account + Bot Token from [@BotFather](https://t.me/BotFather)
- Telegram API credentials from [my.telegram.org](https://my.telegram.org)

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/sleetsid972/Eser.git
cd Eser
```

---

## Step 2 — Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Edit bot credentials

Open `bot.py` and fill in **your own** values at the top of the file:

```python
BOT_TOKEN     = "YOUR_BOT_TOKEN"          # from @BotFather
API_ID        = 12345678                  # from my.telegram.org
API_HASH      = "your_api_hash_here"      # from my.telegram.org
PHONE_NUMBER  = "+1234567890"             # your Telegram account phone
BOT_OWNER_ID  = 123456789                 # your Telegram user ID (get it from @userinfobot)
```

Also update the API URL so the bot can reach the local Flask server:

```python
SHOPIFY_API_URL = "http://127.0.0.1:5000/shopify"
```

---

## Step 5 — Create required folders

```bash
mkdir -p uploads processed
```

---

## Step 6 — Start the API server

Open a terminal (or tmux/screen pane) and run:

```bash
source venv/bin/activate
gunicorn -c gunicorn.conf.py autoshopify:app
```

The API will listen on `http://127.0.0.1:5000`.  
Verify it is running:

```bash
curl http://127.0.0.1:5000/health
# Expected: {"active":0,"queued":0,"service":"autoshopify-api","status":"ok"}
```

---

## Step 7 — Start the Telegram bot

Open a **second** terminal (or tmux pane) and run:

```bash
source venv/bin/activate
python3 bot.py
```

The first time it runs, Telethon will ask you to enter the **verification code** sent to your Telegram account.  
After that it saves a session file (`checker_session.session`) and you will not need to do this again.

---

## Step 8 — Load Shopify sites (admin only)

1. Create a plain text file with one Shopify store URL per line, e.g. `sites.txt`:
   ```
   https://example-store.myshopify.com
   https://another-shop.com
   ```
2. In the Telegram bot, go to **Admin Panel → Upload Sites** and send the file.
3. Run `/test_sites` in the bot to validate which sites are live and accepting payments.

---

## Step 9 — Verify everything works

In the Telegram bot:

- Send `/health` — shows bot status and API latency.
- Send `/stats` — shows checked / approved / charged counters.
- Send `/workers` — shows worker thread count and queue size.

---

## Running as a background service (optional but recommended)

Create the systemd unit files using the templates in `systemd_units.txt`:

```bash
# Copy the unit blocks from systemd_units.txt into separate files:
sudo nano /etc/systemd/system/eser-api.service   # paste the [eser-api] block
sudo nano /etc/systemd/system/eser-bot.service   # paste the [eser-bot] block

# Enable and start:
sudo systemctl daemon-reload
sudo systemctl enable eser-api eser-bot
sudo systemctl start eser-api
sudo systemctl start eser-bot

# Check status:
sudo systemctl status eser-api
sudo systemctl status eser-bot

# View live logs:
sudo journalctl -u eser-api -f
sudo journalctl -u eser-bot -f
```

The bot service is configured to wait for the API to be healthy before it starts.

---

## Admin commands reference

| Command | Description |
|---------|-------------|
| `/approve <user_id> <duration>` | Grant global access (e.g. `7d`, `1month`, `perm`) |
| `/shopify_approve <user_id> <duration>` | Grant Shopify-only access |
| `/gencode <duration>` | Generate a global access redeem code |
| `/shopify_gencode <duration>` | Generate a Shopify access redeem code |
| `/test_sites` | Validate all uploaded sites via the API |
| `/load_working_sites` | Load previously tested working sites |
| `/stats` | View global check statistics |
| `/topstores` | Top 10 sites ranked by score |
| `/workers` | Worker thread / queue status |
| `/health` | Bot + API health check |
| `/slowmode [secs]` | Set per-card delay (0 = off) |
| `/pricefilter [tier]` | Set price filter (`all`, `highest`, `second`, `low`) |

---

## Price filter tiers

| Tier | Price range | Use case |
|------|-------------|----------|
| `all` | No filter | Check all sites |
| `highest` | $10 – $80 | Best value / lowest friction |
| `second` | $80 – $150 | Premium products |
| `low` | $0 or $300+ | Skip — high risk of out-of-stock or subscription traps |

---

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/shopify?site=URL&cc=CC\|MM\|YYYY\|CVV` | GET | Run a single card check |
| `/health` | GET | API health + active request count |
| `/metrics` | GET | Full metrics (latency, success rate, 429 count) |

---

## File structure

```
Eser/
├── autoshopify.py       # Flask API (Shopify checkout engine)
├── bot.py               # Telegram bot
├── gunicorn.conf.py     # Gunicorn production config
├── requirements.txt     # Python dependencies
├── systemd_units.txt    # Systemd service templates
├── sites.txt            # (created by you) Shopify site list
├── users.json           # Auto-created: user access expiries
├── uploads/             # Temporary card files
└── processed/           # Completed job output files
```
