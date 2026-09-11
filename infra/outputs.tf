output "droplet_ip" {
  value = digitalocean_droplet.backend.ipv4_address
}

output "registry_endpoint" {
  value = digitalocean_container_registry.backend.server_url
}
