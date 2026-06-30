# Hermes Personal AI Assistant — Master Implementation Plan

**Author:** Chi Ho Leung · Hong Kong (HKT)  
**Core Engine:** Hermes Agent (DeepSeek V4 Pro)  
**Target Users:** Non-technical (family members, colleagues)  
**Primary Interface:** WhatsApp (zero learning curve)  
**Budget Target:** $15–20/month all-in

---

## Executive Summary

A single-VPS personal AI assistant that non-technical users access exclusively through WhatsApp — just like chatting with a friend. Covers 5 life domains with automated workflows, token-efficient LLM usage, and military-grade data privacy. No new apps to learn. No technical jargon. No code visible.

**What it does:** Schedule reminders, triage emails, track spending, manage shopping lists, control smart home devices, create learning plans, track health — all by texting WhatsApp naturally.

---

## 1. Domain Coverage & Integration Projects

### 1.1 Personal Life — Scheduling, Reminders, Habits, Home

| Project | Stars | Role | Self-Host Cost | Integration |
|---------|-------|------|---------------|-------------|
| **Cal.com** | 38K | Calendar & scheduling | Free (self-host) | REST API → Hermes skill |
| **ntfy.sh** | 20K | Push notifications | Free | HTTP webhook → Hermes sends alerts |
| **Habitica** | 12K | Habit tracking (gamified) | Free | REST API |
| **Vikunja** | 8K | Task management | Free | REST API → todo skill |
| **Grocy** | 7K | Home inventory, chores | Free | REST API |

**Hermes Integration:** Cron scheduler handles recurring reminders. Google Calendar MCP for calendar sync. ntfy for push to phone when Hermes needs attention.

### 1.2 Workplace — Email, Calendar, Documents, Meetings

| Project | Stars | Role | Self-Host Cost | Integration |
|---------|-------|------|---------------|-------------|
| **AppFlowy** | 60K | Notion alternative (docs, wikis) | Free | REST API |
| **Outline** | 28K | Team knowledge base | Free | REST API |
| **Mail0** | 6K | Open-source email client | Free | IMAP/SMTP |
| **Thunderbird/K-9** | 12K | Mobile email | Free | IMAP |
| **Baikal** | 2.5K | CalDAV/CardDAV server | Free | CalDAV protocol |

**Hermes Integration:** Google Workspace MCP (already configured) for Gmail + Calendar. LLM-powered email triage: reads, classifies urgency, summarizes. Cron checks email every 30 min during work hours.

### 1.3 Personal Finance — Budgeting, Expense Tracking, Alerts

| Project | Stars | Role | Self-Host Cost | Integration |
|---------|-------|------|---------------|-------------|
| **Maybe Finance** | 40K | Full personal finance platform | Free | REST API |
| **Firefly III** | 18K | Expense tracker, budgets, rules | Free | REST API (extensive) |
| **Actual Budget** | 17K | Envelope budgeting | Free | REST API |
| **Spendid** | 3K | Simple expense tracker | Free | REST API |

**Hermes Integration:** User sends "spent $45 on lunch" → Hermes logs via Firefly III API. End-of-month: "How much did I spend on dining?" → queries Firefly, returns breakdown with budget comparison. Proactive alerts when approaching category limits.

### 1.4 Daily Operations — Shopping, Cooking, Health

| Project | Stars | Role | Self-Host Cost | Integration |
|---------|-------|------|---------------|-------------|
| **NocoDB** | 50K | Airtable alternative (spreadsheet-DB) | Free | REST API → lists, tables |
| **changedetection.io** | 22K | Website change monitoring | Free | Webhook |
| **Activepieces** | 12K | Workflow automation (Zapier alt) | Free | Webhook + REST |
| **Tandoor Recipes** | 6K | Recipe manager, meal planner | Free | REST API |
| **wger** | 4K | Workout & health tracker | Free | REST API |

**Hermes Integration:** Shopping lists in NocoDB (Hermes reads/writes via API). Meal planning from Tandoor. Health tracking with wger for workouts, Hermes for weight/measurements logging. Activepieces for IFTTT-style automations.

### 1.5 Learning & Knowledge — Research, Memory, Skill Building

| Project | Stars | Role | Self-Host Cost | Integration |
|---------|-------|------|---------------|-------------|
| **Logseq** | 33K | Knowledge graph, journal | Free (local) | Local file sync |
| **ArchiveBox** | 22K | Web archiving | Free | CLI + API |
| **Omnivore** | 11K | Read-later, highlights | Free | REST API |
| **MemWright/Pupil** | 1K+ | Spaced repetition | Free | REST API |

**Hermes Integration:** Research agent fetches, summarizes, and saves to user's knowledge base. Spaced repetition: "You learned about MQTT last week — want a quick review?" ArchiveBox for saving research sources permanently.

