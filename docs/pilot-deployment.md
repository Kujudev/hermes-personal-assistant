# Pilot Deployment — paserver.kujuhk.com

## Prerequisites

- Server with Docker and Docker Compose v2
- DNS: `paserver.kujuhk.com` → server IP (`203.198.112.72`)
- Ports 80 and 443 open on firewall

## One-time setup on server

```bash
# Install Docker (Ubuntu/Debian example)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in
```

## Configure secrets locally

```bash
cp .env.example .env
# Edit .env — set DEEPSEEK_API_KEY, PILOT_PIN (recommended), CADDY_EMAIL
```

**Never commit `.env`.**

## Deploy from your machine

```bash
chmod +x scripts/deploy_pilot.sh
./scripts/deploy_pilot.sh
```

The script:
1. Rsyncs code to `~/hermes-pilot` on the server
2. Uploads `.env` securely via SCP
3. Runs `docker compose -f infra/docker-compose.pilot.yml up -d --build`

## Verify

```bash
curl https://paserver.kujuhk.com/health
# {"status":"ok","llm":"enabled"}
```

Open `https://paserver.kujuhk.com` in your phone browser → Add to Home Screen.

## Pilot soak

Log daily feedback in `docs/pilot-feedback/YYYY-MM-DD.md`.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| SSH auth fails | Verify password/key; ensure `PasswordAuthentication yes` in `sshd_config` |
| TLS fails | Confirm DNS propagated; check `docker logs infra-caddy-1` |
| LLM disabled | Set `DEEPSEEK_API_KEY` in `.env` and redeploy |
| Reminders not firing | Check `docker logs infra-reminder-worker-1` |

## Security note

If credentials were shared in chat or email, **rotate your SSH password and DeepSeek API key** after first successful deploy.
