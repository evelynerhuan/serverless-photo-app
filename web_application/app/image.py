from flask import render_template, redirect, url_for, request, session, send_file
from app import webapp
from app.utils import check_imagename
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import date
import io
import PIL.Image
import time
import os
import urllib.request
from http import HTTPStatus
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the S3 bucket name from the environment variable
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'default-bucket-name')

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

@webapp.route('/form', methods=['GET', 'POST'])
def image_transform():
    """Handle image upload, processing, and storage in S3 and DynamoDB."""
    table = dynamodb.Table('Image')
    photos = request.files.getlist("image_file")

    if not photos or not any(f for f in photos):
        return redirect(url_for('user_image_form', msg="Missing uploaded file"))

    if any(f.filename == '' for f in photos):
        return redirect(url_for('user_image_form', msg='Missing file name'))

    for f in photos:
        if check_imagename(session['username'] + f.filename, table, "image"):
            return redirect(url_for('user_image_form', msg='Same file name already saved in your storage'))

    for i in photos:
        s3 = boto3.client('s3')
        file_path = f"{session['username']}/{i.filename}"
        
        # Convert image to byte streams
        stream = io.BytesIO(i.read())
        image = PIL.Image.open(stream)
        io_s = io.BytesIO()
        io_s1 = io.BytesIO()
        image.save(io_s, format=i.content_type.split("/")[1])
        image.save(io_s1, format=i.content_type.split("/")[1])
        io_s.seek(0)
        io_s1.seek(0)
        
        # Upload original image to S3
        s3.upload_fileobj(io_s, S3_BUCKET_NAME, file_path, ExtraArgs={"ContentType": "image/jpeg"})

        # Upload image to another bucket with metadata
        s3.upload_fileobj(io_s1, 'a3-filter-bucket', i.filename,
                          ExtraArgs={"Metadata": {"filename": i.filename, "username": session["username"]}})
        
        # Retrieve file size from S3
        contents = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, MaxKeys=1, Prefix=file_path)['Contents']
        original_size = contents[0]['Size']
        
        # Store image details in DynamoDB
        table.put_item(
            Item={
                'user_image_name': session['username'] + i.filename,
                'imagename': i.filename,
                'size': original_size,
                'kind': i.content_type.split("/")[0],
                'format': i.content_type.split("/")[1],
                'date_added': date.today().strftime("%Y-%m-%d"),
                'file_direction': file_path,
                'user': session['username'],
            }
        )

    return redirect(url_for('user_image_form', msg='Image uploaded successfully'))

@webapp.route('/form/url', methods=['GET', 'POST'])
def url_image():
    """Handle image upload from URL and store in S3 and DynamoDB."""
    url = request.form['url']
    if url == '':
        return redirect(url_for('user_image_form', msg='Missing URL'))

    try:
        table = dynamodb.Table('Image')
        response = urllib.request.urlopen(url)
        img_name = url.split('/')[-1]
        allowed_extensions = {'png', 'jpg', 'jpeg'}
        file_extension = img_name.split('.')[-1].lower()
        if not any(ext in file_extension for ext in allowed_extensions):
            return redirect(url_for('user_image_form', msg="Failed to retrieve image from URL"))

        if check_imagename(session['username'] + img_name, table, "image"):
            return redirect(url_for('user_image_form', msg='Same file name already saved in your storage'))

        if response.getcode() == 200:
            s3 = boto3.client('s3')
            file_path = f"{session['username']}/{img_name}"
            s3.upload_fileobj(response, S3_BUCKET_NAME, file_path, ExtraArgs={"ContentType": "image/jpeg"})
            
            # Retrieve file size from S3
            contents = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, MaxKeys=1, Prefix=file_path)['Contents']
            original_size = contents[0]['Size']
            
            # Store image details in DynamoDB
            table.put_item(
                Item={
                    'user_image_name': session['username'] + img_name,
                    'imagename': img_name,
                    'size': original_size,
                    'kind': "image",
                    'format': file_extension,
                    'date_added': date.today().strftime("%Y-%m-%d"),
                    'file_direction': file_path,
                    'user': session['username'],
                }
            )
            return redirect(url_for('user_image_form', msg='Image uploaded successfully from URL'))
    
    except Exception as e:
        print(e)
        return redirect(url_for('user_image_form', msg=str(e)))



@webapp.route('/view_filter/<filename>', methods=['GET'])
def show_filter(filename):
    """Generate and display filtered images."""
    filter_names = ['counter', 'detail', 'smooth']
    url_list = []
    s3 = boto3.client('s3')

    for filter_name in filter_names:
        file_path = f"{session['username']}/filter_image/{filename}/{filename}_{filter_name}.jpeg"
        url = s3.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': file_path})
        url_list.append((url, filter_name))
    
    return render_template("view_transform.html", filelist=url_list)


