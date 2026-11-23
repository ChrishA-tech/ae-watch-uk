# Security Module Variables
# Author: CHRISH PEP FELIX A

variable "project_name" {
  type        = string
  description = "Project name"
}

variable "environment" {
  type        = string
  description = "Environment name"
}

variable "gemini_api_key" {
  type        = string
  sensitive   = true
  default     = "dummy_api_key_placeholder"
  description = "Google Gemini API key for clinical agents and embeddings"
}
