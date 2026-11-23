# Database Module Outputs
# Author: CHRISH PEP FELIX A

output "endpoint" {
  value       = aws_db_instance.postgres.endpoint
  description = "PostgreSQL connection endpoint"
}

output "address" {
  value       = aws_db_instance.postgres.address
  description = "PostgreSQL host address"
}

output "port" {
  value       = aws_db_instance.postgres.port
  description = "PostgreSQL port"
}