@webapp.route('/view/<filename>', methods=['GET'])
def view_transform_image(filename):
    """View the transformed image stored in S3."""
    if "loggedin" not in session:
        return redirect(url_for('login'))

    s3 = boto3.client('s3')
    file_path = f"{session['username']}/{filename}"
    url = s3.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': file_path})
    
    return render_template("view.html", url=url)


@webapp.route('/date', methods=['GET', 'POST'])
def image_date():
    """Search and list images by date range."""
    if not request.form['startdate'] or not request.form['enddate']:
        return render_template("search.html", msg="Error! All inputs should be typed")
    
    startdate = request.form['startdate']
    enddate = request.form['enddate']

    formatted_start_date = time.strptime(startdate, "%Y-%m-%d")
    formatted_end_date = time.strptime(enddate, "%Y-%m-%d")

    if formatted_start_date > formatted_end_date:
        return render_template("search.html", msg="Start date should be earlier than end date!")

    table = dynamodb.Table('Image')
    response = table.query(KeyConditionExpression=Key('kind').eq("image"))

    records = [
        i for i in response['Items']
        if formatted_start_date <= time.strptime(i['date_added'], "%Y-%m-%d") <= formatted_end_date
        and i['user'] == session['username']
    ]

    return render_template("list.html", records=records)


@webapp.route('/list_all', methods=['GET', 'POST'])
def image_list_all():
    """List all images sorted by date or size."""
    table = dynamodb.Table('Image')
    sort_option = request.form.get('sort-select')

    response = table.query(KeyConditionExpression=Key('kind').eq("image"))

    records = [i for i in response['Items'] if i['user'] == session['username']]
    
    if sort_option == "date":
        records.sort(key=lambda x: x["date_added"])
    elif sort_option == "size":
        records.sort(key=lambda x: int(x["size"]))

    return render_template("list.html", records=records)


@webapp.route('/delete/<filename>', methods=['GET'])
def delete_image(filename):
    """Delete a specific image from S3 and DynamoDB."""
    table = dynamodb.Table('Image')
    response = table.get_item(Key={'kind': "image", 'user_image_name': filename})

    try:
        file_direction = response["Item"]['file_direction']
        file_name = response["Item"]['imagename']

        # Delete image from DynamoDB
        table.delete_item(Key={'kind': "image", 'user_image_name': filename})

        # Delete image and related files from S3
        s3 = boto3.client('s3')
        s3.delete_object(Bucket=S3_BUCKET_NAME, Key=file_direction)
        
        s3_resource = boto3.resource('s3')
        bucket = s3_resource.Bucket(S3_BUCKET_NAME)
        bucket.objects.filter(Prefix=f"{session['username']}/image_crop/{file_name}/").delete()
        bucket.objects.filter(Prefix=f"{session['username']}/filter_image/{file_name}/").delete()

    except Exception as e:
        print(e)
    
    # Return updated list of images
    response = table.query(KeyConditionExpression=Key('kind').eq("image"))
    records = [i for i in response['Items'] if i['user'] == session['username']]

    return render_template("list.html", records=records, msg="Delete image successfully!")


@webapp.route('/delete_all/<username>', methods=['GET'])
def delete_image_all(username):
    """Delete all images for a specific user."""
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_BUCKET_NAME)
    bucket.objects.filter(Prefix=f"{username}/").delete()

    table = dynamodb.Table('Image')
    response = table.query(KeyConditionExpression=Key('kind').eq("image"))

    for item in response['Items']:
        if item['user'] == session['username']:
            table.delete_item(Key={'kind': item['kind'], 'user_image_name': item['user_image_name']})

    return render_template("list.html", records=[], msg="Delete all images successfully!")


@webapp.route('/list_all_setting<msg>', methods=['GET', 'POST'])
def list_all_main(msg):
    """Display search page with message."""
    if "loggedin" not in session:
        return redirect(url_for('login'))
        
    return render_template("search.html", msg=msg)


@webapp.route('/face_crop<msg>', methods=['GET'])
def face_crop_page(msg):
    """Display face crop page."""
    if "loggedin" not in session:
        return redirect(url_for('login'))
    
    return render_template("crop.html", msg=msg)


