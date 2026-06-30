# Hermes / Aide — Test-Driven Development Roadmap

**Author:** Chi Ho Leung · Hong Kong (HKT)  
**Status:** Living document — update at each phase gate  
**Principle:** No feature ships without a failing test first. No phase advances without exit-criteria tests passing.

---

## 1. Executive Summary

This roadmap turns the two existing plans ([Personal Master Plan](./Hermes_Personal_AI_Assistant_Master_Plan.md) and [Aide PoC](./Aide_MultiTenant_AI_Assistant_PoC.md)) into a **sequential, test-gated delivery program**.

| Phase | Name | Goal | Primary Environment |
|-------|------|------|---------------------|
| **0** | Foundations | Test harness, CI, architecture guardrails | Local dev |
| **1** | Pilot MVP | **You** taste full UX on WhatsApp before anyone else | Pilot (local server) |
| **2** | Personal Production | Family / close colleagues on hardened single-tenant stack | Production (personal) |
| **3** | Aide PoC | 10-user multi-tenant proof | Staging → limited prod |
| **4** | Aide Production | Paid tiers, HK market launch | Production (SaaS) |

**Why test-first:** Architectural bugs (tenant leakage, token budget bypass, data isolation failure) are expensive to fix after users depend on the system. Tests are the contract that locks architecture before UX polish hides structural problems.

**Why pilot-first (Phase 1):** You validate natural-language flows, latency, reminder reliability, and privacy messaging on real WhatsApp before onboarding non-technical users. UX feedback from Phase 1 directly reshapes Phase 2 scope — avoiding costly rework.

---

## 2. Core Principles

### 2.1 Test-Driven Development (TDD) Rules

1. **Red → Green → Refactor** for every capability: write a failing test, implement minimum code, refactor with tests green.
2. **Architecture tests before features:** isolation, auth, encryption, and budget enforcement tests exist in Phase 0 — they must never be deleted, only strengthened.
3. **No “manual only” critical paths:** reminders, expense logging, email triage, and file indexing each have automated acceptance tests.
4. **Contract tests for every external integration:** Hermes ↔ Firefly III, Google MCP, NextCloud, Zitadel, Lago — mock in unit tests, verify against real services in staging.
5. **Regression suite runs on every commit:** a failing guardrail test blocks merge.

### 2.2 Environment Discipline

| Environment | Purpose | Data | Who Uses It |
|-------------|---------|------|-------------|
| **Local dev** | Fast iteration, unit + integration tests | Synthetic / fixtures only | Developer |
| **Pilot** | Phase 1 — your real WhatsApp UX trial | Your real (consented) data | You only |
| **Staging** | Pre-release validation, load smoke tests | Anonymized copy or synthetic | You + automated CI |
| **Production** | Live users | Real user data | Pilot user(s) → family → paying customers |

> **Note:** Local machine and company domain details will be wired in when you return to office. Until then, environments are defined by role, not hostname.

### 2.3 Phase Gate Rule

A phase **does not start** until the previous phase’s **exit-criteria test suite** is 100% green in the target environment.

---

## 3. Test Architecture

### 3.1 Test Pyramid

```
                    ┌─────────────┐
                    │  E2E / UX   │  ← WhatsApp flow sims, onboarding scripts
                   ┌┴─────────────┴┐
                   │  Acceptance  │  ← Gherkin-style user stories per domain
                  ┌┴───────────────┴┐
                  │  Integration    │  ← API contracts, DB, Redis, webhooks
                 ┌┴─────────────────┴┐
                 │  Architecture     │  ← Tenant isolation, auth, encryption, budgets
                ┌┴───────────────────┴┐
                │  Unit                 │  ← Parsers, routers, formatters, validators
                └───────────────────────┘
```

### 3.2 Architecture Guardrail Tests (Non-Negotiable)

These tests prevent **destructive architectural bugs**. They are created in Phase 0 and run forever.

