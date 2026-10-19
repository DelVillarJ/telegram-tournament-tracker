# Docker

Docker deployment instructions are maintained in the repository
[README](../README.md#configuration) and [quick start](../docs/quickstart.md#docker).

The service reads `.env`, mounts the host `data/` directory at `/app/data`, and
runs the bot with Telegram long polling. The webhook port is bound to all host
interfaces by default so Nginx Proxy Manager on another LAN guest can reach the
bot VM on port 8080. Expose it publicly through the TLS reverse proxy, not
directly through router port forwarding to the bot VM. Set
`WEBHOOK_BIND_ADDRESS` to the bot VM's specific LAN address if you prefer to
limit the binding to that interface. Recreate the service after changing
environment variables:

```powershell
docker compose --env-file .env up --detach --build --force-recreate
```

Follow output with `docker compose logs --follow telegram-bot`.
