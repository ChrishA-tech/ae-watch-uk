# Networking Module Variables
# Author: CHRISH PEP FELIX A

variable "project_name" {
  type        = string
  description = "Project name"
}

variable "environment" {
  type        = string
  description = "Environment name"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC CIDR block"
}

variable "availability_zones" {
  type        = list(string)
  default     = ["eu-west-2a", "eu-west-2b"]
  description = "Availability zones in London region"
}
