# Text-to-SQL Deployment Guide

Complete guide to deploying the Text-to-SQL system on AWS EC2 (Ubuntu 22.04).

---

## Prerequisites

- AWS account with EC2 access
- An OpenAI API key with GPT-4o access
- Olist dataset CSVs (from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce))
- SSH key pair for EC2

---

## Phase 1: Launch EC2 Instance

1. Open the EC2 console → **Launch Instance**
2. **AMI:** Ubuntu Server 22.04 LTS (64-bit x86)
3. **Instance type:** `t3.medium` minimum (2 vCPU, 4 GB RAM) — LangChain + ChromaDB need memory
4. **Storage:** 20 GB gp3
5. **Security Group rules:**
   | Type | Port | Source |
   |------|------|--------|
   | SSH  | 22   | Your IP |
   | HTTP | 80   | 0.0.0.0/0 |
6. Select your SSH key pair → **Launch**
7. Note the **Public IPv4 address**

---

## Phase 2: Connect and Clone

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<PUBLIC_IP>
sudo apt-get install -y git
git clone https://github.com/your-org/text-to-sql.git /opt/text-to-sql
cd /opt/text-to-sql
```

---

## Phase 3: System Setup

```bash
sudo bash infra/setup.sh
```

This installs Python 3.11, Node.js 20, nginx, and system dependencies.

---

## Phase 4: Configure Environment

```bash
export OPENAI_API_KEY="sk-your-actual-key-here"
export APP_DIR=/opt/text-to-sql
sudo bash infra/configure_env.sh
```

Verify the `.env` was created with correct permissions:
```bash
ls -la /opt/text-to-sql/.env  # Should show -rw------- (600)
```

---

## Phase 5: Upload Olist Dataset

Upload the CSV files from your local machine to the EC2 instance:

```bash
# From your LOCAL machine:
scp -i ~/.ssh/your-key.pem \
    olist_orders_dataset.csv \
    olist_order_items_dataset.csv \
    olist_customers_dataset.csv \
    olist_products_dataset.csv \
    olist_sellers_dataset.csv \
    olist_geolocation_dataset.csv \
    olist_order_reviews_dataset.csv \
    product_category_name_translation.csv \
    ubuntu@<PUBLIC_IP>:/opt/text-to-sql/data/raw/
```

Or set `KAGGLE_AUTO_DOWNLOAD=1` in `.env` and install the Kaggle CLI:
```bash
pip install kaggle
# Place ~/.kaggle/kaggle.json (from kaggle.com → Account → API)
```

---

## Phase 6: Install Application

```bash
cd /opt/text-to-sql
bash infra/install_app.sh
```

This will:
- Create Python venv and install packages
- Create DB schema
- Seed the Olist data (takes ~5 min)
- Build the ChromaDB vector index
- Compile the React frontend

---

## Phase 7: Install systemd Service

```bash
sudo cp infra/texttosql.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable texttosql    # Start on boot
sudo systemctl start texttosql
```

Check it's running:
```bash
sudo systemctl status texttosql
sudo journalctl -u texttosql -f    # Follow logs
```

---

## Phase 8: Configure nginx

```bash
sudo cp infra/nginx.conf /etc/nginx/sites-available/texttosql
sudo ln -sf /etc/nginx/sites-available/texttosql /etc/nginx/sites-enabled/texttosql
sudo rm -f /etc/nginx/sites-enabled/default    # Remove default placeholder
sudo nginx -t                                   # Test config
sudo systemctl reload nginx
```

---

## Phase 9: Verify Deployment

```bash
bash infra/verify.sh
```

Expected output:
```
✅ texttosql.service is ACTIVE
✅ /api/health returned HTTP 200
✅ nginx is ACTIVE
✅ nginx config syntax OK
✅ Public endpoint http://X.X.X.X/api/health returned HTTP 200
✅ All checks passed. Stack is healthy.
```

---

## Phase 10: Access the Application

Open your browser at `http://<PUBLIC_IP>/`

- **Frontend:** React app with schema explorer and chat interface
- **API docs:** `http://<PUBLIC_IP>/api/docs` (FastAPI Swagger UI)
- **Health check:** `http://<PUBLIC_IP>/api/health`

---

## Updating the Application

```bash
cd /opt/text-to-sql
git pull origin main
source venv/bin/activate && pip install -r requirements.txt
cd frontend && npm ci && npm run build && cd ..
sudo systemctl restart texttosql
```

## Monitoring

```bash
# Live application logs
sudo journalctl -u texttosql -f

# nginx access logs
sudo tail -f /var/log/nginx/access.log

# Query history (in SQLite)
source venv/bin/activate && source .env
python -c "
from model.database import get_engine
from sqlalchemy import text
with get_engine().connect() as c:
    rows = c.execute(text('SELECT question, latency_ms, created_at FROM query_log ORDER BY created_at DESC LIMIT 20')).fetchall()
    for r in rows: print(r)
"
```
