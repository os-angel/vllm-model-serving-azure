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

variable "zone" {
  description = "Zona aprobada para el clúster y ambos pools."
  type        = string
  default     = "us-central1-a"
}

variable "operator_cidr" {
  description = "IPv4 pública vigente del operador, como CIDR /32; pasar por TF_VAR_operator_cidr."
  type        = string

  validation {
    condition     = can(cidrnetmask(var.operator_cidr)) && endswith(var.operator_cidr, "/32")
    error_message = "operator_cidr debe ser una dirección IPv4 única en formato CIDR /32."
  }
}