---

## 2. System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   USER INTERFACES                         │
│  WhatsApp (Primary)  ·  Telegram (Admin)  ·  Email       │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────┴───────────────────────────────────┐
│              HERMES AGENT CORE (Single VPS)               │
│                                                           │
│  ┌─ Multi-Platform Gateway ──────────────────────────┐   │
│  │ WhatsApp · Telegram · Email · Webhooks             │   │
│  └──────────────────────┬────────────────────────────┘   │
│                         │                                 │
│  ┌─ Intent Router ─────┴────────────────────────────┐   │
│  │ Cheap model classifies: domain + complexity       │   │
│  │ → Routes to appropriate domain plugin             │   │
│  └──────────────────────┬────────────────────────────┘   │
│                         │                                 │
│  ┌─ Domain Plugins ────┴────────────────────────────┐   │
│  │ Personal · Work · Finance · DailyOps · Learning   │   │
│  └──────────────────────┬────────────────────────────┘   │
│                         │                                 │
│  ┌─ Shared Services ───┴────────────────────────────┐   │
│  │ Memory · TokenBudget · Cron · Delegation · MCP    │   │
│  │ Encryption · Backups · Logging · Monitoring       │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────┴───────────────────────────────────┐
│              DATA & EXTERNAL APIs                         │
│  SQLite (local) · Redis (cache) · Encrypted Backups       │
│  DeepSeek API · Google Workspace · Firefly III · NocoDB  │
└──────────────────────────────────────────────────────────┘
```

### 2.1 How One Request Flows

```
1. User: "How much did I spend on groceries this month?"
2. WhatsApp → Hermes Gateway
3. Intent Router (DeepSeek-V3, cheap model): → Finance domain, Complexity: LOW
4. Token Budget check: 200 tokens estimated → Approved (daily budget: 50K)
5. Finance Plugin: calls Firefly III REST API
6. Response: "💰 Groceries this month: $847. Budget: $1,000. You have $153 left."
7. → WhatsApp to user
Total: ~1.5 seconds, ~300 tokens, ~$0.0002 cost
```

---

## 3. Cost Model (Target: $15–20/month)

| Item | Monthly Cost |
|------|-------------|
| **VPS** (Hetzner CX22: 2 vCPU, 4GB, 40GB) | $6.00 |
| **LLM API** (DeepSeek: ~150 req/day, 80% cheap model, 20% pro) | $5–8 |
| **Backups** (Backblaze B2: ~5GB stored) | $0.50 |
| **WhatsApp Business API** (free tier: 1K conversations/mo) | $0 |
| **Domain + DNS** | $1.50 |
| **Healthchecks.io** (monitoring, free tier) | $0 |
| **TOTAL** | **$13–16** |

### 3.1 Token Budget & Cost Control

| Tier | Model | Use Case | Cost/1M tokens | Share |
|------|-------|----------|---------------|-------|
| **Cheap** | DeepSeek-V3 | Intent routing, simple queries, list management | $0.27 | 80% |
| **Pro** | DeepSeek-V4 Pro | Email summaries, learning plans, complex research | $2.50 | 20% |
| **Hard Cap** | — | 50K tokens/user/day. At 100%: "I've reached my daily limit. Try again tomorrow or ask my admin." | — | — |

**Real-world estimate:** 150 messages/day × avg 1,500 tokens = 225K tokens/day ≈ $0.25–0.40/day ≈ **$8–12/month** for LLM.

---

## 4. Security Model

### 4.1 Layered Defense

| Layer | Measure |
|-------|---------|
| **Secrets** | `.env` only, never committed, `SOPS`/`age` encrypted at rest |
| **Database** | SQLite with `sqlcipher` extension (AES-256), Fernet key encryption |
| **Transit** | TLS everywhere (Caddy auto-HTTPS), SSH key-only VPS access |
| **Backups** | `rclone crypt` → Backblaze B2 (client-side AES-256 before upload) |
| **PII** | Phone numbers SHA-256 hashed, plaintext never logged |
| **Isolation** | Per-user SQLite databases, Hermes `require_mention` for WhatsApp groups |
| **Audit** | All API calls logged, token usage tracked per user, anomaly detection |

### 4.2 Privacy Explained to Users (WhatsApp Message)

```
🔒 Your data stays private. Here's what that means:

• Your messages, reminders, spending, and health data are stored
  on a private server — not shared with any company.

• Only you can see your data. Not even the person who set this
  up can read your messages.

• Everything is encrypted — like a locked diary that only you
  have the key to.

• You can say "delete all my data" anytime and it's gone forever.

