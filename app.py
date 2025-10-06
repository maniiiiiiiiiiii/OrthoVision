#!/usr/bin/env python
from flask import Flask, render_template, request,jsonify
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import numpy as np
import json
from db import get_db_connection
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Class labels
verbose_name = {
    0: "Normal",
    1: "Doubtful",
    2: "Mild",
    3: "Moderate",
    4: "Severe"
}

# Load models
mobilenet = load_model('knee_mobilenet.h5')
vgg16 = load_model('knee_vgg16.h5')

def predict_label(img_path):
    test_image = image.load_img(img_path, target_size=(224,224))
    test_image = image.img_to_array(test_image)/255.0
    test_image = test_image.reshape(1, 224, 224, 3)

    predict_x = vgg16.predict(test_image) 
    classes_x = np.argmax(predict_x, axis=1)
    return verbose_name[classes_x[0]]

def predict_labels(img_path):
    test_image = image.load_img(img_path, target_size=(224,224))
    test_image = image.img_to_array(test_image)/255.0
    test_image = test_image.reshape(1, 224, 224, 3)

    predict_x = mobilenet.predict(test_image) 
    classes_x = np.argmax(predict_x, axis=1)
    return verbose_name[classes_x[0]]


USERS_FILE = 'users.json'

# def load_users():
#     if os.path.exists(USERS_FILE):
#         with open(USERS_FILE, 'r') as file:
#             return json.load(file)
#     return {}
def get_user_from_db(uname):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Query the database to get the user based on the username
    cursor.execute("SELECT * FROM users WHERE uname = %s", (uname,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return user

def save_users(users):
    with open(USERS_FILE, 'w') as file:
        json.dump(users, file, indent=4)
        
@app.route("/")
@app.route("/first")
def first():
    return render_template('first.html')
    
@app.route("/login")
def login():
    return render_template('login.html')    

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    # users = load_users()

    user = get_user_from_db(data['uname'])

    if user and check_password_hash(user['password_hash'], data['pwd']):
        user_data = {
            'uname': user['uname'],
            'email': user['email'],
            'age': user['age'],
            'gender': user['gender']
        }
        return jsonify({'status': 'success', 'message': 'Login successful','user':user_data})
    return jsonify({'status': 'fail', 'message': 'Invalid credentials'}), 401
# def login_user():
#     data = request.get_json()
#     users = load_users()

#     user = users.get(data['uname'])
#     if user and check_password_hash(user['password'], data['pwd']):
#         return jsonify({'status': 'success', 'message': 'Login successful'})
#     return jsonify({'status': 'fail', 'message': 'Invalid credentials'}), 401

# @app.route('/register', methods=['GET', 'POST'])
# def register_user():
#     if request.method == 'POST':
#         data = request.get_json()  # Get JSON data from the request
#         users = load_users()

#         if data['uname'] in users:
#             return jsonify({'status': 'fail', 'message': 'Username already exists'}), 400  # 400 instead of 404

#         users[data['uname']] = {
#             'email': data['email'],
#             'age': data['age'],
#             'gender': data['gender'],
#             'password': generate_password_hash(data['pwd'])
#         }

#         save_users(users)
#         return jsonify({'status': 'success', 'message': 'Registered successfully'})
    
#     # Handle GET request if necessary (just to render the registration page)
#     return render_template('register.html')
@app.route('/register', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        data = request.get_json()  # Get JSON data from the request
        uname = data['uname']
        email = data['email']
        age = data['age']
        gender = data['gender']
        password = generate_password_hash(data['pwd'])

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE uname = %s", (uname,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'status': 'fail', 'message': 'Username already exists'}), 400

        cursor.execute(
            "INSERT INTO users (uname, email, age, gender, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (uname, email, age, gender, password)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'message': 'Registered successfully'})
    else:
        return render_template('register.html')

@app.route("/chart")
def chart():
    return render_template('chart.html')

@app.route("/performance")
def performance():
    return render_template('performance.html')

@app.route("/index", methods=['GET', 'POST'])
def index():
    return render_template("index.html")

# @app.route("/submit", methods=['GET', 'POST'])
# def get_output():
#     if request.method == 'POST':
#         img = request.files.get('my_image')
#         model = request.form.get('model')
        
#         # Ensure both image and model were provided
#         if img and model:
#             img_path = "static/tests/" + img.filename	
#             img.save(img_path)

#             if model == 'VGG16':
#                 predict_result = predict_label(img_path)
#             elif model == 'MobileNetV2':
#                 predict_result = predict_labels(img_path)
#             else:
#                 predict_result = "Unknown model selected"
            
#             return render_template("result.html", prediction=predict_result, img_path=img_path, model=model)
        
#         # Handle case if image or model is missing
#         return "Image or model selection is missing. Please try again.", 400  # 400: Bad Request
    
#     # Fallback if the request method is not POST
#     return "Invalid request method. Please submit the form correctly.", 405  # 405: Method Not Allowed

@app.route("/submit", methods=['GET', 'POST'])
def get_output():
    if request.method == 'POST':
        img = request.files.get('my_image')
        model = request.form.get('model')
        uname = request.form.get('username')  # Should be passed from frontend (e.g. JS localStorage)

        if img and model and uname:
            img_path = "static/tests/" + img.filename	
            img.save(img_path)

            if model == 'VGG16':
                predict_result = predict_label(img_path)
            elif model == 'MobileNetV2':
                predict_result = predict_labels(img_path)
            else:
                predict_result = "Unknown model selected"

            # Insert prediction into DB
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO prediction_history (uname, image_name, prediction, model_used, predicted_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (uname, img.filename, predict_result, model, datetime.now()))
            conn.commit()
            cursor.close()
            conn.close()

            return render_template("result.html", prediction=predict_result, img_path=img_path, model=model)

        return "Missing required data", 400
    return "Invalid request", 405


@app.route('/get_prediction_history/<uname>')
def get_prediction_history(uname):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT image_name, prediction, model_used,predicted_at
        FROM prediction_history
        WHERE uname = %s
        ORDER BY predicted_at DESC
    """
    cursor.execute(query, (uname,))
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True)
