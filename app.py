# from flask import Flask, render_template, request, redirect, url_for, flash, session
# from werkzeug.security import generate_password_hash, check_password_hash
# from datetime import datetime
# import logging
# import boto3
# import uuid
# import os
# from botocore.exceptions import ClientError

# app = Flask(__name__)
# app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_development')

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Initialize AWS services
# dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
# sns = boto3.client('sns', region_name='ap-south-1')

# # Define DynamoDB tables
# users_table = dynamodb.Table('photography_users')
# bookings_table = dynamodb.Table('photography_bookings')

# @app.route('/')
# def index():
#     if 'username' in session:
#         return redirect(url_for('home'))
#     return render_template('index.html')

# @app.route('/home')
# def home():
#     if 'username' not in session:
#         return redirect(url_for('login', next=request.path))
#     return render_template('home.html', username=session['username'])

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if 'username' in session:
#         return redirect(url_for('home'))
        
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
        
#         try:
#             # Query the users table
#             response = users_table.get_item(Key={'username': username})
#             user = response.get('Item')
            
#             if user and check_password_hash(user['password'], password):
#                 session['username'] = username
#                 session['fullname'] = user['fullname']
#                 flash('Login successful!', 'success')
                
#                 # Check if there's a next parameter in the query string for redirection
#                 next_page = request.args.get('next')
#                 if next_page:
#                     return redirect(next_page)
#                 return redirect(url_for('home'))
#             flash('Invalid username or password', 'error')
            
#         except ClientError as e:
#             logger.error(f"Database error during login: {e}")
#             flash('An error occurred during login. Please try again.', 'error')
    
#     return render_template('login.html')

# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if 'username' in session:
#         return redirect(url_for('home'))
        
#     if request.method == 'POST':
#         fullname = request.form['fullname']
#         username = request.form['username']
#         email = request.form['email']
#         password = request.form['password']
        
#         try:
#             # Check if username already exists
#             response = users_table.get_item(Key={'username': username})
#             if 'Item' in response:
#                 flash('Username already exists!', 'error')
#                 return redirect(url_for('signup'))
                
#             # Create new user in DynamoDB
#             users_table.put_item(
#                 Item={
#                     'username': username,
#                     'password': generate_password_hash(password),
#                     'fullname': fullname,
#                     'email': email,
#                     'created_at': datetime.now().isoformat()
#                 }
#             )
            
#             flash('Registration successful! Please login.', 'success')
#             return redirect(url_for('login'))
            
#         except Exception as e:
#             logger.error(f"Error during signup: {e}")
#             flash(f"An error occurred during registration: {e}", 'error')
            
#     return render_template('signup.html')

# @app.route('/logout')
# def logout():
#     session.pop('username', None)
#     session.pop('fullname', None)
#     flash('You have been logged out', 'info')
#     return redirect(url_for('index'))

# @app.route('/booking', methods=['GET', 'POST'])
# def booking():
#     if 'username' not in session:
#         flash('Please login to book a photographer', 'error')
#         return redirect(url_for('login', next=request.path))
        
#     event_type = request.args.get('event', '')
    
#     if request.method == 'POST':
#         try:
#             # Retrieve user data
#             response = users_table.get_item(Key={'username': session['username']})
#             user = response.get('Item', {})
            
#             # Validate required fields
#             required_fields = ['event_type', 'photographer', 'start_date', 'end_date', 'name', 'email', 'phone', 'package']
#             missing_fields = [field for field in required_fields if not request.form.get(field)]
            
#             if missing_fields:
#                 flash(f'Please fill all required fields: {", ".join(missing_fields)}', 'error')
#                 return redirect(url_for('booking', event=event_type))
                
#             # Generate a unique booking ID
#             booking_id = str(uuid.uuid4())
            
