# Root Outputs for AE-Watch UK Infrastructure
# Author: CHRISH PEP FELIX A

output "vpc_id" {
  value       = module.networking.vpc_id
  description = "Provisioned VPC ID"
}

output "postgres_endpoint" {
  value       = module.database.endpoint
  description = "PostgreSQL RDS connection endpoint"
}

output "alb_dns_name" {
  value       = module.compute.alb_dns_name
  description = "Application Load Balancer DNS name"
}

output "api_gateway_url" {
  value       = "http://${module.compute.alb_dns_name}"
  description = "Public URL for FastAPI Clinical-Ops Gateway"
}

output "dashboard_url" {
  value       = "http://${module.compute.alb_dns_name}:8501"
  description = "Public URL for Streamlit Clinical Command Centre"
}

output "secrets_manager_arn" {
  value       = module.security.secrets_arn
  description = "ARN of Secrets Manager holding API credentials"
}
