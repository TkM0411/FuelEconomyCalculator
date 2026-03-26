terraform {
    backend "s3" {
        bucket = "tkm-tfstate"
        key = "FuelEconomyCalculator/infra/terraform.tfstate"
        region = "us-east-1"
        encrypt = true
    }
}

provider "aws" {
    region = var.aws_region
}