@webapp.route('/crop', methods=['GET', 'POST'])
def crop_face():
    """Handle face cropping and store results in S3."""
    msg = ''
    if request.method == 'GET':
        return render_template("crop.html", msg=msg)
    
    if not request.files['recognition_file']:
        msg = "Missing uploaded file"
        return render_template("crop.html", msg=msg)

    recognition_file = request.files['recognition_file']
    if recognition_file.filename == '':
        msg = "Missing file name"
        return render_template("crop.html", msg=msg)
    
    table = dynamodb.Table('Image')
    if check_imagename(session['username'] + recognition_file.filename, table, "image"):
        return render_template('crop.html', msg='Same file name already saved in your storage')

    file_path = f"{session['username']}/{recognition_file.filename}"
    s3 = boto3.client('s3')
    
    # Convert image to byte streams
    stream = io.BytesIO(recognition_file.read())
    image = PIL.Image.open(stream)
    io_s = io.BytesIO()
    io_s1 = io.BytesIO()
    image.save(io_s, format=recognition_file.content_type.split("/")[1])
    image.save(io_s1, format=recognition_file.content_type.split("/")[1])
    io_s.seek(0)
    io_s1.seek(0)
    
    # Upload original image to S3
    s3.upload_fileobj(io_s, S3_BUCKET_NAME, file_path, ExtraArgs={"ContentType": "image/jpeg"})

    # Upload image to another bucket with metadata
    s3.upload_fileobj(io_s1, 'a3-filter-bucket', recognition_file.filename,
                      ExtraArgs={"Metadata": {"filename": recognition_file.filename, "username": session["username"]}})

    # Retrieve file size from S3
    contents = s3.list_objects_v2(Bucket=S3_BUCKET_NAME, MaxKeys=1, Prefix=file_path)['Contents']
    original_size = contents[0]['Size']

    # Store image details in DynamoDB
    table.put_item(
        Item={
            'user_image_name': session['username'] + recognition_file.filename,
            'imagename': recognition_file.filename,
            'size': original_size,
            'kind': recognition_file.content_type.split("/")[0],
            'format': recognition_file.content_type.split("/")[1],
            'date_added': date.today().strftime("%Y-%m-%d"),
            'file_direction': file_path,
            'user': session['username'],
        }
    )
    
    # Detect and crop faces from the image
    save_place_list = show_faces_crop(file_path, S3_BUCKET_NAME)
    return render_template("crop.html", msg=f"Faces Detected: {len(save_place_list)}", newlist=save_place_list)


def show_faces_crop(photo, bucket):
    """Detect and crop faces from an image stored in S3."""
    client = boto3.client('rekognition')
    
    # Load image from S3 bucket
    s3_connection = boto3.resource('s3')
    s3_object = s3_connection.Object(bucket, photo)
    s3_response = s3_object.get()
    
    stream = io.BytesIO(s3_response['Body'].read())
    image = PIL.Image.open(stream)
	

    # Get image dimensions
    img_width, img_height = image.size

    # Call AWS Rekognition to detect faces
    response = client.detect_faces(Image={'S3Object': {'Bucket': bucket, 'Name': photo}}, Attributes=['ALL'])

    save_place_list = []
    count = 1

    # Process each detected face
    for face_detail in response['FaceDetails']:
        # Calculate bounding box coordinates
        box = face_detail['BoundingBox']
        left = int(box['Left'] * img_width * 0.9)
        top = int(box['Top'] * img_height * 0.9)
        width = int((box['Left'] * img_width + box['Width'] * img_width) * 1.10)
        height = int((box['Top'] * img_height + box['Height'] * img_height) * 1.10)

        # Crop the image
        cropped_image = image.crop((left, top, width, height))
        io_s = io.BytesIO()
        cropped_image.save(io_s, format="JPEG")
        io_s.seek(0)

        # Generate S3 file path for cropped face
        file_dir = f"{session['username']}/image_crop/{photo}/{photo}_{count}.jpeg"

        # Upload cropped face to S3
        s3 = boto3.client('s3')
        s3.upload_fileobj(io_s, S3_BUCKET_NAME, file_dir, ExtraArgs={"ContentType": "image/jpeg"})

        # Generate presigned URL for the cropped face
        url_file = s3.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': file_dir})
        save_place_list.append((url_file, f"{photo}_{count}"))

        count += 1

    return save_place_list


@webapp.route('/face_collection<msg>', methods=['GET'])
def face_collection(msg):
    """Display the face collection page."""
    if "loggedin" not in session:
        return redirect(url_for('login'))

    return render_template("face_collection.html", msg=msg)


@webapp.route('/upload_face', methods=['GET', 'POST'])
def upload_face():
    """Upload a new face image to the S3 bucket."""
    msg = ''
    if not request.files['face_image']:
        msg = "Missing uploaded file"
        return redirect(url_for('face_collection', msg=msg))

    image = request.files['face_image']
    if image.filename == '':
        msg = "Missing file name"
        return redirect(url_for('face_collection', msg=msg))

    face_name = request.form.get('name', '')
    if face_name == '':
        msg = "Missing face name"
        return redirect(url_for('face_collection', msg=msg))

    # Upload face image and its corresponding name to S3
    file_dir = f"{session['username']}_{image.filename}"
    stream = io.BytesIO(image.read())
    image = PIL.Image.open(stream)
    io_s = io.BytesIO()
    image.save(io_s, format="JPEG")
    io_s.seek(0)

    s3_client = boto3.client('s3')
    s3_client.upload_fileobj(io_s, 'a3-face-recognition-bucket', file_dir,
                             ExtraArgs={"Metadata": {"face_name": face_name, "user_name": session["username"]}})

    msg = "Upload successful"
    return redirect(url_for('face_collection', msg=msg))


