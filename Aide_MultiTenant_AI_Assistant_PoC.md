# Aide — Multi-Tenant Personal AI Assistant · PoC Architecture

**Product:** Aide — "Your AI assistant. Already in your WhatsApp."
**Stack:** Hermes Agent + PostgreSQL + Traefik + Zitadel + NextCloud + Lago
**Phase:** Proof of Concept → 10 users → Production
**Target:** Hong Kong professionals (30–55), 92% WhatsApp penetration

---

## 1. Product Overview

| | |
|---|---|
| **Name** | **Aide** (French for "assistant") |
| **Tagline** | Your AI assistant. Already in your WhatsApp. |
| **No app to download** | User saves a phone number, says hello, done |
| **Cross-device** | WhatsApp on phone → Telegram on tablet → Web on laptop — one identity |
| **Shared drive** | Every user gets personal cloud storage. Send photos, PDFs, voice notes — Aide indexes everything |
| **Target** | HK finance/legal professionals, SME owners, working parents, frequent travelers |

### Pricing Tiers

| Tier | Price/mo | Daily Tokens | Storage | Users | Key Features |
|------|----------|-------------|---------|-------|--------------|
| **Free** | $0 | 10K | — | 1 | Basic Q&A, 10 msg/day |
| **Pro** | $8 | 100K | 5 GB | 1 | Full assistant, drive, cross-device, file indexing |
| **Family** | $15 | 100K/user | 20 GB shared | ≤3 | All Pro features + shared lists, shared folders, family calendar |

---

## 2. Multi-Tenant Architecture

### 2.1 Infrastructure Stack

```
┌──────────────────────────────────────────────────────────────┐
│                    INTERNET (HTTPS)                           │
└──────────────────────────┬───────────────────────────────────┘
                           │
┌──────────────────────────┴───────────────────────────────────┐
│                   TRAEFIK API GATEWAY                         │
│  • TLS termination (Let's Encrypt auto)                       │
│  • Rate limiting per tenant (100 req/min)                     │
│  • ForwardAuth → Zitadel (JWT validation)                     │
│  • Request routing: /api/* → Hermes, /files/* → NextCloud     │
└──────┬──────────┬──────────┬──────────┬──────────────────────┘
       │          │          │          │
┌──────┴──┐ ┌─────┴───┐ ┌───┴────┐ ┌──┴──────────┐
│ Zitadel │ │  Lago   │ │NextCloud│ │Hermes Agent  │
│  (IAM)  │ │(Billing)│ │(Drive)  │ │(AI Engine)   │
│ Auth ·  │ │Plans ·  │ │Files ·  │ │Profiles ·    │
│ OIDC ·  │ │Usage ·  │ │Sync ·   │ │Skills ·      │
│Users ·  │ │Stripe   │ │Sharing  │ │Memory ·       │
│Tenants  │ │Gateway  │ │         │ │Cron ·         │
└──────┬──┘ └─────┬───┘ └───┬────┘ │Delegation     │
       │          │          │      └──────┬────────┘
       │          │          │             │
┌──────┴──────────┴──────────┴─────────────┴──────────┐
│               PostgreSQL 16 (Single Cluster)          │
│  Row-Level Security per tenant (tenant_id column)     │
│  Tables: users, tenants, sessions, messages,          │
│          token_usage, files_index, subscriptions      │
└──────────────────────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────┐
│              REDIS (Cache + Session)                  │
│  Per-tenant session state, token budget counters,     │
│  WebSocket presence tracking                          │
└──────────────────────────────────────────────────────┘
```

### 2.2 Tenant Isolation Strategy

**Recommended: Hermes Profiles + PostgreSQL RLS**

| Layer | Isolation Method |
|-------|-----------------|
| **Filesystem** | Hermes profiles: `~/.hermes/profiles/<tenant_id>/` — isolated skills, cron, memory |
| **Database** | PostgreSQL RLS: every table has `tenant_id` column. `SET app.current_tenant_id = '<uuid>'` before queries |
| **Cache** | Redis key prefix: `tenant:<id>:*` — no cross-tenant reads |
| **LLM** | Separate API calls per tenant — no context sharing between users |
| **Drive** | NextCloud per-user directories: `/data/<tenant_id>/files/` |

Why not separate processes: Hermes profiles give us 90% of the isolation with 10% of the ops overhead. For PoC (10 users), profile-per-tenant is ideal. At 1000+ users, move to process-per-tenant-group.

### 2.3 Database Schema (Core Tables)

