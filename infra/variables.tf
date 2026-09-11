variable "droplet_name" {
  description = "Name for the droplet running the backend."
  type        = string
  default     = "kumo-kosmos-backend"
}

variable "registry_name" {
  description = "DigitalOcean container registry name, must be unique within your account."
  type        = string
  default     = "kumo-kosmos"
}

variable "region" {
  description = "DigitalOcean region slug (nyc1, sfo3, etc, run `doctl compute region list`)."
  type        = string
  default     = "nyc1"
}

variable "droplet_size" {
  description = "Droplet size slug. s-1vcpu-1gb is the cheapest that comfortably runs the app + Postgres together."
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "ssh_public_key" {
  description = "Your SSH public key contents (e.g. `cat ~/.ssh/id_ed25519.pub`), used to access the droplet."
  type        = string
}
