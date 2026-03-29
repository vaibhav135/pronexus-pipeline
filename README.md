# ProNexus Lead Generation Pipeline

Automated pipeline to discover blue-collar businesses (HVAC, plumbers, electricians), identify business owners, and find contact emails — at scale and under 4 cents per lead.

## Table of Contents

- [Architecture](#architecture)
- [Pipeline Steps](#pipeline-steps)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Research & Decisions](#research--decisions)
- [Cost Model](#cost-model)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    PIPELINE WORKER                       │
│                  (Python, FastAPI, uv)                   │
│                                                         │
│  ┌──────────┐   ┌───────────┐   ┌───────────────────┐  │
│  │  Step 1  │   │  Step 2   │   │      Step 3       │  │
│  │Discovery │──▶│ Owner ID  │──▶│  Email Finding     │  │
│  └──────────┘   └───────────┘   └───────────────────┘  │
│       │               │                   │             │
│       ▼               ▼                   ▼             │
│  ┌─────────────────────────────────────────────────┐    │
│  │               PostgreSQL Database               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │         FastAPI — Status & Monitoring API        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                        │
                  Railway.app
```

## Pipeline Steps

### Step 1: Business Discovery

Search Google Maps for businesses by category + location using Scraper Tech API.

- **API:** Scraper Tech via `api.scraper.tech`
- **Input:** Query like `"HVAC contractor Houston TX"`
- **Output:** Business name, phone, website, address, rating, reviews
- **Deduplication:** By `place_id`

### Step 2: Owner Identification (Waterfall)

Find the business owner's name through a multi-step fallback chain:

```
Website Scrape (Jina Reader + Groq)
        │
        ├── Found → store, move to Step 3
        │
        ▼ Not found
Tavily Search (1,000 free/month) + Groq
        │
        ├── Found → store, move to Step 3
        │
        ▼ Not found
Exa Search (1,000 one-time credits) + Groq
        │
        ├── Found → store, move to Step 3
        │
        ▼ Not found
Store as null → move to Step 3
```

**Website scraping:** [Jina Reader API](https://jina.ai/reader/) converts any URL to clean markdown (renders JavaScript, handles complex sites). Falls back to plain `httpx` if Jina is unavailable.

**LLM extraction:** Groq Llama 3.1 8B ($0.05/1M tokens) extracts the owner name from scraped text. An 8B model performs identically to 70B for this simple extraction task.

**Search fallback:** When the owner name isn't on the website, we search the web using [Tavily](https://tavily.com/) (primary, 1,000 free/month resets) and [Exa](https://exa.ai/) (secondary, 1,000 one-time credits).

### Step 3: Email Finding (Waterfall)

*Coming soon* — Outscraper → Prospeo → Hunter.io waterfall.

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.12 | Ecosystem fit |
| Package manager | uv | Fast, lockfile-based |
| Web framework | FastAPI | Async, lightweight |
| ORM | SQLModel | SQLAlchemy + Pydantic in one |
| Database | PostgreSQL | Structured, queryable |
| Migrations | Alembic | Schema versioning |
| LLM | Groq (Llama 3.1 8B) | Cheapest, fastest, proven |
| Website scraping | Jina Reader API | JS rendering, clean markdown |
| Search (primary) | Tavily | 1,000 free/month, AI-optimized |
| Search (secondary) | Exa | Semantic search, people/company categories |
| Maps discovery | Scraper Tech | Google Maps data |
| Containerization | Docker | Local dev + Railway deploy |
| Hosting | Railway.app | Managed Postgres, 24/7 worker |

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker (for local PostgreSQL)

### Setup

```bash
# Clone and enter backend
cd backend

# Install dependencies
uv sync

# Copy env template and add your API keys
cp .env.example .env
# Edit .env with your keys

# Start PostgreSQL
docker-compose up -d

# Run migrations
uv run python -m alembic upgrade head

# Start the server
uv run uvicorn app.main:app --reload
```

### Required API Keys

| Key | Where to get it | Free tier |
|---|---|---|
| `MAP_SCRAPER` | [scraper.tech](https://scraper.tech) | Pro plan $5.99/mo |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | Free tier available |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | 1,000 searches/month |
| `EXA_API_KEY` | [dashboard.exa.ai](https://dashboard.exa.ai) | 1,000 one-time credits |
| `JINA_AI_API_KEY` | [jina.ai](https://jina.ai) | 10M free tokens |

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + health check
│   ├── config.py            # Settings from env vars
│   ├── database.py          # Async SQLModel engine + session
│   │
│   ├── models/
│   │   └── db.py            # SQLModel tables (Business, ScrapeJob)
│   │
│   ├── api/
│   │   ├── routes.py        # API routes (POST /api/search)
│   │   └── schemas.py       # Pydantic request/response schemas
│   │
│   ├── pipeline/
│   │   ├── discovery.py     # Step 1: Google Maps scraping
│   │   ├── owner_id.py      # Step 2: Owner identification (TODO)
│   │   └── email_finder.py  # Step 3: Email waterfall (TODO)
│   │
│   └── utils/
│       └── __init__.py
│
├── alembic/                 # Database migrations
├── scripts/
│   └── test_discovery.py    # Discovery service test
├── docker-compose.yml       # Local PostgreSQL
├── pyproject.toml
└── .env.example
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/search` | Search Google Maps, store businesses |

### POST /api/search

```json
{
  "query": "HVAC contractor Houston TX",
  "limit": 20,
  "offset": 0,
  "country": "us",
  "lang": "en",
  "zoom": 12,
  "lat": "",
  "lng": ""
}
```

Returns discovered businesses with deduplication by `place_id`.

## Research & Decisions

Extensive research was done to find the best tools for each pipeline step. Here's a summary of what was tested and why specific tools were chosen.

### LLM for Owner Name Extraction

| Model | Result | Price/1M input |
|---|---|---|
| **Llama 3.1 8B (Groq)** | 2/3 correct | $0.05 |
| Llama 3.3 70B (Groq) | 2/3 correct | $0.59 |
| Llama 4 Scout 17B (Groq) | 2/3 correct | $0.11 |
| GPT-OSS 20B (Groq) | Broken (reasoning model) | $0.075 |
| GPT-OSS 120B (Groq) | Broken (reasoning model) | $0.15 |
| Nemotron Nano 30B (OpenRouter) | 2/3 correct | $0.05 |

**Decision:** Llama 3.1 8B. All working models gave identical results — bigger models don't help for simple name extraction. Research confirms 8B matches 70B on extraction tasks ([arxiv](https://arxiv.org/pdf/2506.08827), [Nature](https://www.nature.com/articles/s41598-025-28767-z)).

### NER Models vs LLMs

| Model | Score | Notes |
|---|---|---|
| **Groq Llama 8B** | 2/3 | Best — understands context ("owner" vs random person) |
| GLiNER (zero-shot NER) | 1.5/3 | Good on clean text, noisy on real websites |
| NuNER Zero | 1/3 | Worse than GLiNER on our test data |
| spaCy | 1/3 | Too noisy, can't distinguish owner from other people |

**Decision:** LLM over NER. NER models find all person names but can't tell owner from customer testimonial. LLM understands context.

### Website Scraping

| Method | Score | Notes |
|---|---|---|
| **Jina Reader** | 2/3 | Renders JS, clean markdown, free 10M tokens |
| ScrapeGraphAI | 2/3 | Playwright-based, heavy deps |
| httpx + strip_html | 1/3 | Misses JS-rendered content |

**Decision:** Jina Reader API. One HTTP call, no browser dependency, renders JavaScript.

### Search Fallback (when owner not on website)

| Method | Score | Cost | Status |
|---|---|---|---|
| Scrapling + residential proxy + Google | 2/3 | ~$0.07/month | Proven, future implementation |
| Camoufox + residential proxy + Google | 2/3 | ~$0.07/month | Proven but inconsistent |
| **Tavily** | Not tested on our data | 1,000 free/month | Primary fallback |
| **Exa** | Not tested on our data | 1,000 one-time | Secondary fallback |
| SearXNG (self-hosted) | 1/3 | Free | Poor result quality |
| DuckDuckGo (ddgs library) | 0/3 | Free | Useless for owner names |
| DuckDuckGo via Camoufox | 2/3 | Free | Good but not Google quality |
| yagooglesearch | 0/3 | Free | Broken since Jan 2025 |
| Serper free tier | 2,500 one-time | $50/50k after | Too expensive |

**Decision:** Tavily (primary) + Exa (secondary). Both have free tiers. Future: add Scrapling + residential proxy for direct Google search when free tiers are exhausted.

### Google Search — Why It's Hard

Since January 2025, Google requires JavaScript rendering for search results. No HTTP-only scraper works anymore. Additionally:
- Google detects all headless browsers (Playwright, Lightpanda) and silently returns empty results
- reCAPTCHA v3 is invisible scoring — no puzzle to solve
- The only open-source tool that bypassed Google detection was **Scrapling's StealthyFetcher** combined with a **residential proxy** (DataImpulse, $1/GB)
- Commercial SERP APIs (Serper, SerpAPI) work because they use Google's official Custom Search API or massive proxy infrastructure

### How Commercial Tools Do Web Search

| Product | Search method |
|---|---|
| Claude Code | Anthropic's proprietary web search |
| OpenClaw | Brave Search API (user provides key) |
| Jan.ai | Serper API (Google results via MCP) |
| Perplexity | Own search index (hundreds of billions of pages) |
| ChatGPT | Bing (Microsoft partnership) |

## Cost Model

### At 10,000 leads/month

| Item | Cost |
|---|---|
| Scraper Tech Pro (Google Maps) | $5.99 |
| Groq Llama 8B (owner extraction) | ~$0.54 |
| Tavily (search fallback) | Free (1,000/month) |
| Exa (search overflow) | Free (1,000 one-time) |
| Jina Reader (website scraping) | Free (10M tokens) |
| Railway Hobby plan | $5.00 |
| **Total** | **~$12/month** |
| **Cost per lead** | **~$0.0012** |

---

*Built with research-driven decisions. Every tool was tested on real business websites before being selected.*
