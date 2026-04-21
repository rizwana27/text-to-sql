# 🧠 Text-to-SQL

💬 Ask a question in plain English. 🔍 Get back a SQL query and real results from the database. No SQL knowledge required.

> **Audience:** No prior knowledge of LLMs or vector databases is assumed.

---

## 📚 Table of Contents

1. [🤔 What Does This Project Do?](#1-what-does-this-project-do)
2. [😬 The Problem With "Typical" Text-to-SQL](#2-the-problem-with-typical-text-to-sql)
3. [🛠️ How This Project Solves It](#3-how-this-project-solves-it)
4. [🏗️ High-Level Architecture](#4-high-level-architecture)
5. [🔄 Step-by-Step: How a Query Works](#5-step-by-step-how-a-query-works)
6. [✅ What It Can (and Cannot) Do](#6-what-it-can-and-cannot-do)
7. [📁 Project Structure](#7-project-structure)
8. [🗄️ Database Schema](#8-database-schema)
9. [🚀 Quick Start](#9-quick-start)
10. [⚙️ Environment Variables](#10-environment-variables)

---

## 1. 🤔 What Does This Project Do?

This system lets a non-technical user type a question like:

> *"What are the top 10 product categories by revenue this year?"*

…and automatically:

1. 🗺️ Figures out which database tables are relevant to the question.
2. ✍️ Asks an LLM (GPT-4o) to write the correct SQL query.
3. ⚡ Runs that SQL against a real database (Olist Brazilian E-Commerce dataset).
4. 📊 Returns the results in a clean table in the browser.

The underlying database is a **star-schema** data warehouse built on the [Olist public dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), which contains real Brazilian e-commerce orders, products, sellers, customers, and reviews.

---

## 2. 😬 The Problem With "Typical" Text-to-SQL

When someone first tries to build a text-to-SQL system, the obvious approach is usually:

> *"I'll just paste the entire database schema into the LLM prompt and ask it to write a query."*

This works fine for toy databases with 3–4 tables. In the real world, it breaks down fast 💥:

| Problem | Why it happens |
|---|---|
| 🌊 **Context window overflow** | A real warehouse can have 50–200 tables. The full schema — table names, column names, types, foreign keys — can easily exceed the LLM's context limit (even GPT-4o's 128k tokens). |
| 📢 **Noise drowns out signal** | Even if it fits, flooding the prompt with irrelevant tables confuses the model. It might join to the wrong table or use the wrong column because it's overwhelmed. |
| 🔍 **Business meaning is lost** | Column names like `order_total_usd` or `is_active_member` don't tell the LLM *how* to use them correctly. Should `order_total_usd` be summed or averaged? Should you filter on `order_status = 'delivered'` first? The schema alone doesn't say. |
| 👻 **Hallucinated SQL** | Without enough context, the LLM invents column names or table relationships that don't exist, producing queries that fail at runtime. |
| 🚨 **No safety guardrails** | A naive implementation has no check to stop the LLM from generating `DELETE` or `DROP TABLE` statements if the user's question is phrased ambiguously. |

**This project solves all of these problems. 🎯**

---

## 3. 🛠️ How This Project Solves It

Instead of dumping the whole schema into the prompt, we use three key techniques:

### 📖 Technique 1: Semantic Layer (the "data dictionary")

Every table and column is annotated with business-friendly descriptions in [`agent/semantic_layer.py`](agent/semantic_layer.py). For example:

```
order_total_usd: "Final post-tax revenue in USD for this line item.
                  Always use this for GMV calculations.
                  Never use freight_value_usd as a revenue proxy."
```

This tells the LLM *how* to use each column, not just *what type* it is. Think of it as a data dictionary that the LLM reads before writing SQL. 📚

### 🔎 Technique 2: RAG — Retrieval-Augmented Generation

Instead of sending all table descriptions at once, we:

1. **At startup:** Embed every table description into a vector database (ChromaDB) using OpenAI embeddings. Each table becomes a point in high-dimensional space. 📌
2. **At query time:** Embed the user's question using the same embedding model. Find the 3 most *semantically similar* table descriptions using cosine similarity. Inject *only those 3 tables* into the LLM prompt. 🎯

The user asks about "revenue by category" → we retrieve `fact_orders` and `dim_products` → the LLM only sees those two tables → cleaner, more accurate SQL. ✨

### 💡 Technique 3: Few-Shot Examples

The prompt includes curated question→SQL example pairs (stored in [`agent/few_shot_examples.yaml`](agent/few_shot_examples.yaml)). These teach the LLM the exact SQL dialect, join patterns, and aggregation idioms expected for *this specific database*, acting as in-context learning.

### 🛡️ Technique 4: HITL Safety Guard

Before any SQL is executed, a Human-In-The-Loop (HITL) guard scans for dangerous keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, etc.). If found, execution is blocked and the user must explicitly type `CONFIRM` in a modal before anything runs. Pure `SELECT` queries pass through automatically. 🔒

---

## 4. 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (React)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  ChatWindow  │  │  SqlDisplay  │  │   ResultsTable    │  │
│  │ (ask a Q)    │  │ (show SQL)   │  │ (show rows)       │  │
│  └──────┬───────┘  └──────────────┘  └───────────────────┘  │
│         │ POST /query                                         │
└─────────┼───────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────┐
│                    FastAPI Backend (Python)                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   sql_chain.py (LCEL pipeline)        │   │
│  │                                                       │   │
│  │  Question                                             │   │
│  │     │                                                 │   │
│  │     ▼                                                 │   │
│  │  [1] retriever.py ──► ChromaDB (vector store)        │   │
│  │     │   (embed question, find top-3 relevant tables)  │   │
│  │     ▼                                                 │   │
│  │  [2] Load few_shot_examples.yaml                      │   │
│  │     │                                                 │   │
│  │     ▼                                                 │   │
│  │  [3] Build ChatPromptTemplate                         │   │
│  │     │   (schema + examples + question)               │   │
│  │     ▼                                                 │   │
│  │  [4] GPT-4o (temperature=0) ◄── OpenAI API           │   │
│  │     │   (generate SQL)                               │   │
│  │     ▼                                                 │   │
│  │  [5] hitl_guard.py                                    │   │
│  │     │   (block writes, require human approval)       │   │
│  │     ▼                                                 │   │
│  │  [6] Execute SQL ──► SQLite / PostgreSQL              │   │
│  │     │                                                 │   │
│  │     ▼                                                 │   │
│  │  [7] Log to query_log table                           │   │
│  │     │                                                 │   │
│  │     ▼                                                 │   │
│  │  Return {sql, results, latency_ms}                    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────┐
│         ChromaDB (vector store)       │
│  Table descriptions stored as vectors │
│  Persisted to ./chroma_store/         │
└──────────────────────────────────────┘
          │
┌─────────▼────────────────────────────┐
│     SQLite (./data/olist.db)          │
│  fact_orders, dim_users,              │
│  dim_products, dim_sellers,           │
│  dim_geography, dim_reviews,          │
│  query_log                            │
└──────────────────────────────────────┘
```

---

## 5. 🔄 Step-by-Step: How a Query Works

Here is exactly what happens when a user types *"Which states have the most canceled orders?"* and hits Enter:

**Step 1 → Embed the question 🔢**
The question is converted to a 1536-dimension vector using OpenAI's `text-embedding-3-small` model.

**Step 2 → Retrieve relevant schema (RAG) 🗂️**
ChromaDB compares the question vector against all stored table description vectors and returns the 3 closest matches — in this case `fact_orders` (has `order_status`) and `dim_users` (has `state`).

**Step 3 → Build the prompt 📝**
A `ChatPromptTemplate` is assembled with:
- A system message containing the retrieved table schemas and a few Q→SQL examples.
- A user message containing the question.

**Step 4 → Ask GPT-4o 🤖**
The prompt is sent to GPT-4o with `temperature=0` (fully deterministic — no creative variation in SQL). The model returns a raw SQL string.

**Step 5 → Clean the SQL 🧹**
A small regex function strips any markdown code fences (` ```sql `) or stray labels that the model might have included.

**Step 6 → HITL safety check 🛡️**
The SQL is scanned for dangerous keywords. This is a `SELECT` query, so it passes automatically.

**Step 7 → Execute the SQL ⚡**
The query runs against the SQLite database. A `LIMIT 1000` clause is injected automatically if not already present, so the response stays manageable.

**Step 8 → Log and return 📦**
The question, generated SQL, latency, and tables used are written to the `query_log` table for observability. The API returns `{sql, results, latency_ms}` to the frontend.

**Step 9 → Display in the browser 🖥️**
React renders the SQL in a syntax-highlighted box and the results as a pageable table.

---

## 6. ✅ What It Can (and Cannot) Do

### ✅ Can Do

- 💬 Answer any analytical question about the Olist e-commerce dataset in plain English.
- 💰 Revenue analysis: total, by category, by seller, by month, by state.
- 👥 Customer analysis: active members, geographic distribution, top spenders, cohorts.
- 🏪 Seller analysis: rankings, geographic distribution, freight costs.
- 📦 Order analysis: status breakdown, cancellation rates, monthly trends.
- ⭐ Review/NPS analysis: average scores by category, complaint rates.
- 🔀 Complex queries: multi-table joins, CTEs (`WITH` clauses), window functions.
- 🗣️ Explain what SQL it generated and why.
- 🚧 Block dangerous write operations and ask for human confirmation.

### ❌ Cannot Do

- 🚫 Modify data (INSERT/UPDATE/DELETE) without explicit human approval via the confirmation modal.
- 🔒 Query tables or columns outside the defined semantic schema.
- 🌐 Answer questions about data that isn't in the Olist dataset (e.g., live stock prices).
- 🎲 Guarantee 100% correct SQL for every possible question — LLM output is probabilistic. Always review the generated SQL before trusting results.

---

## 7. ✨ New Features

### 📊 Evaluation Dashboard

An automated RAGAS-style SQL evaluation pipeline that runs every question in a golden test set through the full LLM pipeline and scores the output.

**How to use:** Click the **Evaluation** tab in the app and press **Run Evaluation**.

**How it works:**
1. Each question is run through `run_query()` to generate and execute SQL.
2. The expected SQL is also executed directly to produce a reference result set.
3. Both result sets are compared value-by-value (order-agnostic, column-name-agnostic).
4. Pass/fail, latency, and any errors are persisted to the `eval_log` table.

**Metrics tracked:** Execution accuracy (%), pass/fail per question, average latency (ms), run ID for historical comparison.

---

### 📈 Chart Auto-Generation

After SQL results are returned, the pipeline automatically classifies the result shape and suggests the best chart type.

**How it works:** `_classify_chart()` in `sql_chain.py` inspects column names and value types:
- Date/time column + numeric column → **Line chart**
- Category column + numeric column → **Bar chart**
- Otherwise → **Table only**

A **Show Chart / Show Table** toggle appears below each result set when a chart is available. Charts are rendered using [Recharts](https://recharts.org).

---

### 🕘 Query History

A collapsible left sidebar shows the last 20 queries from the `query_log` table. Clicking any past question pre-fills the chat input so it can be re-run or modified.

The sidebar collapses to a narrow strip to maximize screen space and expands with a single click.

---

## 8. 📁 Project Structure

```
text-to-sql/
│
├── agent/                      # Core AI pipeline
│   ├── sql_chain.py            # Main LCEL pipeline: question → SQL → results + chart classification
│   ├── retriever.py            # RAG: embed question, query ChromaDB
│   ├── semantic_layer.py       # Business descriptions for every table/column
│   ├── build_index.py          # One-time script: embed schema into ChromaDB
│   ├── hitl_guard.py           # Safety: block write SQL, require human approval
│   └── few_shot_examples.yaml  # Curated Q→SQL examples for in-context learning
│
├── api/                        # FastAPI web server
│   ├── main.py                 # App factory, CORS, error handling
│   └── routes/
│       ├── query.py            # POST /query — runs the full pipeline
│       ├── schema.py           # GET /schema — returns table descriptions
│       ├── health.py           # GET /health — liveness check
│       ├── eval.py             # POST /eval, GET /eval/meta — golden-set evaluation
│       └── history.py          # GET /history — last 20 queries from query_log
│
├── model/                      # SQLAlchemy ORM models
│   ├── database.py             # Engine + session factory
│   └── schema.py               # Table definitions (star schema + query_log + eval_log)
│
├── frontend/                   # React + TypeScript UI
│   └── src/
│       ├── App.tsx             # Root component
│       ├── api.ts              # HTTP client
│       └── components/
│           ├── ChatWindow.tsx       # Question input + message history
│           ├── SqlDisplay.tsx       # Syntax-highlighted SQL output
│           ├── ResultsTable.tsx     # Pageable results grid
│           ├── ChartDisplay.tsx     # Bar/line chart via Recharts
│           ├── QueryHistory.tsx     # Collapsible query history sidebar
│           ├── EvalDashboard.tsx    # Evaluation metrics dashboard
│           ├── SchemaExplorer.tsx   # Browse available tables/columns
│           └── ApprovalModal.tsx    # HITL confirmation dialog
│
├── data/
│   ├── raw/                    # Raw Olist CSV files
│   ├── eval_golden_set.json    # 12-question golden test set for evaluation
│   └── seed.py                 # Load CSVs → SQLite (run once)
│
├── infra/                      # Deployment scripts (Linux/nginx/systemd)
│
├── requirements.txt            # Python dependencies
└── .env.example                # Copy to .env and fill in your keys
```

---

## 8. 🗄️ Database Schema

The database uses a **star schema** — a design pattern common in data warehouses where one central "fact" table holds measurable events, and multiple "dimension" tables hold descriptive attributes. ⭐

```
                    ┌─────────────┐
                    │  dim_users  │
                    │  user_id PK │
                    │  city       │
                    │  state      │
                    └──────┬──────┘
                           │ FK
┌──────────────┐    ┌──────▼────────────┐    ┌───────────────┐
│ dim_products │    │   fact_orders     │    │  dim_sellers  │
│ product_id PK│◄───│   order_id PK     │───►│  seller_id PK │
│ category_name│    │   user_id FK      │    │  seller_city  │
│ photos_qty   │    │   product_id FK   │    │  seller_state │
└──────────────┘    │   seller_id FK    │    └───────────────┘
                    │   order_total_usd │
                    │   order_status    │    ┌───────────────┐
                    │   created_at      │───►│  dim_reviews  │
                    └───────────────────┘    │  review_id PK │
                                             │  order_id FK  │
                    ┌───────────────────┐    │  review_score │
                    │  dim_geography    │    └───────────────┘
                    │  geo_id PK        │
                    │  zip_code_prefix  │
                    │  city, state      │
                    │  lat, lng         │
                    └───────────────────┘
```

---

## 9. 🚀 Quick Start

### Prerequisites

- 🐍 Python 3.11+
- 🟢 Node.js 18+
- 🔑 An OpenAI API key

### 1. Clone and install Python dependencies

```bash
git clone https://github.com/nerdjerry/text-to-sql.git
cd text-to-sql
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# ✏️ Edit .env and set your OPENAI_API_KEY
```

### 3. Seed the database 🌱

Download the raw Olist CSVs into `data/raw/` (see Kaggle link in [What Does This Project Do?](#1-what-does-this-project-do)), then run:

```bash
python -m data.seed
```

### 4. Build the vector index 🔢

This embeds all table descriptions into ChromaDB. Run once, or re-run whenever you update `semantic_layer.py`:

```bash
python -m agent.build_index
```

### 5. Start the API server 🖥️

```bash
uvicorn api.main:app --reload --port 8000
```

### 6. Start the frontend 🎨

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser and start asking questions! 🎉

---

## 10. ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key. Get one at [platform.openai.com](https://platform.openai.com). |
| `OPENAI_MODEL` | `gpt-4o` | The chat model used to generate SQL. |
| `DATABASE_URL` | `sqlite:///./data/olist.db` | SQLAlchemy connection string. Use `postgresql://...` for Postgres. |
| `CHROMA_PERSIST_DIR` | `./chroma_store` | Directory where ChromaDB persists vector embeddings. |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model used for both indexing and retrieval. |
| `LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `ALLOWED_ORIGINS` | `*` | Comma-separated CORS origins. Set to your domain in production. |

### Medium blog link-
[https://medium.com/@shaikrizwanahussain/i-extended-an-open-source-text-to-sql-system-241be9a81b30?postPublishedType=repub](https://medium.com/@shaikrizwanahussain/i-extended-an-open-source-text-to-sql-system-241be9a81b30?postPublishedType=repub)