```sql
-- Root tenant table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_hash TEXT UNIQUE NOT NULL,        -- SHA-256 of WhatsApp number
    display_name TEXT,
    plan TEXT DEFAULT 'free',               -- free, pro, family
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT now(),
    token_used_today INT DEFAULT 0,
    token_limit_daily INT DEFAULT 10000,
    storage_used_bytes BIGINT DEFAULT 0,
    storage_limit_bytes BIGINT DEFAULT 5368709120  -- 5GB default
);

-- All multi-tenant tables follow this pattern:
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    role TEXT NOT NULL,                     -- user, assistant, system
    content TEXT NOT NULL,
    tokens_used INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- RLS: every table enforces tenant isolation
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON conversations
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Repeat for: reminders, expenses, files_index, health_logs, learning_plans, shopping_lists
```

### 2.4 Token Budget Enforcement

```
User sends message
    → Traefik: check JWT → extract tenant_id
    → Hermes: SET app.current_tenant_id = '<uuid>'
    → Token Budget Service:
        1. Redis GET tenant:<id>:tokens_used_today
        2. Estimate tokens for this request (intent router: cheap model estimates)
        3. If current + estimate > daily_limit:
           → Return: "You've reached your daily limit. Upgrade to Pro?"
        4. Otherwise: approve → increment counter
    → After response: Redis INCRBY tenant:<id>:tokens_used_today <actual_tokens>
    → Daily cron at midnight HKT: RESET all counters
```

---

## 3. User Flow

### 3.1 Onboarding (< 2 minutes)

```
0:00  User visits aide.ai/hk
0:15  Enters WhatsApp number → clicks "Start"
0:20  Receives WhatsApp OTP: "Your Aide verification code: 829401"
0:35  Enters OTP on website → verified
0:45  Chooses plan: Free (Start now) or Pro ($8/mo, 7-day free trial)
1:00  WhatsApp: "Hello! I'm Aide, your personal assistant 👋"
1:15  Aide introduces itself with emoji menu of capabilities
1:30  User: "Remind me to submit Q3 report Friday 5pm"
1:45  Aide: "✅ Set. I'll remind you Friday at 5pm."
```

### 3.2 Cross-Device Continuity

```
Phone (WhatsApp):     "Save this receipt photo"
Tablet (Telegram):    "What's my spending this week?"  ← Aide has the receipt
Laptop (Web):          Opens aide.ai → sees same conversation, same files
```

**How**: Hermes session DB stores conversation state. Redis tracks last-active device. NextCloud syncs files across devices. Supabase Realtime (WebSocket) pushes state changes to all connected devices.

---

## 4. Shared Drive Architecture

### 4.1 Per-User Cloud Storage (NextCloud)

```
User sends photo of receipt via WhatsApp
    → Hermes receives: image/jpeg
    → MarkItDown: extract text (OCR) → structured metadata
    → Save to: NextCloud /data/<tenant_id>/files/receipts/2026-07-01_lunch.jpg
    → Index in: files_index table {tenant_id, path, type, extracted_text, tags, created_at}
    → Later: "Show me my March receipts"
    → Hermes: SELECT * FROM files_index WHERE tenant_id=X AND path LIKE '%receipts%2026-03%'
    → Returns: list of files with thumbnails + amounts

User sends PDF (45-page insurance policy)
    → Hermes receives: application/pdf
    → MarkItDown: convert to Markdown (structured)
    → Save to: NextCloud /data/<tenant_id>/files/documents/insurance_policy.md
    → Index full text in vector DB (for semantic search)
    → Later: "What's my hospital coverage limit?"
    → Hermes: vector search → retrieves relevant sections → LLM answers
```

### 4.2 Auto-Organized Folder Structure

```
/data/<tenant_id>/files/
├── receipts/          ← Auto-sorted by date
│   ├── 2026-06/
│   └── 2026-07/
├── documents/         ← PDFs, contracts, policies
├── photos/            ← Personal photos with metadata extraction
├── voice-notes/       ← Voice messages transcribed
├── shared/            ← Family plan: shared with other tenant IDs
└── archive/           ← User-marked archived items
```

---

## 5. Deployment Plan — PoC (10 Users)

### 5.1 Single VPS (Hetzner CX32: 4 vCPU, 8GB, 80GB — $12/mo)

```yaml
# docker-compose.yml
services:
  traefik:        # API Gateway + SSL
  zitadel:        # Auth (512MB)
  lago:           # Billing (512MB)
  nextcloud:      # File storage (512MB)
  hermes-agent:   # 10 profile instances (2GB)
  postgres:       # Single DB for all (1GB)
  redis:          # Cache + sessions (256MB)
  supabase-realtime: # WebSocket sync (256MB)
```

