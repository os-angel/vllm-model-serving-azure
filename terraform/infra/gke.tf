resource "google_service_account" "gke_nodes" {
  account_id   = "nemotron-gke-nodes"
  display_name = "Nemotron GKE lab nodes"
}

resource "google_project_iam_member" "gke_node_role" {
  project = var.project_id
  role    = "roles/container.defaultNodeServiceAccount"
  member  = "serviceAccount:${google_service_account.gke_nodes.email}"
}

resource "google_container_cluster" "lab" {
  name                     = "nemotron-lab"
  location                 = var.zone
  network                  = google_compute_network.lab.id
  subnetwork               = google_compute_subnetwork.lab.id
  networking_mode          = "VPC_NATIVE"
  initial_node_count       = 1
  remove_default_node_pool = true
  deletion_protection      = false
  enable_shielded_nodes    = true
  min_master_version       = "1.35.6-gke.1250000"

  release_channel {
    channel = "STABLE"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = local.pod_range_name
    services_secondary_range_name = local.service_range_name
  }

  master_authorized_networks_config {
    gcp_public_cidrs_access_enabled = false

    cidr_blocks {
      cidr_block   = var.operator_cidr
      display_name = "operator"
    }
  }
}

resource "google_container_node_pool" "cpu" {
  name       = "cpu"
  location   = var.zone
  cluster    = google_container_cluster.lab.id
  node_count = 1
  version    = "1.35.6-gke.1250000"

  node_config {
    machine_type    = "e2-standard-4"
    image_type      = "COS_CONTAINERD"
    disk_type       = "pd-balanced"
    disk_size_gb    = 50
    service_account = google_service_account.gke_nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]

    labels = {
      workload = "cpu"
    }
  }

  depends_on = [google_project_iam_member.gke_node_role]
}

resource "google_container_node_pool" "gpu" {
  name       = "gpu"
  location   = var.zone
  cluster    = google_container_cluster.lab.id
  node_count = 1
  version    = "1.35.6-gke.1250000"

  node_config {
    machine_type    = "g2-standard-4"
    image_type      = "COS_CONTAINERD"
    disk_type       = "pd-balanced"
    disk_size_gb    = 50
    service_account = google_service_account.gke_nodes.email
    oauth_scopes    = ["https://www.googleapis.com/auth/cloud-platform"]

    labels = {
      workload = "gpu"
    }

    taint {
      key    = "dedicated"
      value  = "gpu"
      effect = "NO_SCHEDULE"
    }

    guest_accelerator {
      type  = "nvidia-l4"
      count = 1

      gpu_driver_installation_config {
        gpu_driver_version = "DEFAULT"
      }
    }
  }

  depends_on = [google_project_iam_member.gke_node_role]
}
