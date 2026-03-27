import json

def lambda_handler(event, context):
    # Log the incoming event for debugging
    print("Received event:", json.dumps(event))

    # Extract the HTTP method and path from the event
    http_method = event.get('httpMethod')
    path = event.get('path')

    # Handle different HTTP methods and paths
    if http_method == 'GET' and path == '/hello':
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Hello, World!'})
        }
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'message': 'Not Found'})
        }