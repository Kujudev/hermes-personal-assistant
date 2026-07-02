# Hermes Personal AI Assistant

Planning repository for a WhatsApp-first personal AI assistant powered by [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Development

```bash
pip install -e ".[dev]"
pytest -v
docker compose -f docker-compose.dev.yml up -d redis
```

### Pilot deploy (Phase 1)

```bash
cp .env.example .env   # fill in secrets
./scripts/deploy_pilot.sh
```

- **Web chat:** https://paserver.kujuhk.com (WhatsApp-style UI until WhatsApp API is ready)
- See [docs/pilot-interfaces.md](./docs/pilot-interfaces.md) and [docs/pilot-deployment.md](./docs/pilot-deployment.md)
- If port 80/443 is already occupied on your server, see the reverse-proxy fallback in `docs/pilot-deployment.md`

### Layout

| Path | Description |
|------|-------------|
| `services/hermes_core/` | Core assistant services (router, budget, reminders, gateway mock) |
| `tests/guardrails/` | Architecture guardrail tests (`GR-*`) |
| `tests/acceptance/` | User-story acceptance tests (`ACC-*`) |
| `tests/unit/` | Unit tests |
| `tests/integration/` | Gateway mock and integration tests |
| `infra/` | Infrastructure notes and future deploy configs |
| `scripts/check_secrets.sh` | GR-SEC-03 secret scanner |

## Plans

| Document | Description |
|----------|-------------|
| [Development_Roadmap.md](./Development_Roadmap.md) | **Test-driven delivery roadmap** — phased plan, staging/production strategy, architecture guardrails, pilot protocol (you as Phase 1 user) |
| [Hermes_Personal_AI_Assistant_Master_Plan.md](./Hermes_Personal_AI_Assistant_Master_Plan.md) | Single-VPS personal assistant — domains, architecture, cost model, security, UX, and 5-day implementation roadmap |
| [Aide_MultiTenant_AI_Assistant_PoC.md](./Aide_MultiTenant_AI_Assistant_PoC.md) | Multi-tenant **Aide** product PoC — PostgreSQL + Traefik + Zitadel + NextCloud + Lago stack for 10-user proof of concept |

## Summary

- **Interface:** WhatsApp (primary), with Telegram and email as secondary channels
- **Engine:** Hermes Agent with DeepSeek V4 Pro
- **Target users:** Non-technical family members, colleagues, and HK professionals
- **Budget:** $15–20/month (personal) · tiered SaaS pricing for Aide PoC
