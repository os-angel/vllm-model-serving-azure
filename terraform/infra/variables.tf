variable "project_id" {
  description = "Proyecto GCP aprobado para el laboratorio."
  type        = string
  default     = "llmresearch-510422"
}

variable "region" {
  description = "Región de la red y el futuro clúster zonal."
  type        = string
  default     = "us-central1"
}
