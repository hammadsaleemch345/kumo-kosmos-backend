terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.46"
    }
  }
}

# Auth: export DIGITALOCEAN_TOKEN before running terraform, rather than hardcoding it here
# or in a committed .tfvars file.
provider "digitalocean" {}

resource "digitalocean_container_registry" "backend" {
  name                   = var.registry_name
  subscription_tier_slug = "starter" # free tier: 500MB storage, enough for this single image
}

resource "digitalocean_ssh_key" "deploy" {
  name       = "${var.droplet_name}-deploy-key"
  public_key = var.ssh_public_key
}

resource "digitalocean_droplet" "backend" {
  name     = var.droplet_name
  region   = var.region
  size     = var.droplet_size
  image    = "ubuntu-22-04-x64"
  ssh_keys = [digitalocean_ssh_key.deploy.fingerprint]

  # Installs Docker + Compose and logs the droplet in to the private container registry so
  # `docker compose up` (run manually on first deploy, see infra/README.md) can pull the image.
  # Deliberately doesn't start the app itself here — the app needs DATABASE_URL/SECRET_KEY
  # secrets that shouldn't be baked into Terraform state via user_data.
  user_data = <<-EOF
    #!/bin/bash
    set -e
    apt-get update
    apt-get install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  EOF
}

resource "digitalocean_firewall" "backend" {
  name        = "${var.droplet_name}-fw"
  droplet_ids = [digitalocean_droplet.backend.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    # Everything now goes through the Caddy proxy, routed by hostname (api.kumokosmos.com /
    # kumokosmos.com) — app and frontend containers no longer publish their ports directly,
    # so 8080/8081 don't need to be open here anymore. 80 is needed even with HTTPS: Caddy
    # uses it for the Let's Encrypt ACME challenge and to redirect plain HTTP to HTTPS.
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  # No rule for 5432: Postgres is only reachable inside the docker-compose network, never
  # exposed to the droplet's public interface.

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