| Guardrail ID | What It Protects | Example Assertion |
|--------------|------------------|-------------------|
| **GR-ISO-01** | User data isolation | User A's reminder query returns zero rows for User B |
| **GR-ISO-02** | Tenant RLS (Phase 3+) | SQL without `tenant_id` context returns empty / errors |
| **GR-ISO-03** | Filesystem isolation | Profile path for tenant X cannot read tenant Y files |
| **GR-AUTH-01** | Unauthenticated rejection | API without valid JWT returns 401 |
| **GR-AUTH-02** | Cross-tenant token reuse | JWT for tenant A rejected on tenant B routes |
| **GR-BUDGET-01** | Token hard cap | Request exceeding daily limit returns user-friendly message, no LLM call |
| **GR-BUDGET-02** | Budget counter accuracy | After N messages, Redis/DB counter matches sum of logged usage |
| **GR-SEC-01** | No plaintext PII in logs | Log scan finds no raw phone numbers or email bodies |
| **GR-SEC-02** | Encryption at rest | DB/file blobs are not readable without key |
| **GR-SEC-03** | Secrets not in repo | CI secret scanner passes |
| **GR-DEL-01** | Right to erasure | `delete all my data` removes DB rows, files, and cache keys |
| **GR-CRON-01** | Reminder delivery | Scheduled job fires within ±60s of target time |
| **GR-CRON-02** | Idempotent cron | Duplicate cron tick does not double-send reminder |

### 3.3 Acceptance Test Catalog (By Domain)

Each user-facing capability gets a test **before** implementation.

#### Personal Life
| Test ID | User Story | Pass Criteria |
|---------|------------|---------------|
| ACC-PL-01 | "Remind me to call mom at 3pm" | Confirmation message; push at 3pm ±1 min |
| ACC-PL-02 | "What reminders do I have today?" | Lists only current user's reminders |
| ACC-PL-03 | "Cancel the mom reminder" | Reminder removed; no fire at 3pm |

#### Finance
| Test ID | User Story | Pass Criteria |
|---------|------------|---------------|
| ACC-FIN-01 | "Spent $45 on lunch" | Firefly entry created; budget summary in reply |
| ACC-FIN-02 | "How much on dining this month?" | Correct category total; budget % shown |
| ACC-FIN-03 | Over-budget alert | Proactive message when category > 80% |

#### Work / Email
| Test ID | User Story | Pass Criteria |
|---------|------------|---------------|
| ACC-WK-01 | "What's in my inbox?" | Urgency-classified summary; no full email bodies leaked to logs |
| ACC-WK-02 | "Summarize the urgent ones" | Summaries only for flagged messages |

#### Daily Ops
| Test ID | User Story | Pass Criteria |
|---------|------------|---------------|
| ACC-DO-01 | "Add milk to shopping list" | NocoDB row created; list query returns milk |
| ACC-DO-02 | "Remove milk from list" | Row deleted |

#### Learning
| Test ID | User Story | Pass Criteria |
|---------|------------|---------------|
| ACC-LR-01 | "I want to learn about blockchain" | Structured multi-week plan returned |
| ACC-LR-02 | Follow-up lesson request | Plan context preserved in conversation |

#### Privacy / UX
| Test ID | User Story | Pass Criteria |
|---------|------------|---------------|
| ACC-UX-01 | "Hi" (first message) | Onboarding menu under 60s read time; no jargon |
| ACC-UX-02 | "How does my privacy work?" | Privacy explainer matches approved copy |
| ACC-UX-03 | Gibberish input | Graceful recovery; no stack trace or JSON |
| ACC-UX-04 | Response latency | p95 < 5s for LOW complexity intents in pilot |

### 3.4 Tooling Recommendations

| Layer | Tool | Role |
|-------|------|------|
| Unit / integration | `pytest` | Python services, Hermes skills, API handlers |
| Architecture | `pytest` + testcontainers | Postgres, Redis in CI |
| Contract | `pytest` + recorded fixtures | External API shape validation |
| E2E gateway | Hermes gateway test mode or webhook replay | Simulates WhatsApp inbound/outbound |
| CI | GitHub Actions | Run guardrails + acceptance on every PR |
| Load smoke | `k6` or `locust` (Phase 3+) | 10-user concurrent message simulation |
| Log PII scan | Custom CI step / `gitleaks` | GR-SEC-01, GR-SEC-03 |

---

## 4. Phase 0 — Foundations (Test Harness & Skeleton)

**Duration guide:** 3–5 working days  
**Environment:** Local dev  
**User:** Developer only

### 4.1 Deliverables

- [ ] Monorepo layout: `services/`, `tests/`, `infra/`, `docs/`
- [ ] `docker-compose.dev.yml` — Hermes Agent + SQLite + Redis (minimal)
- [ ] CI pipeline: lint → unit → guardrail → integration
- [ ] All **GR-*** guardrail tests written (initially skipped or failing)
- [ ] Test fixtures: synthetic users, phone hashes, sample messages
- [ ] WhatsApp gateway **mock/replay** harness for automated E2E without real Meta API in CI
- [ ] Environment config template (`.env.example`) — no real secrets

