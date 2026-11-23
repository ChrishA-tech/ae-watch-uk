# Input Variables for AE-Watch UK Infrastructure
# Author: CHRISH PEP FELIX A
# Project: AE-Watch UK

variable "project_name" {
  type        = string
  default     = "ae-watch-uk"
  description = "Project name prefix for all provisioned cloud resources"
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Deployment environment (development, staging, production)"
}

variable "aws_region" {
  type        = string
  default     = "eu-west-2"
  description = "AWS region for deployment (London, UK for NHS data residency compliance)"
}

variable "author" {
  type        = string
  default     = "CHRISH PEP FELIX A"
  description = "System author attribution tag"
}

variable "vpc_cidr" {
  type        = string
  default     = "10.0.0.0/16"
  description = "CIDR block for the production VPC"
}

variable "db_name" {
  type        = string
  default     = "aewatch"
  description = "Target PostgreSQL database name"
}

variable "db_username" {
  type        = string
  default     = "aewatch_admin"
  description = "Master username for PostgreSQL RDS"
}

variable "fastapi_port" {
  type        = number
  default     = 8000
  description = "Internal container port for FastAPI Clinical-Ops Gateway"
}

variable "dashboard_port" {
  type        = number
  default     = 8501
  description = "Internal container port for Streamlit Command Centre"
}
