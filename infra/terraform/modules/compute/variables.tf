# Compute Module Variables
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

variable "public_subnet_ids" {
  type        = list(string)
  description = "Public subnet IDs for ALB"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs for ECS tasks"
}

variable "ecs_execution_role_arn" {
  type        = string
  description = "ECS execution role ARN"
}

variable "fastapi_port" {
  type        = number
  default     = 8000
  description = "FastAPI port"
}

variable "dashboard_port" {
  type        = number
  default     = 8501
  description = "Streamlit dashboard port"
}
