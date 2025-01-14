import json
import boto3
import os
import datetime

DYNAMO_DB_TABLE_NAME = os.getenv("DYNAMO_DB_TABLE_NAME")

dynamodb_client = boto3.client("dynamodb")

def generate_datetimestamp():
    current_datetime = datetime.now()
    return current_datetime.strftime("%Y-%m-%d %H:%M:%S")

def calculate_fuel_economy(odometer_start, odometer_end, fuel_litres):
    fuel_economy = (odometer_end - odometer_start) / fuel_litres
    return round(fuel_economy, 2)


def write_data_to_dynamodb(user_name, data_record):
    current_timestamp = generate_datetimestamp()
    user_id = user_name + current_timestamp
    fuel_economy = calculate_fuel_economy(float(data_record["odometer_start"]), float(data_record["odometer_end"]), float(data_record["fuel_litres"]))
    response = dynamodb_client.put_item(
        Item={
            'user_id': {
                'S': user_id,
            },
            'user_name': {
                'S': user_name,
            },
            'vehicle_type': {
                'S': data_record["data_record"],
            },
            'refuel_date': {
                'S': data_record["refuel_date"],
            },
            'refuel_quantity_litres': {
                'N': data_record["refuel_quantity_litres"],
            },
            'odometer_reading_start': {
                'N': data_record["odometer_reading_start"],
            },
            'odometer_reading_end': {
                'N': data_record["odometer_reading_end"],
            },
            'fuel_economy': {
                'N': fuel_economy,
            },
        },
        ReturnConsumedCapacity='TOTAL',
        TableName=DYNAMO_DB_TABLE_NAME,
    )
    return response


def get_data_from_dynamodb(user_name, page_size):
    query_params = {
        'TableName': DYNAMO_DB_TABLE_NAME,
        'KeyConditionExpression': 'user_name = :pk',
        'ExpressionAttributeValues': {
            ':pk': {'S': user_name}  # 'S' indicates a string data type
        },
        'Limit' : page_size
    }

    # Initialize variables
    last_evaluated_key = None
    all_items = []

    # Loop to handle pagination
    while True:
        # Add ExclusiveStartKey if this is not the first request
        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key

        # Perform the query
        response = dynamodb_client.query(**query_params)

        # Append items to the list (convert them from DynamoDB format)
        all_items.extend(response['Items'])

        # Check if there are more pages of results
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break  # Exit loop if no more pages
    return all_items


def lambda_handler(event, context):
    try:
        username = event['requestContext']['authorizer']['claims']['cognito:username']
        resource_path = event['requestContext']['resourcePath']
        http_method = event['httpMethod']
        print(f"Logged-In UserName: {username}")
        print(f"API Endpoint Path: {resource_path}")
        print(f"HTTP Method: {http_method}")
        if http_method == "GET":
            data = get_data_from_dynamodb(username, 50)
            return {
            "statusCode": 200,
            "body": json.dumps(data)
        }
        elif http_method == "PUT":
            record = event['requestContext']['body']
            response_body = write_data_to_dynamodb(username, record)
            return {
            "statusCode": 201,
            "body": response_body
        }
    except KeyError as e:
        return {
            "statusCode": 400,
            "body": "Unable to retrieve username."
        }
    except Exception as ex:
        return {
            "statusCode": 500,
            "body": ex.__str__()
        }