### 4.2 Exit Criteria (Phase 0 → Phase 1)

| # | Criterion | Verified By |
|---|-----------|-------------|
| 1 | CI green on empty/minimal implementation | GitHub Actions |
| 2 | GR-SEC-03 passes | Secret scanner |
| 3 | Gateway mock can inject a message and capture outbound reply | E2E harness test |
| 4 | Intent router unit tests pass for domain classification | Unit suite |
| 5 | Token budget service unit tests pass (approve / deny) | Unit suite |

---

## 5. Phase 1 — Pilot MVP (You as Sole Test User)

**Duration guide:** 5–7 working days build + **7–14 days pilot soak**  
**Environment:** Pilot (deployed on your local server when ready)  
**User:** **You only** — real WhatsApp, real workflows, structured feedback

This is the most important phase for UX. Nothing else ships to family or customers until you sign off.

### 5.1 Scope (Minimum Lovable Pilot)

| Priority | Feature | Why in Pilot |
|----------|---------|--------------|
| P0 | WhatsApp send/receive | Core channel |
| P0 | Onboarding flow (ACC-UX-01) | First impression |
| P0 | Reminders (ACC-PL-01–03) | Proves cron + push reliability |
| P0 | Privacy explainer (ACC-UX-02) | Trust before real data |
| P0 | Token budget display / soft cap | Cost control feedback |
| P1 | Expense logging (ACC-FIN-01–02) | Firefly integration proof |
| P1 | Shopping list (ACC-DO-01–02) | Simple CRUD + NLU |
| P2 | Email triage summary (ACC-WK-01) | Higher complexity; validate latency |
| P2 | Telegram admin `/status` | Ops visibility without exposing admin to family |

**Explicitly out of Phase 1:** multi-tenancy, billing, NextCloud drive, family accounts, public signup.

### 5.2 Test-First Build Order

For each feature, follow this sequence:

```
1. Write acceptance test (ACC-*)
2. Write integration test (API / DB)
3. Implement Hermes skill / plugin
4. Run full suite locally
5. Deploy to pilot environment
6. Manual WhatsApp verification (you)
7. Log UX feedback entry (see §5.4)
```

### 5.3 Pilot Deployment Topology

```
┌─────────────────────────────────────────┐
│  PILOT (your local server — TBD host)   │
│                                         │
│  Hermes Agent (single profile: pilot)   │
│  SQLite + Redis                         │
│  Firefly III (Docker)                   │
│  NocoDB (Docker)                        │
│  Caddy / reverse proxy (TLS when domain │
│    is configured)                       │
└─────────────────────────────────────────┘
         │
         ▼
   WhatsApp (your number only)
   Telegram (admin channel — you only)
```

### 5.4 Pilot Feedback Protocol

During the 7–14 day soak, record feedback daily in `docs/pilot-feedback/YYYY-MM-DD.md`:

| Field | Example |
|-------|---------|
| **Scenario** | Set reminder via voice-of-text |
| **Input** | "Remind me to submit report Friday 5pm" |
| **Expected** | Confirmation with correct timezone (HKT) |
| **Actual** | … |
| **Severity** | Blocker / Major / Minor / Nit |
| **Test gap?** | Should this become ACC-* or GR-*? |

**Weekly pilot review checklist:**
- [ ] Any reminder missed or duplicated?
- [ ] Any response > 5s without explanation?
- [ ] Any message confusing to a non-technical reader?
- [ ] Token spend within expected range?
- [ ] Would you trust a family member using this today?

### 5.5 Exit Criteria (Phase 1 → Phase 2)

| # | Criterion | Verified By |
|---|-----------|-------------|
| 1 | All P0 acceptance tests green in pilot | Automated + your sign-off |
| 2 | ≥ 80% P1 acceptance tests green | Test suite |
| 3 | Zero open **Blocker** UX items | Pilot feedback log |
| 4 | GR-ISO-01, GR-BUDGET-01, GR-CRON-01, GR-SEC-01 pass in pilot | Guardrail suite |
| 5 | 7 consecutive days with no missed P0 reminders | Pilot soak log |
| 6 | **Written pilot sign-off** from you | `docs/pilot-signoff.md` |

---

## 6. Phase 2 — Personal Production (Family & Colleagues)

