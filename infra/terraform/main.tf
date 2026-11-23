# Terraform Root Configuration for AE-Watch UK Production Deployment
# Author: CHRISH PEP FELIX A
# Project: AE-Watch UK

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Author      = var.author
      Repository  = "https://github.com/chrishpepfelix/ae-watch-uk"
    }
  }
}

# 1. Random password for PostgreSQL RDS
resource "random_password" "db_password" {
  length  = 24
  special = false
}

# 2. Networking Module
module "networking" {
  source       = "./modules/networking"
  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
}

# 3. Security Module
module "security" {
  source       = "./modules/security"
  project_name = var.project_name
  environment  = var.environment
}

# 4. Database Module
module "database" {
  source       = "./modules/database"
  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.networking.vpc_id
  subnet_ids   = module.networking.private_subnet_ids
  db_name      = var.db_name
  db_username  = var.db_username
  db_password  = random_password.db_password.result
}

# 5. Compute Module
module "compute" {
  source                 = "./modules/compute"
  project_name           = var.project_name
  environment            = var.environment
  vpc_id                 = module.networking.vpc_id
  public_subnet_ids      = module.networking.public_subnet_ids
  private_subnet_ids     = module.networking.private_subnet_ids
  ecs_execution_role_arn = module.security.ecs_execution_role_arn
  fastapi_port           = var.fastapi_port
  dashboard_port         = var.dashboard_port
}
