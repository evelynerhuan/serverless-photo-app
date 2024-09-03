import hashlib
import bcrypt
import boto3
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from app import webapp

def check_username(username, table):
    """
    Check if the username exists in the given DynamoDB table.
    
    Args:
        username (str): The username to check.
        table (boto3.Table): The DynamoDB table instance.

    Returns:
        bool: True if the username exists, False otherwise.
    """
    response = table.get_item(Key={'username': username})
    return 'Item' in response

def generate_salt():
    """
    Generate a salt for password hashing.
    
    Returns:
        str: A generated salt.
    """
    return bcrypt.gensalt(12)  # Set rounds to 12 for security

def hash_password(salt, password):
    """
    Hash a password using SHA-256 with a given salt.
    
    Args:
        salt (str): The salt to use for hashing.
        password (str): The plain text password.

    Returns:
        str: The hashed password.
    """
    to_be_hashed = str(password) + str(salt)
    return hashlib.sha256(to_be_hashed.encode('utf-8')).hexdigest()

def check_password(username, password, table):
    """
    Check if the provided password matches the stored password for a given username.
    
    Args:
        username (str): The username to check.
        password (str): The plain text password to verify.
        table (boto3.Table): The DynamoDB table instance.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    response = table.get_item(Key={'username': username})
    if 'Item' not in response:
        return False
    
    stored_password = response['Item']['password']
    salt = response['Item']['salt']
    hashed_password = hash_password(salt, password)
    
    return stored_password == hashed_password

def update_password(username, password, salt, table):
    """
    Update the password and salt for a given username in DynamoDB.
    
    Args:
        username (str): The username whose password needs to be updated.
        password (str): The new hashed password.
        salt (str): The new salt.
        table (boto3.Table): The DynamoDB table instance.
    """
    response = table.get_item(Key={'username': username})
    if 'Item' not in response:
        raise ValueError("Username does not exist")
    
    item = response['Item']
    item['password'] = password
    item['salt'] = salt

    table.put_item(Item=item)

def check_email(username, email, table):
    """
    Verify if the provided email matches the email stored for the given username.
    
    Args:
        username (str): The username to check.
        email (str): The email to verify.
        table (boto3.Table): The DynamoDB table instance.

    Returns:
        bool: True if the email matches, False otherwise.
    """
    response = table.get_item(Key={'username': username})
    if 'Item' not in response:
        return False

    return response['Item']['email'] == email

def get_reset_token(username):
    """
    Generate a reset token for password recovery.
    
    Args:
        username (str): The username for which to generate the token.

    Returns:
        str: The generated token.
    """
    s = Serializer(webapp.config['SECRET_KEY'], 1800)  # Token expires in 1800 seconds (30 minutes)
    return s.dumps({'username': username}).decode('utf-8')

def verify_reset_token(token, table):
    """
    Verify the reset token and check if it corresponds to an existing username.
    
    Args:
        token (str): The reset token to verify.
        table (boto3.Table): The DynamoDB table instance.

    Returns:
        bool: True if the token is valid and the username exists, False otherwise.
    """
    s = Serializer(webapp.config['SECRET_KEY'])
    try:
        username = s.loads(token)['username']
    except Exception:
        return False
    return check_username(username, table)

def get_username_token(token):
    """
    Retrieve the username from the reset token.
    
    Args:
        token (str): The reset token.

    Returns:
        str: The username embedded in the token.
    """
    s = Serializer(webapp.config['SECRET_KEY'])
    return s.loads(token)['username']

def check_imagename(user_image_name, table, kind):
    """
    Check if the image name exists in the DynamoDB table for a given kind.
    
    Args:
        user_image_name (str): The full image name to check.
        table (boto3.Table): The DynamoDB table instance.
        kind (str): The kind of image (e.g., 'image', 'thumbnail').

    Returns:
        bool: True if the image name exists, False otherwise.
    """
    response = table.get_item(Key={'user_image_name': user_image_name, "kind": kind})
    return 'Item' in response