**Duration guide:** 5–10 working days + 2 week soak  
**Environment:** Production (personal)  
**Users:** 3–10 trusted non-technical users

### 6.1 Scope Additions

- Per-user isolation (separate SQLite DBs or strict user_id scoping)
- User onboarding script (invite by phone hash)
- Email triage (ACC-WK-01–02) production-ready
- Learning plan generator (ACC-LR-01–02)
- Backup automation: `rclone crypt` → Backblaze B2
- Monitoring: Healthchecks.io + disk/RAM alerts via Telegram
- GR-DEL-01 erasure flow

### 6.2 Staging for Personal Production

Even on a single machine, maintain a **staging profile**:

| Aspect | Staging | Production |
|--------|---------|------------|
| Hermes profile | `staging` | `prod` |
| Database | `staging.db` | `prod.db` |
| WhatsApp | Your second number or sandbox | Real user numbers |
| External APIs | Firefly/NocoDB staging containers | Production containers |
| Promotion | All tests green → manual promote | — |

**Promotion checklist:**
1. Full regression green on staging
2. Backup restore drill passed (see §8.2)
3. Deploy to prod during low-traffic window (HKT evening)
4. Smoke test ACC-PL-01 on prod
5. Monitor 24h before inviting family

### 6.3 Exit Criteria (Phase 2 → Phase 3)

| # | Criterion | Verified By |
|---|-----------|-------------|
| 1 | All ACC-* and GR-* tests green | CI + staging |
| 2 | ≥ 3 family/colleague users onboarded | User list |
| 3 | Backup restore drill < 1 hour | Drill log |
| 4 | No cross-user data leakage in manual audit | GR-ISO-01 + spot check |
| 5 | Monthly cost within $15–20 budget | Cost log |

---

## 7. Phase 3 — Aide PoC (Multi-Tenant, 10 Users)

**Duration guide:** 10–15 working days + 4 week beta  
**Environment:** Staging → limited production  
**Users:** 10 HK professionals (invite-only)

### 7.1 Scope

Full stack from [Aide PoC plan](./Aide_MultiTenant_AI_Assistant_PoC.md):

- Traefik + Zitadel + PostgreSQL (RLS) + Redis + NextCloud + Lago
- Hermes multi-profile (one per tenant)
- Token budget enforcement per plan tier
- File indexing pipeline (photo → OCR → NextCloud → DB)
- Cross-device: WhatsApp + Telegram + web dashboard (billing only)
- Admin Telegram commands (`/status`, `/tenants`, `/budget`)

### 7.2 Additional Guardrail Tests (Phase 3)

| Guardrail ID | Assertion |
|--------------|-----------|
| GR-ISO-02 | RLS blocks cross-tenant reads even with raw SQL |
| GR-ISO-03 | NextCloud path traversal cannot access other tenant |
| GR-AUTH-02 | Cross-tenant JWT rejected |
| GR-BUDGET-02 | Per-tenant counters independent |
| GR-RATE-01 | Traefik rate limit triggers at 100 req/min/tenant |

### 7.3 Staging vs Production (Aide)

```
┌──────────────── STAGING ────────────────┐
│ Full Docker Compose stack             │
│ Synthetic tenants (10 fixtures)       │
│ Stripe test mode · Lago sandbox       │
│ k6 load test: 10 concurrent users     │
└───────────────────────────────────────┘
                    │ promote
                    ▼
┌──────────────── PRODUCTION (limited) ───┐
│ Same compose shape, production secrets  │
│ 10 real invite-only users               │
│ Stripe live · Lago production         │
│ Real WhatsApp Business API              │
└───────────────────────────────────────┘
```

### 7.4 Exit Criteria (Phase 3 → Phase 4)

| # | Criterion | Verified By |
|---|-----------|-------------|
| 1 | All GR-* including RLS tests green | CI |
| 2 | 10 users onboarded, ≥ 8 active weekly | Analytics |
| 3 | k6 smoke: p95 latency < 8s at 10 concurrent | Load test report |
| 4 | File indexing ACC tests pass for photo + PDF | Acceptance suite |
| 5 | Lago billing: upgrade Free → Pro works | Stripe test |
| 6 | Profitable unit economics at 10 × $8 Pro | Cost vs revenue sheet |

---

## 8. Phase 4 — Aide Production (Public Launch)

**Duration guide:** Ongoing  
**Environment:** Production (SaaS)  
**Users:** Paying customers, HK market

### 8.1 Infrastructure Evolution

