output "network_name" {
  description = "Nombre de la VPC para el futuro clúster."
  value       = google_compute_network.lab.name
}

output "subnetwork_name" {
  description = "Nombre de la subred de us-central1."
  value       = google_compute_subnetwork.lab.name
}

output "pod_range_name" {
  description = "Nombre del rango secundario para Pods."
  value       = local.pod_range_name
}

output "service_range_name" {
  description = "Nombre del rango secundario para Services."
  value       = local.service_range_name
}

output "cluster_name" {
  description = "Nombre del clúster GKE zonal."
  value       = google_container_cluster.lab.name
}

output "cluster_location" {
  description = "Zona del clúster GKE."
  value       = google_container_cluster.lab.location
}
