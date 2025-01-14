#DynamoDB
resource "aws_dynamodb_table" "fec_datastore" {
    name = "${var.environment}-fec-datastore"
    billing_mode = "PROVISIONED"
    read_capacity  = 1
    write_capacity = 1
    hash_key = "user_id"
    range_key = "refuel_date"

    attribute {
      name = "user_id"
      type = "S"
    }

    attribute {
      name = "user_name"
      type = "S"
    }

    attribute {
      name = "refuel_date"
      type = "S"
    }

    local_secondary_index {
      name = "UserNameIndex"
      projection_type = "ALL"
      range_key = "refuel_date"
    }

    local_secondary_index {
      name = "RefuelDateIndex"
      projection_type = "ALL"
      range_key = "user_name"
    }

    tags = merge({
        Name = "Fuel Economy Calculator Datastore"
    }, local.common_tags)
}

#CognitoUserPool
resource "aws_cognito_user_pool" "fec_userpool" {
  name = "${var.environment}-fec-user-pool"
  password_policy {
    minimum_length = 8
    password_history_size = 3
    require_lowercase = true
    require_numbers = true
    require_symbols = true
    require_uppercase = true
  }
}