#             # Process booking form
#             booking_data = {
#                 'booking_id': booking_id,
#                 'username': session['username'],
#                 'user': session['fullname'],
#                 'user_email': user.get('email', ''),
#                 'name': request.form['name'],
#                 'email': request.form['email'],
#                 'phone': request.form['phone'],
#                 'event_type': request.form['event_type'],
#                 'photographer': request.form['photographer'],
#                 'start_date': request.form['start_date'],
#                 'end_date': request.form['end_date'],
#                 'package': request.form['package'],
#                 'payment_method': request.form['payment'],
#                 'notes': request.form.get('notes', ''),
#                 'booking_date': datetime.now().isoformat(),
#                 'status': 'Confirmed'
#             }
            
#             # Save to DynamoDB
#             bookings_table.put_item(Item=booking_data)
#             logger.info(f"Booking created with ID: {booking_id}")
            
#             # Send notification
#             # send_booking_notification(booking_data)
            
#             # Store booking ID in session for the success page
#             session['last_booking_id'] = booking_id
            
#             return redirect(url_for('success'))
            
#         except Exception as e:
#             logger.error(f"Error in booking form: {str(e)}")
#             flash(f'An error occurred: {str(e)}', 'error')
#             return redirect(url_for('booking', event=event_type))
            
#     return render_template('booking.html', event_type=event_type)

# @app.route('/success', methods=['GET', 'POST'])
# def success():
#     if 'username' not in session:
#         return redirect(url_for('login'))
        
#     # Just render the success template without passing booking details
#     return render_template('success.html')

# @app.route('/contact')
# def contact():
#     return render_template('contact.html')

# @app.route('/about')
# def about():
#     return render_template('about.html')

# @app.route('/services')
# def services():
#     return render_template('services.html')

# @app.route('/photographers')
# def photographers():
#     return render_template('photographers.html')

# if __name__ == "__main__":
#     # Create tables if they don't exist
    
#     # Run the Flask app
#     app.run(host='0.0.0.0', port=5000, debug=False)
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

client = MongoClient("mongodb://localhost:27017")
db = client['snapclick']

@app.route('/')
def index():
    photographers = list(db.photographers.find())
    return render_template('index.html', photographers=photographers)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')

        if db.users.find_one({"username": username}):
            flash("Username already exists.", "danger")
            return render_template('signup.html')

        if db.users.find_one({"email": email}):
            flash("Email already registered.", "danger")
            return render_template('signup.html')

        hashed_pw = generate_password_hash(password)
        db.users.insert_one({
            "username": username,
            "email": email,
            "password": hashed_pw
        })
        flash("Signup successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        user = db.users.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            flash("Login successful!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "danger")
            return render_template('login.html')
    return render_template('login.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@app.route('/photographers')
def photographers():
    photographers = list(db.photographers.find())
    return render_template('photographers.html', photographers=photographers)

@app.route('/book/<photographer_id>', methods=['GET', 'POST'])
def book(photographer_id):
    if not session.get('user_id'):
        flash("You must be logged in to book a photographer.", "danger")
        return redirect(url_for('login'))

    photographer = db.photographers.find_one({"_id": ObjectId(photographer_id)})
    if not photographer:
        flash("Photographer not found.", "danger")
        return redirect(url_for('photographers'))

    if request.method == 'POST':
        event_type = request.form.get('event_type')
        date = request.form.get('date')
        location = request.form.get('location')
        notes = request.form.get('notes')

        # Ensure date is in photographer's availability
        if date not in photographer.get('availability', []):
            flash("Selected date is not available for this photographer.", "danger")
            return render_template('book.html', photographer=photographer, now=datetime.now)

        db.bookings.insert_one({
            "user_id": ObjectId(session['user_id']),
            "photographer_id": photographer['_id'],
            "event_type": event_type,
            "date": date,
            "location": location,
            "notes": notes,
            "created_at": datetime.utcnow()
        })

        # Remove the booked date from photographer's availability
        db.photographers.update_one(
            {"_id": photographer['_id']},
            {"$pull": {"availability": date}}
        )

        return redirect(url_for('booking_success'))

    return render_template('book.html', photographer=photographer, now=datetime.now)

@app.route('/booking-success')
def booking_success():
    return render_template('success.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)