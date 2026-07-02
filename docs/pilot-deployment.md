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
3. Runs `docker compose --env-file ../.env -f infra/docker-compose.pilot.yml up -d --build`

## Verify

```bash
curl https://paserver.kujuhk.com/health
# {"status":"ok","llm":"enabled"}
```

Open `https://paserver.kujuhk.com` in your phone browser → Add to Home Screen.

## Pilot soak

Log daily feedback in `docs/pilot-feedback/YYYY-MM-DD.md`.

## Troubleshooting

### Port 80/443 already in use

If deploy fails with:

```text
failed to bind host port 0.0.0.0:80/tcp: address already in use
```

your server already has another service listening on port 80, 443, or both.

Check what is using those ports:

```bash
sudo ss -ltnp '( sport = :80 or sport = :443 )'
```

You have two valid fixes:

#### Option A — let Hermes Caddy own 80/443

Stop the existing web server, then redeploy:

```bash
sudo systemctl stop nginx || true
sudo systemctl stop apache2 || true
cd ~/hermes-pilot/infra
docker compose -f docker-compose.pilot.yml up -d --build
```

Use this when `paserver.kujuhk.com` should be dedicated to Hermes.

#### Option B — keep your existing reverse proxy

If you already run Nginx, Apache, or another Caddy on the host, leave it on 80/443 and change `.env`:

```bash
CADDY_HTTP_BIND=8080
CADDY_HTTPS_BIND=8443
PILOT_API_BIND=127.0.0.1:18000
```

Then redeploy:

```bash
./scripts/deploy_pilot.sh
```

Now make your existing reverse proxy forward `paserver.kujuhk.com` to:

```text
http://127.0.0.1:8080
```

Example Nginx snippet:

```nginx
server {
    server_name paserver.kujuhk.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

If you prefer to bypass Hermes Caddy entirely, proxy directly to:

```text
http://127.0.0.1:18000
```

### PUBLIC_DOMAIN blank / Caddy keeps restarting

If `docker compose ps` shows `infra-caddy-1` restarting and logs say:

```text
server block without any key is global configuration
```

then Compose is not loading the parent `.env`, so `PUBLIC_DOMAIN` is blank.

Start it like this from `~/hermes-pilot/infra`:

```bash
docker compose --env-file ../.env -f docker-compose.pilot.yml up -d --build
docker compose --env-file ../.env -f docker-compose.pilot.yml ps
```

| Issue | Fix |
|-------|-----|
| SSH auth fails | Verify password/key; ensure `PasswordAuthentication yes` in `sshd_config` |
| TLS fails | Confirm DNS propagated; check `docker logs infra-caddy-1` |
| Port 80/443 already in use | Stop the existing listener or set `CADDY_HTTP_BIND=8080` and proxy to `127.0.0.1:8080` |
| `PUBLIC_DOMAIN` blank / Caddy restarts | Start compose with `--env-file ../.env` |
| LLM disabled | Set `DEEPSEEK_API_KEY` in `.env` and redeploy |
| Reminders not firing | Check `docker logs infra-reminder-worker-1` |

## Security note

If credentials were shared in chat or email, **rotate your SSH password and DeepSeek API key** after first successful deploy.
