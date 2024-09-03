# Serverless Photo Organization Web Application

## Introduction

This project is a serverless photo organization web application designed to help users store, organize, and search their images efficiently. Leveraging advanced techniques like face recognition and image detection, the application simplifies the process of managing large photo collections, making it easier for users to find and organize their photos.

Note: This project was developed in September 2021 as part of a practical assignment to explore serverless architectures and advanced image processing techniques using AWS services.

## Features

![Flow Chart](/additional_resources/flow_chart.jpg)


- **User Registration and Authentication**: Secure account creation and login.
- **Image Upload**: Users can upload images to their account for storage and management.
- **Image Management**:
  - **Sort and Search**: Sort photos by date or size and search based on various criteria.
  - **Apply Filters**: Users can apply different visual effects to images, including contour, detail, and smooth filters.
  - **Face Detection**: Automatically detect and crop faces from uploaded images.
- **Face Collection Management**: Users can add faces to a collection with corresponding names, enabling easy recognition later.
- **Face Recognition**: Identify and recognize faces in uploaded photos, matching them against the user's face collection.

## Architecture

![Architecture Diagram](/additional_resources/architecture_diagram.jpg)

The application is built using a serverless architecture with the following AWS services:

- **DynamoDB**: Stores user information, image metadata, and face data.
- **S3 Buckets**: Stores images and manages photo collections.
- **AWS Rekognition**: Provides face recognition and image detection capabilities.
- **AWS Lambda**: Executes background processes triggered by events, such as image uploads.
- **API Gateway**: Serves as the entry point to the application, routing requests to the appropriate services.
- **Zappa**: Facilitates the deployment of the application to AWS Lambda.


## Project Structure

- **`lambda/`**: Contains AWS Lambda function code.
  - `add-face-collection-function.py`: Handles face collection, indexing faces in AWS Rekognition, and storing metadata in DynamoDB.
  - `filter-image-function.py`: Applies filters to images stored in S3 and processes them according to the user's requirements.

- **`web_application/`**: Contains the main Flask web application code.
  - `app/`: Source code for the Flask application.
    - `__init__.py`: Initializes the Flask app and its configurations.
    - `main.py`: Defines the main entry point of the web application, rendering the home page.
    -	`image.py`: Handles image-related routes, including uploading, filtering, and managing images.
    - `routes.py`: Defines the routes and views for the web application, handling user interactions.
    - `utils.py`: Utility functions for tasks like password hashing, token generation, and more.
  - `static/`: Static assets (CSS, JS, images).
  - `templates/`: HTML templates for rendering web pages.
  - `zappa_settings.json`: Configuration file for deploying the application using Zappa.
  - `requirements.txt`: List of Python dependencies required by the project.

- **`additional_resources/`**: Contains images and other resources used to explain the project.
  - `architecture_diagram.jpg`: Shows the architecture of the web application.
  - `flow_chart.jpg`: Displays the flow chart of the application's processes.
  - `nosql_database_overview.jpg`: (Replace with the actual file name and purpose).
  - 'user_manual.pdf`: explores the project

- **`README.md`**: This file. Provides an overview of the project, instructions for installation and deployment, and other relevant documentation.



## Installation and Deployment

### Environment Requirements

- Python 3.8
- AWS Account with access to S3, DynamoDB, and Rekognition

### Local Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/yourrepository.git
   ```
2. **Create a virtual environment and install dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Deployment to AWS

1. **Configure `zappa_settings.json`**:
   Ensure that the `zappa_settings.json` file is correctly configured with your AWS details and S3 bucket names.

2. **Deploy the application with Zappa**:
   ```bash
   zappa deploy dev
   ```
3. **Update the application**:
   If you make changes to the code, update the deployment with:
   ```bash
   zappa update dev
   ```

## Usage

- **Register and Login**: Access the website through the Zappa-generated link, create a new account, and log in to manage your photos.
- **Upload Images**: Upload images to your account and manage them through the web interface.
- **Apply Filters**: Select an image and apply various filters (contour, detail, smooth) to see different visual effects.
- **Face Detection**: Detect and crop faces from uploaded images. You can then view all photos containing a specific face by clicking on it.
- **Face Collection**: Add faces to your collection by uploading face images with corresponding names. This functionality allows for easier face recognition in future uploads.
- **Face Recognition**: Upload a photo, and the application will identify and display the names of recognized faces from your collection.

## Lambda Functions Details

### Face Collection Logic

- **Lambda Function**: `add-face-collection-function.py`
- **Process**:
  - When a user uploads a face image, it is stored in the `a3-face-recognition` S3 bucket.
  - A Lambda function is triggered, which calls `index_faces(bucket, key)` to index the face in AWS Rekognition.
  - The function retrieves the face ID from the response, along with the face name and username from the S3 bucket, and stores this information in the DynamoDB `face` table.

### Face Recognition Logic

- **Lambda Function**: `filter-image-function.py`
- **Process**:
  - After a photo is uploaded, the function detects all faces in the image.
  - For each detected face, it searches the face collection in AWS Rekognition.
  - The function then calls `recognize_each_face(response)` to match the face with the stored data in DynamoDB and renders the results on the frontend.