**Total RAM: ~5GB / 8GB — comfortable for 10 users PoC.**

### 5.2 Monthly Cost Breakdown — PoC

| Item | Cost |
|------|------|
| VPS (Hetzner CX32) | $12 |
| DeepSeek API (10 users × avg 30K tokens/day) | $15–25 |
| Backblaze B2 backups | $1 |
| Domain (aide.ai) | $12/year ≈ $1/mo |
| Stripe processing | ~3% of revenue |
| **TOTAL** | **$29–39/month** |

At $8/user Pro plan: 10 users = $80/mo revenue → **profitable at PoC scale.**

### 5.3 Production Scaling Path

| Phase | Users | Infrastructure | Cost/mo |
|-------|-------|---------------|---------|
| **PoC** | 10 | 1× CX32 Docker Compose | $30–40 |
| **Beta** | 100 | 1× CX42 (8 vCPU, 16GB) + 1× DB only CX22 | $60–80 |
| **Launch** | 1,000 | k3s cluster (3 nodes CX32) + managed Postgres | $200–400 |
| **Scale** | 10K+ | Citus horizontal Postgres, Kong AI Gateway, Hermes process-per-tenant-group | $800–1,500 |

---

## 6. Security Model

| Layer | Measure |
|-------|---------|
| **Auth** | Zitadel OIDC — JWT access tokens, refresh tokens, WhatsApp phone OTP |
| **API** | Traefik ForwardAuth — validates JWT on every request, rate limits per tenant |
| **Database** | PostgreSQL RLS — `tenant_id` enforced at DB level. Even if SQL injection succeeds, can't read other tenants |
| **Files** | NextCloud per-user directories — WebDAV auth tied to Zitadel user |
| **LLM** | No tenant data shared between API calls. Each request is stateless |
| **Secrets** | `.env` only, SOPS/age encrypted at rest, never committed |
| **PII** | Phone numbers SHA-256 hashed. Conversation data encrypted at rest |
| **Backups** | Daily encrypted to Backblaze B2 via `rclone crypt` (client-side AES-256) |

---

## 7. Admin Dashboard (Hermes Self-Managed)

Admin interacts via **Telegram** (privileged channel):

```
/status         → CPU, RAM, disk, active tenants, token usage today
/tenants        → List all tenants: plan, usage, status
/tenant <id>    → Detail: messages today, storage used, last active
/alert          → Set alert: "Warn me when >80% disk"
/budget         → Global token spend today/this month
/logs <N>       → Last N error logs
```

For customer-facing: web dashboard at `aide.ai/dashboard` — billing only (change plan, view invoices, payment methods). Everything else is WhatsApp.

---

## 8. Competitive Moat

| Competitor | Aide's Advantage |
|-----------|-----------------|
| **ChatGPT** | ChatGPT is a chatbot. Aide is an assistant — it has a drive, remembers context across days, pushes reminders proactively. ChatGPT doesn't store your files or remind you to call mom. |
| **Pi / Replika** | Companion AI, not a productivity tool. No file storage, no reminders, no email triage. |
| **Generic WhatsApp bots** | Single-function (weather, news). Aide is a unified interface to your whole digital life. |
| **Google Assistant / Siri** | Tied to ecosystem. No cross-device file store. Can't answer questions about your own documents. |
| **Notion AI / Mem** | Productivity tools with AI, not AI-first. You still need to open an app and organize manually. |

**Moat factors:**
1. WhatsApp-native — 92% HK penetration, zero adoption friction
2. Personal cloud drive — your files + AI that understands them
3. Cross-device identity — same assistant everywhere
4. Proactive, not reactive — pushes reminders, alerts, suggestions
5. Self-hosted privacy — data never leaves the VPS you control

---

## 9. 5-Day PoC Build Plan

| Day | Deliverables |
|-----|-------------|
| **1** | VPS provisioned, Docker Compose stack: Traefik + Zitadel + PostgreSQL + Redis + NextCloud |
| **2** | Hermes Agent multi-profile setup. Tenant provisioning script. WhatsApp Gateway + Telegram Gateway |
| **3** | Core skills: reminders, expense logging, email triage (Google MCP), shopping list |
| **4** | File indexing pipeline: WhatsApp photo → MarkItDown OCR → NextCloud save → DB index. Shared drive queries. Token budget enforcement |
| **5** | Lago billing integration. Admin Telegram commands. Onboarding flow test. 10-user invitation. Monitoring alerts |

---

**Ready to build.** All components open-source, self-hosted, API-integrable. One VPS. Docker Compose. WhatsApp-first. Hong Kong market validated.
