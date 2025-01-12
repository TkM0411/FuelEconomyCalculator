import json
import boto3
import os
import base64

DYNAMO_DB_TABLE_NAME = os.getenv("DYNAMO_DB_TABLE_NAME")

dynamodb_client = boto3.client("dynamodb")

def write_data_to_dynamodb(user_name, data_record):
    pass


def calculate_fuel_economy(odometer_start, odometer_end, fuel_litres):
    fuel_economy = (odometer_end - odometer_start) / fuel_litres
    return fuel_economy


def get_data_from_dynamodb(user_name, page_size, data_records):
    pass


def edit_record(user_name, record_id, modified_data):
    pass


def delete_record(user_name, record_id):
    pass


def lambda_handler(event, context):
    try:
        username = event['requestContext']['authorizer']['claims']['cognito:username']
        resource_path = event['requestContext']['resourcePath']
        http_method = event['httpMethod']
    except KeyError as e:
        return {
            "statusCode": 400,
            "body": "Unable to retrieve username."
        }