| Milestone | Users | Infrastructure |
|-----------|-------|----------------|
| Launch | 100 | Single CX42 + managed backup |
| Growth | 1,000 | k3s cluster (3 nodes) |
| Scale | 10K+ | Citus Postgres, Kong AI Gateway, process-per-tenant-group |

### 8.2 Production Operations

| Practice | Frequency | Test / Drill |
|----------|-----------|--------------|
| Backup | Daily encrypted | Monthly restore drill (GR-REST-01) |
| Guardrail suite | Every deploy | CI blocking |
| Penetration spot-check | Quarterly | Tenant isolation audit |
| Token spend review | Daily | GR-BUDGET-02 + admin `/budget` |
| Dependency updates | Monthly | Full regression |

**GR-REST-01 (add in Phase 2):** Restore from latest backup to clean VM; ACC-PL-01 passes within 60 minutes.

### 8.3 Production Deployment Pipeline

```
PR opened
  → CI: unit + guardrail + acceptance
  → Merge to main
  → Auto-deploy to STAGING
  → Staging regression + load smoke
  → Manual approval (you)
  → Deploy to PRODUCTION (blue/green or rolling)
  → Post-deploy smoke: ACC-UX-01, ACC-PL-01, GR-AUTH-01
  → Rollback on any smoke failure
```

---

## 9. Master Timeline (Indicative)

| Week | Phase | Focus |
|------|-------|-------|
| 1 | 0 | Repo scaffold, CI, guardrail tests, gateway mock |
| 2 | 1 build | P0 features test-first |
| 3 | 1 build | P1 features + pilot deploy |
| 3–4 | 1 soak | **Your pilot** — daily feedback |
| 5 | 2 | Hardening, family onboarding prep |
| 6 | 2 soak | Family users, backup/monitoring |
| 7–8 | 3 build | Multi-tenant stack, RLS, NextCloud |
| 9–10 | 3 soak | 10-user PoC beta |
| 11+ | 4 | Launch prep, marketing, scaling |

> Weeks are indicative sequencing blocks, not calendar commitments. Phase gates matter more than dates.

---

## 10. Risk Register (Test-Mitigated)

| Risk | Likelihood | Impact | Test Mitigation |
|------|------------|--------|-----------------|
| Tenant data leakage | Medium | Critical | GR-ISO-01/02/03 — block deploy if red |
| Token cost runaway | Medium | High | GR-BUDGET-01/02 + daily admin review |
| Reminder silent failure | Medium | High | GR-CRON-01/02 + pilot soak |
| WhatsApp API change | Low | High | Gateway abstraction + contract tests |
| UX unfit for non-technical users | High | High | **Phase 1 pilot** before family |
| Backup unusable | Low | Critical | GR-REST-01 monthly drill |
| Scope creep into Aide before personal works | Medium | High | Phase gates — no Phase 3 until Phase 2 sign-off |

---

## 11. What We Need From You (When Back at Office)

These items are **not blockers** for Phase 0 or test authoring. They are required before Phase 1 pilot deploy:

| Item | Used For |
|------|----------|
| Local server specs / OS | Pilot deployment target |
| Company domain name | TLS, webhooks, optional dashboard |
| WhatsApp Business API credentials | Real pilot channel |
| DeepSeek API key | LLM |
| Google Workspace OAuth (if email in pilot) | ACC-WK-* |
| Preferred timezone confirmation | HKT assumed |

Until then: build and test against mocks locally; plug in real endpoints at pilot deploy time.

---

## 12. Immediate Next Actions

1. **Scaffold repo** — `tests/guardrails/`, `tests/acceptance/`, `services/hermes-skills/`
2. **Implement Phase 0** — CI + failing guardrail tests + gateway mock
3. **Write ACC-PL-01** as first acceptance test (reminder happy path)
4. **Prepare pilot feedback template** — `docs/pilot-feedback/TEMPLATE.md`
5. **Defer** domain/TLS/server binding until you provide office details

---

## 13. Document Index

| Document | Role |
|----------|------|
| [Hermes_Personal_AI_Assistant_Master_Plan.md](./Hermes_Personal_AI_Assistant_Master_Plan.md) | Feature & architecture reference (single-tenant) |
| [Aide_MultiTenant_AI_Assistant_PoC.md](./Aide_MultiTenant_AI_Assistant_PoC.md) | Multi-tenant product & infra reference |
| **This document** | Delivery sequence, test gates, environments, pilot protocol |

---

*Last updated: 2026-06-30*
