from flask import Flask, render_template, request, redirect, url_for, session
from app import webapp, mail
import boto3
from flask_mail import Message
import re
from botocore.exceptions import ClientError
from os import environ
from app.utils import (
    check_username, generate_salt, hash_password, check_password, update_password, check_email, 
    get_reset_token, verify_reset_token, get_username_token
)

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

@webapp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register a new user by storing their credentials in DynamoDB.
    """
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form['username']
        email = request.form['email']
        salt = generate_salt()
        password = hash_password(salt, request.form['password'])
        table = dynamodb.Table('User_info')
        
        # Validate input
        if check_username(username, table):
            msg = 'User already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Store user credentials in DynamoDB
            table.put_item(
                Item={
                    'username': username,
                    'password': password,
                    'email': email,
                    'salt': salt,
                }
            )
            msg = 'You have successfully registered!'
            return render_template('login.html', msg=msg)
            
    return render_template('register.html', msg=msg)

@webapp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Authenticate user and create a session.
    """
    if "loggedin" in session:
        return redirect(url_for('dashboard'))
    
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        table = dynamodb.Table('User_info')
        
        if not check_username(username, table):
            msg = 'Incorrect username! Please check your login information and try again.'
        elif not check_password(username, password, table):
            msg = 'Incorrect password!'
        else:
            session['loggedin'] = True
            session['username'] = username
            msg = 'Logged in successfully!'
            return redirect(url_for('dashboard'))

    return render_template('login.html', msg=msg)

@webapp.route('/logout')
def logout():
    """
    Log the user out by clearing the session data.
    """
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@webapp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    """
    Display the user's dashboard.
    """
    if "loggedin" not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html')

@webapp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    """
    Allow logged-in users to change their password.
    """
    msg = ''
    if "loggedin" not in session:
        return redirect(url_for('login'))

    if request.method == 'POST' and 'old_password' in request.form and 'password' in request.form:
        old_password = request.form['old_password']
        new_password = request.form['password']
        username = session['username']
        table = dynamodb.Table('User_info')
        
        if not check_password(username, old_password, table):
            msg = 'Your password is incorrect, please try again.'
        else:
            salt = generate_salt()
            hashed_password = hash_password(salt, new_password)
            update_password(username, hashed_password, salt, table)
            msg = 'You have successfully changed your password!'
            
    return render_template("change_password.html", msg=msg)

@webapp.route('/password_recovery', methods=['GET', 'POST'])
def password_recovery():
    """
    Send a password recovery email with a token to reset the user's password.
    """
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'email' in request.form:
        username = request.form['username']
        email = request.form['email']
        table = dynamodb.Table('User_info')

        if not check_username(username, table):
            msg = 'This username does not exist! Please check your information and try again.'
        elif not check_email(username, email, table):
            msg = 'This email address does not match the username! Please check your information and try again.'
        else:
            token = get_reset_token(username)
            subject = 'Password reset requested'
            message = Message(subject, sender=environ.get('MAIL_USERNAME'), recipients=[email])
            message.body = f'''To reset your password, visit the following link: {url_for('reset_password', token=token, _external=True)}
            If you did not make this request then simply ignore this email and no changes will be made.
            '''
            mail.send(message)
            msg = 'An email for password recovery has been sent. Please check your inbox.'
            
    return render_template("password_recovery.html", msg=msg)

@webapp.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_password(token):
    """
    Allow users to reset their password using a token sent via email.
    """
    msg = ''
    table = dynamodb.Table('User_info')

    if not verify_reset_token(token, table):
        msg = 'Warning: The token is either invalid or expired. Please generate a new link.'
        return render_template("password_recovery.html", msg=msg)

    if request.method == 'POST' and 'password' in request.form and 'confirm_password' in request.form:
        if request.form['confirm_password'] == request.form['password']:
            salt = generate_salt()
            password = hash_password(salt, request.form['password'])
            username = get_username_token(token)
            update_password(username, password, salt, table)
            msg = 'Your password has been successfully reset!'
        else:
            msg = 'Passwords do not match, please try again.'

    return render_template("reset_password.html", msg=msg, token=token)

@webapp.route('/create_table')
def create_table():
    """
    Create DynamoDB tables. (Example provided for the 'face' table.)
    """
    table = dynamodb.create_table(
        TableName='face',
        KeySchema=[
            {'AttributeName': 'index', 'KeyType': 'HASH'},  # Partition key
            {'AttributeName': 'username', 'KeyType': 'RANGE'}  # Sort key
        ],
        AttributeDefinitions=[
            {'AttributeName': 'index', 'AttributeType': 'S'},
            {'AttributeName': 'username', 'AttributeType': 'S'}
        ],
        ProvisionedThroughput={'ReadCapacityUnits': 10, 'WriteCapacityUnits': 10}
    )
    return redirect(url_for('main'))

@webapp.route('/delete_table')
def delete_table():
    """
    Delete a specific DynamoDB table.
    """
    dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')
    dynamodb_client.delete_table(TableName='User_info')
    return redirect(url_for('main'))

@webapp.route('/form<msg>', methods=['GET'])
def user_image_form(msg):
    """
    Display the form for image upload with a message.
    """
    if "loggedin" not in session:
        return redirect(url_for('login'))
    
    return render_template("form.html", msg=msg)

@webapp.route('/create_collection')
def create_collection():
    """
    Create a Rekognition collection for storing face data.
    """
    collection_id = "face_collection"
    client = boto3.client('rekognition')
    response = client.create_collection(CollectionId=collection_id)
    print('Collection ARN:', response['CollectionArn'])
    print('Status code:', response['StatusCode'])
    print('Done...')
    return redirect(url_for('main'))

@webapp.route('/delete_collection')
def delete_collection():
    """
    Delete a Rekognition collection by its ID.
    """
    collection_id = "face_collection"
    print(f'Attempting to delete collection: {collection_id}')
    
    client = boto3.client('rekognition')
    status_code = 0
    
    try:
        response = client.delete_collection(CollectionId=collection_id)
        status_code = response['StatusCode']
        print(f'Successfully deleted collection: {collection_id}')
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceNotFoundException':
            print(f'The collection {collection_id} was not found.')
        else:
            print(f'Error occurred: {e.response["Error"]["Message"]}')
        status_code = e.response['ResponseMetadata']['HTTPStatusCode']
    
    print(f'Status code: {status_code}')
    return redirect(url_for('main'))
