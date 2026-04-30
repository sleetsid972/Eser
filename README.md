# Eser — Setup Guide

Stripe + Braintree + Shopify card checker.  
The bot runs as a single process — Shopify checkout is integrated directly into `bot.py`.

| Process | File | Role |
|---------|------|------|
| **Bot** | `bot.py` | Telegram bot — user interface, mass checking, Shopify GraphQL checkout (integrated), site management |

> **Note:** `Autoshopify (1).py` is kept as a legacy reference. The bot no longer calls it — all Shopify checkout logic runs inside `bot.py` via `shopify_checkout_core()`.

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

---

## Step 5 — Create required folders

```bash
mkdir -p uploads processed
```

---

## Step 6 — Start the Telegram bot

```bash
source venv/bin/activate
python3 bot.py
```

The first time it runs, Telethon will ask you to enter the **verification code** sent to your Telegram account.  
After that it saves a session file (`checker_session.session`) and you will not need to do this again.

---

## Step 7 — Load Shopify sites (admin only)

1. Create a plain text file with one Shopify store URL per line, e.g. `sites.txt`:
   ```
   https://example-store.myshopify.com
   https://another-shop.com
   ```
2. In the Telegram bot, go to **Admin Panel → Upload Sites** and send the file.
3. Run `/test_sites` in the bot to validate which sites are live and accepting payments.

---

## Step 8 — Verify everything works

In the Telegram bot:

- Send `/health` — shows bot status, store cache, and price cache stats.
- Send `/stats` — shows checked / approved / charged counters.
- Send `/workers` — shows worker thread count and queue size.

---

## Running as a background service (optional but recommended)

Create the systemd unit file using the template in `systemd_units.txt`:

```bash
sudo nano /etc/systemd/system/eser-bot.service   # paste the [eser-bot] block

# Enable and start:
sudo systemctl daemon-reload
sudo systemctl enable eser-bot
sudo systemctl start eser-bot

# Check status:
sudo systemctl status eser-bot

# View live logs:
sudo journalctl -u eser-bot -f
```

---

## Admin commands reference

| Command | Description |
|---------|-------------|
| `/approve <user_id> <duration>` | Grant global access (e.g. `7d`, `1month`, `perm`) |
| `/shopify_approve <user_id> <duration>` | Grant Shopify-only access |
| `/gencode <duration>` | Generate a global access redeem code |
| `/shopify_gencode <duration>` | Generate a Shopify access redeem code |
| `/test_sites` | Validate all uploaded sites (direct checkout, no external API) |
| `/load_working_sites` | Load previously tested working sites |
| `/stats` | View global check statistics |
| `/topstores` | Top 10 sites ranked by score |
| `/workers` | Worker thread / queue status |
| `/health` | Bot health + store/price cache status |
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

## File structure

```
Eser/
├── Autoshopify (1).py   # Legacy Flask API reference (not used by bot)
├── bot.py               # Telegram bot with integrated Shopify checkout engine
├── gunicorn.conf.py     # Gunicorn config (for legacy API reference only)
├── requirements.txt     # Python dependencies
├── systemd_units.txt    # Systemd service templates
├── sites.txt            # (created by you) Shopify site list
├── users.json           # Auto-created: user access expiries
├── uploads/             # Temporary card files
└── processed/           # Completed job output files
```

