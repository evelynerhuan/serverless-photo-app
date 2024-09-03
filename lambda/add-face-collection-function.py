import boto3
import json
import urllib
import logging

# Initialize clients
dynamodb = boto3.client('dynamodb')
s3 = boto3.client('s3')
rekognition = boto3.client('rekognition')

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def index_faces(bucket, key, collection_id):
    """
    Index faces in the specified S3 object using Rekognition.
    
    Args:
        bucket (str): The name of the S3 bucket.
        key (str): The object key (file name) in the S3 bucket.
        collection_id (str): The Rekognition collection ID.

    Returns:
        dict: The response from Rekognition containing face indexing results.
    """
    response = rekognition.index_faces(
        Image={"S3Object": {"Bucket": bucket, "Name": key}},
        CollectionId=collection_id
    )
    return response

def lambda_handler(event, context):
    """
    AWS Lambda handler that processes S3 events, indexes faces using Rekognition, 
    and stores the face data in DynamoDB.
    
    Args:
        event (dict): The event data from S3.
        context (LambdaContext): The runtime information of the Lambda function.

    Returns:
        dict: The response from the Rekognition service.
    """
    # Get bucket and key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

    # Collection and Table names (could be environment variables)
    collection_id = "face_collection"
    table_name = "face"

    try:
        logger.info(f"Processing object {key} from bucket {bucket}")

        # Index face in Rekognition
        response = index_faces(bucket, key, collection_id)
        
        # Verify successful indexing
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            face_id = response['FaceRecords'][0]['Face']['FaceId']
            
            # Get metadata from S3 object
            s3_response = s3.head_object(Bucket=bucket, Key=key)
            face_name = s3_response['Metadata']['face_name']
            user_name = s3_response['Metadata']['user_name']
            
            # Update DynamoDB
            db_response = dynamodb.put_item(
                TableName=table_name,
                Item={
                    'index': {'S': face_id},
                    'face_name': {'S': face_name},
                    'username': {'S': user_name},
                }
            )
            logger.info(f"Successfully indexed face: {face_name} for user: {user_name}")
        else:
            logger.error(f"Failed to index face for object {key} in bucket {bucket}")

        return response
        
    except Exception as e:
        logger.error(f"Error processing object {key} from bucket {bucket}: {e}")
        raise e