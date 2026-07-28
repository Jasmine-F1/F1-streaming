output "kubeconfig_path" {
  description = "Path to the kubeconfig file kind wrote for this cluster"
  value       = kind_cluster.this.kubeconfig_path
}

output "cluster_endpoint" {
  value = kind_cluster.this.endpoint
}
