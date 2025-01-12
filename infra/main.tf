#DynamoDB
resource "aws_dynamodb_table" "fec-datastore" {
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
      name = "vehicle_type"
      type = "S"
    }

    attribute {
      name = "refuel_date"
      type = "S"
    }

    attribute {
      name = "refuel_quantity_litres"
      type = "N"
    }

    attribute {
      name = "odometer_reading_start"
      type = "N"
    }

    attribute {
      name = "odometer_reading_end"
      type = "N"
    }

    attribute {
      name = "fuel_economy"
      type = "N"
    }

    tags = merge({
        Name = "Fuel Economy Calculator Datastore"
    }, local.common_tags)
}

#CognitoUserPool
