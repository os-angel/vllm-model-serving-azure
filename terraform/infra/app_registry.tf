# Grupo 2: propuesta inactiva hasta revisar plan y costo con el propietario.
variable "enable_app_registry" {
  description = "Crear el registry privado dedicado al chat después de revisar plan y costo. Mantener true hasta destroy si ya fue creado."
  type        = bool
  default     = false
}

resource "google_project_service" "artifact_registry" {
  count              = var.enable_app_registry ? 1 : 0
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "app" {
  count                  = var.enable_app_registry ? 1 : 0
  project                = var.project_id
  location               = var.region
  repository_id          = "nemotron-lab-apps"
  description            = "Imagen del chat del laboratorio Nemotron; eliminar al cerrar."
  format                 = "DOCKER"
  cleanup_policy_dry_run = true

  docker_config {
    immutable_tags = true
  }

  vulnerability_scanning_config {
    enablement_config = "DISABLED"
  }

  labels = {
    purpose = "nemotron-lab"
  }

  depends_on = [google_project_service.artifact_registry]
}

resource "google_artifact_registry_repository_iam_member" "nodes_reader" {
  count      = var.enable_app_registry ? 1 : 0
  project    = var.project_id
  location   = google_artifact_registry_repository.app[0].location
  repository = google_artifact_registry_repository.app[0].repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.gke_nodes.email}"
}

output "app_image_repository" {
  description = "Repositorio de imagen del chat; null cuando registry está deshabilitado."
  value       = var.enable_app_registry ? "${var.region}-docker.pkg.dev/${var.project_id}/nemotron-lab-apps/chat" : null
}
