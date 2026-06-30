# Hermes Personal AI Assistant

Planning repository for a WhatsApp-first personal AI assistant powered by [Hermes Agent](https://github.com/NousResearch/hermes-agent).

## Plans

| Document | Description |
|----------|-------------|
| [Hermes_Personal_AI_Assistant_Master_Plan.md](./Hermes_Personal_AI_Assistant_Master_Plan.md) | Single-VPS personal assistant — domains, architecture, cost model, security, UX, and 5-day implementation roadmap |
| [Aide_MultiTenant_AI_Assistant_PoC.md](./Aide_MultiTenant_AI_Assistant_PoC.md) | Multi-tenant **Aide** product PoC — PostgreSQL + Traefik + Zitadel + NextCloud + Lago stack for 10-user proof of concept |

## Summary

- **Interface:** WhatsApp (primary), with Telegram and email as secondary channels
- **Engine:** Hermes Agent with DeepSeek V4 Pro
- **Target users:** Non-technical family members, colleagues, and HK professionals
- **Budget:** $15–20/month (personal) · tiered SaaS pricing for Aide PoC
