# Deploying to DigitalOcean

Switched from Fly.io: Fly's terms have language against sexually explicit content and nobody
had written confirmation it was actually fine for this site. DigitalOcean explicitly allows
legal adult content, so there's no ambiguity to worry about later.

Terraform provisions: a Droplet (with Docker pre-installed via cloud-init), a firewall (only
ports 22 and 8080 open, Postgres never exposed publicly), an SSH key, and a private container
registry to hold the built image. Postgres runs as a container on the same Droplet via
`docker-compose.yml`, not DigitalOcean's managed database product — the managed DB alone starts
around $15/month, more than the whole budget discussed with the client. Self-hosting Postgres
on the same box keeps the total closer to just the Droplet's ~$6/month.

## One-time setup

```bash
export DIGITALOCEAN_TOKEN=<personal access token, from DO dashboard → API → Generate New Token>
```

## 1. Provision the Droplet, firewall, and registry with Terraform

```bash
cd infra
terraform init
terraform plan -var="ssh_public_key=$(cat ~/.ssh/id_ed25519.pub)"
terraform apply -var="ssh_public_key=$(cat ~/.ssh/id_ed25519.pub)"
```

Note the `droplet_ip` and `registry_endpoint` outputs, both needed below.

## 2. Build and push the image to the registry

```bash
cd ../backend
doctl registry login
docker build -t <registry_endpoint>/kumo-kosmos-backend:latest .
docker push <registry_endpoint>/kumo-kosmos-backend:latest
```

## 3. Deploy on the Droplet

SSH in (`ssh root@<droplet_ip>`) and set up the running containers:

```bash
doctl registry login   # so the droplet itself can pull the private image
mkdir -p /opt/app && cd /opt/app
# copy docker-compose.yml here (scp it up, or paste it)

export POSTGRES_PASSWORD=$(openssl rand -hex 24)
export SECRET_KEY=$(openssl rand -hex 32)
export APP_IMAGE=<registry_endpoint>/kumo-kosmos-backend:latest

docker compose up -d
```

`start.sh` (the container's entrypoint) runs `alembic upgrade head` before starting the app on
every start, so migrations apply automatically, no separate release step needed like Fly had.

Confirm it's healthy:

```bash
curl http://<droplet_ip>:8080/health
```

## Redeploying after a code change

```bash
docker build -t <registry_endpoint>/kumo-kosmos-backend:latest .
docker push <registry_endpoint>/kumo-kosmos-backend:latest
ssh root@<droplet_ip> "cd /opt/app && docker compose pull && docker compose up -d"
```

## Secrets

`POSTGRES_PASSWORD` and `SECRET_KEY` live only in the Droplet's shell environment when
`docker compose up` runs, never in Terraform state or committed anywhere. Once the client's
CCBill details are in hand, add `CCBILL_CLIENT_ACCOUNT` etc. the same way, as additional
environment variables in the compose invocation.

## DNS (kumokosmos.com) and HTTPS

This setup serves plain HTTP on port 8080 for now, fine for testing. Before real launch: point
`kumokosmos.com` at the Droplet's IP (an A record), and put a reverse proxy (Caddy or nginx +
certbot) in front of the app container for HTTPS — not built yet, this is testing-only as is.
