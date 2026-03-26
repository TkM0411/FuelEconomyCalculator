variable "aws_region" {
    type = string
    description = "AWS Region"
    default = "ap-south-2"
}

variable "environment" {
    type = string
    description = "Environment"
    default = "dev"
}

variable "static_tags" {
    type = map(string)
    description = "Common Tags for all resources"
    default = {
        "Created By" = "Terraform"
        "Project" = "Fuel Economy Calculator Infrastructure"
        "Owner" = "TkM"
    }
}