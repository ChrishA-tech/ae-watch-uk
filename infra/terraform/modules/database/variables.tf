# Database Module Variables
# Author: CHRISH PEP FELIX A

variable "project_name" {
  type        = string
  description = "Project name"
}

variable "environment" {
  type        = string
  description = "Environment name"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for DB subnet group"
}

variable "db_name" {
  type        = string
  description = "Database name"
}

variable "db_username" {
  type        = string
  description = "Master database username"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Master database password"
}
