# ProNexus Lead Generation Pipeline

Automated pipeline to discover blue-collar businesses (HVAC, plumbers, electricians), identify business owners, and find contact emails — at scale and under 4 cents per lead.

## Table of Contents

- [Architecture](#architecture)
- [Pipeline Steps](#pipeline-steps)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Frontend](#frontend)
- [Research & Decisions](#research--decisions)
- [Cost Model](#cost-model)

## Architecture

```
┌──────────────────────────────────────────────────────┐
│              FRONTEND (Next.js + Bun)                │
│                                                      │
│  Search Bar ──▶ Results Table ──▶ Export (CSV/PDF/DOCX)
│       │              ▲                               │
│       │              │ SSE (real-time updates)        │
│       ▼              │                               │
└──────────────────────┼───────────────────────────────┘
                       │
              HTTP / SSE (CORS)
                       │
┌──────────────────────┼───────────────────────────────┐
│              BACKEND (FastAPI + Python)               │
│                                                      │
│  ┌──────────┐   ┌───────────┐   ┌─────────────────┐ │
│  │  Step 1  │   │  Step 2   │   │     Step 3      │ │
│  │Discovery │──▶│ Owner ID  │──▶│  Email Finding   │ │
│  └──────────┘   └───────────┘   └─────────────────┘ │
│       │               │                │             │
│       ▼               ▼                ▼             │
│  ┌─────────────────────────────────────────────────┐ │
│  │              PostgreSQL Database                │ │
│  └─────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
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

### Step 2: Owner Identification + Email Extraction

One website scrape feeds both owner name extraction and email extraction in parallel.

```
Scrape website (httpx homepage + about/contact pages → Jina Reader fallback)
    ├── Extract owner name (Groq LLM)
    ├── Extract emails (regex)
    │
    ├── Both found? → done
    │
    ▼ Missing name or email?
Search fallback (Tavily → Exa) — one query, extract both
    ├── Extract owner name (Groq LLM)
    ├── Extract emails (regex)
    │
    ├── Both found? → done
    │
    ▼ Still missing email + have owner name?
Prospeo (owner name + domain → personal email)
    │
    ▼ Still nothing?
Store whatever we have → move on
```

**Website scraping:** `httpx` fetches the homepage and discovers internal pages (about, contact, team) via link parsing. Strips HTML boilerplate (nav, footer, header, sidebar) for cleaner LLM input. Falls back to [Jina Reader API](https://jina.ai/reader/) for JS-heavy sites.

**LLM extraction:** Groq Llama 3.1 8B ($0.05/1M tokens) extracts the owner name from scraped text. An 8B model performs identically to 70B for this simple extraction task.

**Email extraction:** Regex-based extraction from the raw HTML — catches emails in text, `mailto:` links, and contact sections. No LLM needed.

**Search fallback:** When the owner name isn't on the website, we search the web using [Tavily](https://tavily.com/) (primary, 1,000 free/month) and [Exa](https://exa.ai/) (secondary, 1,000 free/month). Both name and email are extracted from the same search results.

**Email fallback:** When no email is found from website or search, [Prospeo](https://prospeo.io/) finds personal emails using the owner name + domain ($0.0074/email, only charges for valid results).

### Future: Direct Google Search

Scrapling's `StealthyFetcher` + DataImpulse residential proxy successfully bypassed Google's bot detection in our tests (found 2/3 owner names via real Google results). This can be added as a third search fallback when Tavily/Exa free tiers are exhausted. See [Research & Decisions](#google-search--why-its-hard) for details.

## Tech Stack

### Backend

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.12 | Ecosystem fit |
| Package manager | uv | Fast, lockfile-based |
| Web framework | FastAPI | Async, lightweight |
| ORM | SQLModel | SQLAlchemy + Pydantic in one |
| Database | PostgreSQL | Structured, queryable |
| Migrations | Alembic | Schema versioning |
| LLM | Groq (Llama 3.1 8B) | Cheapest, fastest, proven |
| Website scraping | httpx + Jina Reader | httpx primary, Jina for JS rendering |
| Search (primary) | Tavily | 1,000 free/month, AI-optimized |
| Search (secondary) | Exa | Semantic search, people/company categories |
| Email finding | Prospeo | Personal email from name + domain |
| Maps discovery | Scraper Tech | Google Maps data |
| Containerization | Docker | Local dev + Railway deploy |
| Hosting | Railway.app | Managed Postgres, 24/7 worker |

### Frontend

| Layer | Tool | Why |
|---|---|---|
| Framework | Next.js 16 (App Router) | React, SSR, file-based routing |
| Runtime | Bun | Fast installs, fast dev server |
| Styling | Tailwind CSS v4 | Utility-first, custom design tokens |
| Components | shadcn/ui (Radix) | Copy-paste, full control |
| Forms | react-hook-form + zod | Validation, type safety |
| Data fetching | @tanstack/react-query | Caching, mutations, server state |
| Icons | lucide-react | Consistent icon set |
| PDF export | jsPDF + jspdf-autotable | Client-side PDF generation |
| DOCX export | docx + file-saver | Client-side Word document generation |

### Design System (Light Theme)

| Token | Color | Usage |
|---|---|---|
| `primary` | `#4F46E5` (Indigo) | Buttons, CTAs, focus rings |
| `secondary` | `#06B6D4` (Teal) | Links, accents |
| `background` | `#FAFBFC` | Page background |
| `surface` | `#FFFFFF` | Cards, table background |
| `success` | `#10B981` | Enriched, verified |
| `warning` | `#F59E0B` | In-progress states |
| `error` | `#EF4444` | Failed states |
| `text` | `#1A1A2E` | Primary text |
| `text-muted` | `#6B7280` | Secondary text |

All colors are available as Tailwind classes (`bg-primary`, `text-text-muted`, etc.) — no raw hex codes in components.

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/)
- Docker (for local PostgreSQL)

### Backend Setup

```bash
cd backend

# Install dependencies
uv sync

# Copy env template and add your API keys
cp .env.example .env
# Edit .env with your keys

# Start PostgreSQL
docker-compose up -d

# Run migrations
uv run alembic upgrade head

# Start the server (runs on http://localhost:8000)
uv run fastapi dev app/main.py
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
bun install

# Start dev server (runs on http://localhost:3000)
bun dev
```

The frontend connects to the backend at `http://localhost:8000` by default. Override with `NEXT_PUBLIC_API_URL` env var.

### Required API Keys

| Key | Where to get it | Free tier |
|---|---|---|
| `MAP_SCRAPER` | [scraper.tech](https://scraper.tech) | Pro plan $5.99/mo |
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | Free tier available |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | 1,000 searches/month |
| `EXA_API_KEY` | [dashboard.exa.ai](https://dashboard.exa.ai) | 1,000 free/month |
| `JINA_AI_API_KEY` | [jina.ai](https://jina.ai) | 10M free tokens |
| `PROSPEO_API_KEY` | [prospeo.io](https://prospeo.io) | Pay per valid result ($0.0074/email) |

### Environment Variables

Backend (`backend/.env`):

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `GROQ_API_KEY` | Groq LLM API key | — |
| `MAP_SCRAPER` | Scraper Tech API key | — |
| `TAVILY_API_KEY` | Tavily search API key | — |
| `EXA_API_KEY` | Exa search API key | — |
| `JINA_AI_API_KEY` | Jina Reader API key | — |
| `PROSPEO_API_KEY` | Prospeo email finder API key | — |

Frontend (`frontend/.env.local`):

| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## Project Structure

```
pronexus-pipeline/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app, CORS, health check
│   │   ├── config.py              # Settings from env vars
│   │   ├── database.py            # Async SQLModel engine + session
│   │   ├── models/
│   │   │   └── db.py              # SQLModel tables (Business, Owner, Email, ScrapeJob)
│   │   ├── api/
│   │   │   ├── routes.py          # API routes (search, enrich, jobs, SSE stream)
│   │   │   └── schemas.py         # Pydantic request/response schemas
│   │   └── pipeline/
│   │       ├── discovery.py       # Step 1: Google Maps scraping
│   │       ├── website_scraper.py # Website scraping (httpx + Jina Reader)
│   │       ├── owner_id.py        # Owner name extraction (Groq LLM)
│   │       ├── search_fallback.py # Tavily → Exa search waterfall
│   │       └── email_finder.py    # Prospeo email fallback
│   ├── alembic/                   # Database migrations
│   ├── scripts/                   # Test scripts
│   ├── docker-compose.yml         # Local PostgreSQL
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css        # Design system tokens + Tailwind config
│   │   │   ├── layout.tsx         # Root layout with QueryProvider
│   │   │   ├── page.tsx           # Home: search bar + recent searches
│   │   │   └── search/[id]/
│   │   │       └── page.tsx       # Results: table + auto-enrich + export
│   │   ├── components/
│   │   │   ├── search-bar.tsx     # Search form (react-hook-form + zod)
│   │   │   ├── job-card.tsx       # Search history cards
│   │   │   ├── results-table.tsx  # Business data table with live updates
│   │   │   ├── export-menu.tsx    # CSV, PDF, DOCX export
│   │   │   └── ui/               # shadcn/ui components
│   │   └── lib/
│   │       ├── api.ts             # React Query hooks + SSE client
│   │       ├── types.ts           # TypeScript types (mirrors backend schemas)
│   │       ├── schemas.ts         # Zod form validation schemas
│   │       ├── query-provider.tsx # React Query provider
│   │       └── utils.ts           # shadcn utility
│   ├── package.json
│   └── bun.lock
│
└── README.md
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/search` | Search Google Maps, store businesses |
| `POST` | `/api/enrich` | Run full pipeline on a single business |
| `GET` | `/api/jobs` | List all search jobs (most recent first) |
| `GET` | `/api/jobs/{id}` | Get a job with its businesses |
| `GET` | `/api/jobs/{id}/enrich-stream` | SSE: enrich all businesses, stream results |

### POST /api/search

Search Google Maps for businesses and store results.

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

### POST /api/enrich

Run the full enrichment pipeline on a stored business — scrape website, identify owner, find email.

```json
{
  "business_id": "uuid-of-business"
}
```

Returns:

```json
{
  "business_id": "...",
  "business_name": "North Texas HVAC",
  "owner_name": "Bryan Slagle",
  "owner_source": "website_httpx",
  "email": "bryan@northtxhvac.com",
  "email_type": "personal",
  "email_source": "website"
}
```

### GET /api/jobs

List all search jobs, most recent first (limit 50).

```json
[
  {
    "id": "uuid",
    "search_query": "HVAC contractor Houston TX",
    "status": "completed",
    "results_count": 20,
    "last_run_at": "2026-03-29T10:30:00Z",
    "created_at": "2026-03-29T10:30:00Z"
  }
]
```

### GET /api/jobs/{id}

Get a single job with all its businesses.

```json
{
  "job": { "id": "...", "search_query": "...", "status": "completed", "results_count": 20, "..." : "..." },
  "businesses": [ { "id": "...", "name": "...", "..." : "..." } ]
}
```

### GET /api/jobs/{id}/enrich-stream

SSE endpoint that enriches all businesses for a job and streams results in real-time.

**Event types:**

| Event | Data | Description |
|---|---|---|
| `result` | `EnrichResponse` | A business was successfully enriched |
| `progress` | `{ completed, total }` | Progress update |
| `error` | `{ business_id, business_name, error }` | Enrichment failed for one business |
| `done` | `{ message }` | All businesses processed |

The frontend automatically connects to this endpoint when navigating to a search results page. Each business is enriched sequentially — already-enriched businesses return cached results.

## Frontend

### Pages

**Home (`/`)** — Search bar with advanced options (result limit, lat/lng), list of recent searches as clickable cards.

**Results (`/search/[id]`)** — Data table showing all businesses from a search. Enrichment starts automatically via SSE. Rows update in real-time as owner names and emails are found. Export to CSV, PDF, or DOCX at any time.

### Features

- Real-time enrichment via Server-Sent Events (SSE)
- Auto-enrich on page load — no manual trigger needed
- Stop/resume enrichment at any time
- Retry failed enrichments
- Export results as CSV, PDF, or DOCX
- Advanced search options (result limit, coordinates)
- Source badges on owner names and emails (Website, Search, Prospeo)
- Verified business indicators
- Responsive table with loading skeletons

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

**Decision:** httpx as primary (fast, no deps), Jina Reader as fallback for JS-heavy sites. HTML stripping removes boilerplate (nav, footer, header, sidebar) for cleaner LLM input.

### Search Fallback (when owner not on website)

| Method | Score | Cost | Status |
|---|---|---|---|
| Scrapling + residential proxy + Google | 2/3 | ~$0.07/month | Proven, future implementation |
| Camoufox + residential proxy + Google | 2/3 | ~$0.07/month | Proven but inconsistent |
| **Tavily** | Found Bryan Slagle | 1,000 free/month | Primary fallback |
| **Exa** | Not tested | 1,000 free/month | Secondary fallback |
| SearXNG (self-hosted) | 1/3 | Free | Poor result quality |
| DuckDuckGo (ddgs library) | 0/3 | Free | Useless for owner names |
| DuckDuckGo via Camoufox | 2/3 | Free | Good but not Google quality |
| yagooglesearch | 0/3 | Free | Broken since Jan 2025 |
| Serper free tier | 2,500 one-time | $50/50k after | Too expensive after free tier |

**Decision:** Tavily (primary) + Exa (secondary). Both have monthly-resetting free tiers. Future: add Scrapling + residential proxy for direct Google search when free tiers are exhausted.

### Google Search — Why It's Hard

Since January 2025, Google requires JavaScript rendering for search results. No HTTP-only scraper works anymore. Additionally:
- Google detects all headless browsers (Playwright, Lightpanda) and silently returns empty results
- reCAPTCHA v3 is invisible scoring — no puzzle to solve
- The only open-source tool that bypassed Google detection was **Scrapling's StealthyFetcher** combined with a **residential proxy** (DataImpulse, $1/GB)
- Commercial SERP APIs (Serper, SerpAPI) work because they use Google's official Custom Search API or massive proxy infrastructure
- No open-source CAPTCHA solver exists for reCAPTCHA v3 (it's behavior-based scoring, not a puzzle)

### How Commercial Tools Do Web Search

| Product | Search method |
|---|---|
| Claude Code | Anthropic's proprietary web search |
| OpenClaw | Brave Search API (user provides key) |
| Jan.ai | Serper API (Google results via MCP) |
| Perplexity | Own search index (hundreds of billions of pages) |
| ChatGPT | Bing (Microsoft partnership) |

### Tools Tested But Not Used

| Tool | Why not |
|---|---|
| ScrapeGraphAI | Heavy deps (Playwright + langchain), SearchGraph sends 67k tokens per query |
| LangExtract (Google) | Provider routing fights non-Gemini models, no improvement over raw Groq |
| Camoufox | Works but inconsistent with Google after multiple rapid searches |
| Lightpanda | JS engine too weak for Google, detected as bot |
| OpenSERP | go-rod Chromium can't handle authenticated proxies |
| SearXNG | Google engine blocked, other engines return poor results |
| yagooglesearch/googlesearch-python | Broken since Google requires JS (Jan 2025) |
| GLiNER/NuNER Zero | NER can't distinguish owner from random person on page |
| spaCy | Too noisy for messy website HTML |

## Cost Model

### At 10,000 leads/month

| Item | Cost |
|---|---|
| Scraper Tech Pro (Google Maps) | $5.99 |
| Groq Llama 8B (owner extraction) | ~$0.54 |
| Tavily (search fallback) | Free (1,000/month) |
| Exa (search overflow) | Free (1,000/month) |
| Jina Reader (website scraping) | Free (10M tokens) |
| Prospeo (email fallback, ~30% of leads) | ~$22.00 |
| Railway Hobby plan | $5.00 |
| **Total** | **~$34/month** |
| **Cost per lead** | **~$0.0034** |

---

*Built with research-driven decisions. Every tool was tested on real business websites before being selected.*