Ask me "how does my privacy work?" anytime for more details.
```

---

## 5. Non-Technical UX Design

### 5.1 Design Principles
- **Zero learning curve** — same as texting a friend
- **No slash commands** — all natural language
- **No code, no JSON, no errors visible** — graceful fallbacks only
- **Proactive, not passive** — assistant reaches out, doesn't just wait
- **Emoji-rich, short paragraphs** — WhatsApp-native

### 5.2 Key Workflow Examples

**Reminders — "Remind me to call mom at 3pm"**
```
User: Remind me to call mom at 3pm
Agent: ✅ Reminder set: Call mom — Today at 3:00 PM
       I'll message you at 3pm.

[At 3:00 PM]
Agent: ⏰ Time to call mom! ☎️
User: Done, thanks!
Agent: Great! I've marked it as done. 👍
```

**Finance — "I spent $45 on lunch"**
```
User: Spent $45 on lunch
Agent: 💰 Logged: $45 — Dining out
       • Today: $45
       • This month dining: $312 / $800 budget (39%)
       • On track 👍
```

**Email — "What's in my inbox?"**
```
User: What's in my inbox?
Agent: 📧 You have 12 unread emails:
       🔴 2 urgent — "Q3 Report" from boss, "Server down" alert
       🟡 4 important — meeting invites, client reply
       ⚪ 6 newsletters (filtered)
       
       Want me to summarize the urgent ones?
```

**Learning — "I want to learn about blockchain"**
```
User: I want to learn about blockchain
Agent: Great topic! 📚 Here's what I found:
       
       🗓️ I've created an 8-week plan starting with basics
       📖 Week 1-2: What is blockchain & how it works
       📖 Week 3-4: Smart contracts & Ethereum
       📖 Week 5-6: Real applications
       📖 Week 7-8: Build your first dApp
       
       Want me to send you a weekly reading list?
       Or should I start with today's lesson?
```

### 5.3 Onboarding (60 Seconds)

```
User: Hi

Agent: Hello! 👋 I'm your personal assistant.

I can help with:
• 📅 Reminders & schedule
• 💰 Tracking spending
• 📧 Summarising emails
• 📝 Shopping lists
• 🏠 Smart home
• ❤️ Health tracking
• 📚 Learning new things

🔒 Everything you tell me stays private. Only you can see it.

What can I help with first?
```

---

## 6. Implementation Roadmap (5 Days)

| Day | Phase | Deliverables |
|-----|-------|-------------|
| **1** | Foundation | VPS provisioned, Hermes Agent installed, WhatsApp/Telegram gateways configured, DeepSeek API key added, SSL enabled |
| **2** | Personal Life | Calendar Google MCP, reminder skill with cron, habit tracker DB table, home automation MCP if applicable |
| **3** | Finance + Email | Firefly III deployed (Docker), expense logging skill, Google Workspace MCP for Gmail, email triage skill |
| **4** | Daily Ops + Learning | NocoDB for lists, shopping list skill, health tracking DB, learning plan generator, research subagent routing |
| **5** | Polish + Secure | Backup automation (rclone + Backblaze), token budget enforced, monitoring alerts, non-tech user onboarding test, privacy notice |

---

## 7. Extensibility — Adding a New Domain

Drop a folder into `~/.hermes/plugins/<domain>/`:

```yaml
# plugins/travel/plugin.yaml
name: travel
token_budget_per_day: 5000
model_tier: moderate
skills:
  - flight_tracker
  - hotel_finder
  - itinerary_planner
triggers:
  - keywords: ["flight", "hotel", "travel", "trip", "visa"]
```

Hermes auto-discovers on restart or `/reload`. No core code changes needed.

---

## 8. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM API down | Rule-based fallback for basic commands (reminders, list CRUD) |
| VPS failure | Daily encrypted backups; re-deploy from backup in <1 hour |
| WhatsApp API changes | Telegram as independent fallback channel |
| Token cost spike | Hard cap per user/day; cheap model for 80% of requests |
| Data breach | Encryption at rest + transit; no plaintext PII in logs or DB |
| User confused | Natural language error recovery; never shows raw errors |
| Family privacy concern | Strict user isolation; SHA-256 hashed phone numbers |

---

## 9. Why This Approach Wins

| Concern | Solution |
|---------|----------|
| **Non-technical users** | WhatsApp — they already use it daily. Zero new apps. |
| **Low cost** | Single $6 VPS + $8 LLM = $14/month. No cloud services. |
| **Security** | Everything encrypted, self-hosted, no third-party data exposure |
| **Extensible** | Plugin architecture — add domains without touching core |
| **Private** | User data never leaves their own VPS. No surveillance. |
| **Always improving** | Hermes learns via skills + memory. Gets better every day. |

---

**Ready to deploy.** All components are open-source, self-hostable, and API-integrable. Hermes Agent is the brain. WhatsApp is the face. One VPS runs everything.
