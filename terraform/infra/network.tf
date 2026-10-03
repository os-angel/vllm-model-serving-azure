locals {
  pod_range_name     = "nemotron-pods"
  service_range_name = "nemotron-services"
}

resource "google_compute_network" "lab" {
  name                    = "nemotron-lab-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "lab" {
  name          = "nemotron-lab-us-central1"
  region        = var.region
  network       = google_compute_network.lab.id
  ip_cidr_range = "10.80.0.0/20"

  secondary_ip_range {
    range_name    = local.pod_range_name
    ip_cidr_range = "10.81.0.0/20"
  }

  secondary_ip_range {
    range_name    = local.service_range_name
    ip_cidr_range = "10.82.0.0/22"
  }
}