@webapp.route('/face_recognition<msg>', methods=['GET'])
def face_recognition(msg):
    """Display the face recognition page."""
    if "loggedin" not in session:
        return redirect(url_for('login'))

    return render_template("face_recognition.html", msg=msg)


@webapp.route('/upload_face_recognition', methods=['GET', 'POST'])
def upload_face_recognition():
    """Handle face recognition by uploading an image."""
    msg = ''

    if not request.files['recognition_file']:
        msg = "Missing uploaded file"
        return redirect(url_for('face_recognition', msg=msg))

    recognition_file = request.files['recognition_file']
    if recognition_file.filename == '':
        msg = "Missing file name"
        return redirect(url_for('face_recognition', msg=msg))

    # Detect faces using AWS Rekognition
    rekognition = boto3.client('rekognition', region_name='us-east-1')
    stream = io.BytesIO(recognition_file.read())
    response = rekognition.detect_faces(Image={'Bytes': stream.read()})
    face_details = response['FaceDetails']

    image = PIL.Image.open(stream)
    img_width, img_height = image.size

    face_name_list, similarity_list = [], []

    # Crop each detected face and compare with known faces
    for face in face_details:
        box = face['BoundingBox']
        left = int(box['Left'] * img_width * 0.9)
        top = int(box['Top'] * img_height * 0.9)
        width = int((box['Left'] * img_width + box['Width'] * img_width) * 1.10)
        height = int((box['Top'] * img_height + box['Height'] * img_height) * 1.10)

        cropped_image = image.crop((left, top, width, height))
        stream = io.BytesIO()
        cropped_image.save(stream, format="JPEG")
        image_crop_binary = stream.getvalue()

        # Submit cropped image to Rekognition for comparison
        response = rekognition.search_faces_by_image(CollectionId='face_collection', Image={'Bytes': image_crop_binary})

        if response['FaceMatches']:
            for match in response['FaceMatches']:
                face_name, similarity = recognize_each_face(match)
                if face_name:
                    face_name_list.append(face_name)
                    similarity_list.append(similarity)

    if face_name_list:
        msg = '{} in the picture with {}% similarity'.format(
            ', '.join(face_name_list),
            ', '.join([str(round(similarity, 3)) for similarity in similarity_list])
        )
        return redirect(url_for('face_recognition', msg=msg))

    msg = 'No matched face found. Please try another picture.'
    return redirect(url_for('face_recognition', msg=msg))


def recognize_each_face(match):
    """Retrieve face name and similarity from DynamoDB based on the match."""
    face_table = dynamodb.Table('face')
    face_name, similarity = None, None

    face = face_table.get_item(Key={
        'index': match['Face']['FaceId'],
        'username': session['username']
    })

    if 'Item' in face:
        face_name = face['Item']['face_name']
        similarity = match['Similarity']

    return face_name, similarity


@webapp.route('/compare/<file>', methods=['GET'])
def compare_all_pics(file):
    """Compare a submitted picture with all pictures in the user's collection."""
    table = dynamodb.Table('Image')

    # Retrieve all user images from DynamoDB
    response = table.query(KeyConditionExpression=Key('kind').eq("image"))

    s3_connection = boto3.resource('s3')
    file_dir = f"{session['username']}/image_crop/{file[:-1]}/{file[:-1]}_{file[-1]}.jpeg"

    records = []
    for item in response['Items']:
        if item['user'] == session['username']:
            # Retrieve each user image from S3
            s3_object = s3_connection.Object(S3_BUCKET_NAME, item['file_direction'])
            s3_response = s3_object.get()
            stream = io.BytesIO(s3_response['Body'].read())

            # Get the submitted picture from S3
            submitted_pic_object = s3_connection.Object(S3_BUCKET_NAME, file_dir)
            submitted_pic_response = submitted_pic_object.get()
            submitted_pic_stream = io.BytesIO(submitted_pic_response['Body'].read())

            # Compare the submitted picture with each user image
            if compare_faces(submitted_pic_stream, stream):
                records.append(item)

    return render_template("list.html", records=records)


def compare_faces(source_file, target_file):
    """Compare two images using AWS Rekognition and return True if they match."""
    client = boto3.client('rekognition')

    response = client.compare_faces(SimilarityThreshold=80,
                                    SourceImage={'Bytes': source_file.read()},
                                    TargetImage={'Bytes': target_file.read()})

    return bool(response["FaceMatches"])
	
	