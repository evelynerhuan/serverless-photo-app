import json
import urllib.parse
import boto3
import io
from PIL import Image, ImageFilter
import logging
import os

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3 = boto3.client('s3')

def apply_filters(image):
    """
    Apply a set of filters to the image and return the results.
    
    Args:
        image (PIL.Image): The input image.

    Returns:
        dict: A dictionary with filter names as keys and filtered images as values.
    """
    filters = {
        'contour': image.filter(ImageFilter.CONTOUR),
        'detail': image.filter(ImageFilter.DETAIL),
        'smooth': image.filter(ImageFilter.SMOOTH),
    }
    return filters

def upload_filtered_images(filters, username, filename, bucket_name):
    """
    Upload filtered images to S3.
    
    Args:
        filters (dict): A dictionary containing filtered images.
        username (str): The username associated with the images.
        filename (str): The original filename.
        bucket_name (str): The name of the S3 bucket to upload to.
    """
    for filter_name, filtered_image in filters.items():
        io_s = io.BytesIO()
        filtered_image.save(io_s, format="JPEG")
        io_s.seek(0)
        file_path = f"{username}/filter_image/{filename}/{filename}_{filter_name}.jpeg"
        s3.upload_fileobj(io_s, bucket_name, file_path, ExtraArgs={"ContentType": "image/jpeg"})
        logger.info(f"Uploaded filtered image: {file_path}")

def lambda_handler(event, context):
    """
    AWS Lambda function to apply image filters and save the results back to S3.
    
    Args:
        event (dict): The event data from S3.
        context (LambdaContext): The runtime information of the Lambda function.
    """
    # Get bucket and key from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    # Output bucket name (could be set via environment variable)
    output_bucket = os.environ.get('OUTPUT_BUCKET', 'ece1779assignmentfall2021')
    source_bucket = os.environ.get('SOURCE_BUCKET', 'a3-filter-bucket')
    
    try:
        logger.info(f"Processing file {key} from bucket {bucket}")

        # Get metadata from S3 object
        s3_response = s3.head_object(Bucket=bucket, Key=key)
        username = s3_response['Metadata']['username']
        filename = s3_response['Metadata']['filename']
        
        # Download image from S3
        s3_connection = boto3.resource('s3')
        s3_object = s3_connection.Object(bucket, key)
        s3_response = s3_object.get()

        stream = io.BytesIO(s3_response['Body'].read())
        image = Image.open(stream)
        
        # Apply filters to the image
        filters = apply_filters(image)
        
        # Upload filtered images to S3
        upload_filtered_images(filters, username, filename, output_bucket)
        
        # Delete original image from the source bucket
        s3.delete_object(Bucket=source_bucket, Key=filename)
        logger.info(f"Deleted original file {filename} from bucket {source_bucket}")
        
    except Exception as e:
        logger.error(f"Error processing file {key} from bucket {bucket}: {e}")
        raise e