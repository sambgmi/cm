# app.py - Complete AWS DynamoDB Integration
import os
import boto3
import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

app = Flask(__name__)
# Use environment variable for secret key in production
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS services
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
sns = boto3.client('sns', region_name='ap-south-1')

# Define DynamoDB tables
users_table = dynamodb.Table('photography_users')
bookings_table = dynamodb.Table('photography_bookings')
photographers_table = dynamodb.Table('photography_photographers')

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    try:
        # Get first 3 photographers using DynamoDB scan
        response = photographers_table.scan(Limit=3)
        photographers = response.get('Items', [])
        return render_template('index.html', photographers=photographers)
    except ClientError as e:
        logger.error(f"Error fetching photographers: {e}")
        return render_template('index.html', photographers=[])

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')

        try:
            # Check if username exists using GSI
            response = users_table.query(
                IndexName='username-index',
                KeyConditionExpression=Key('username').eq(username)
            )
            
            if response['Items']:
                flash("Username already exists.", "danger")
                return render_template('signup.html')

            # Check if email exists using GSI
            response = users_table.query(
                IndexName='email-index',
                KeyConditionExpression=Key('email').eq(email)
            )
            
            if response['Items']:
                flash("Email already registered.", "danger")
                return render_template('signup.html')

            # Create new user
            user_id = str(uuid.uuid4())
            hashed_pw = generate_password_hash(password)
            
            users_table.put_item(
                Item={
                    'user_id': user_id,
                    'username': username,
                    'email': email,
                    'password': hashed_pw,
                    'created_at': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"New user registered: {username}")
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('login'))
            
        except ClientError as e:
            logger.error(f"Error during signup: {e}")
            flash("An error occurred during signup. Please try again.", "danger")
            return render_template('signup.html')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        try:
            # Query user by username using GSI
            response = users_table.query(
                IndexName='username-index',
                KeyConditionExpression=Key('username').eq(username)
            )
            
            if response['Items'] and check_password_hash(response['Items'][0]['password'], password):
                user = response['Items'][0]
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                logger.info(f"User logged in: {username}")
                flash("Login successful!", "success")
                return redirect(url_for('index'))
            else:
                flash("Invalid username or password.", "danger")
                
        except ClientError as e:
            logger.error(f"Error during login: {e}")
            flash("An error occurred during login. Please try again.", "danger")
            
    return render_template('login.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/logout')
def logout():
    username = session.get('username', 'Unknown')
    session.clear()
    logger.info(f"User logged out: {username}")
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

@app.route('/photographers')
def photographers():
    search_query = request.args.get('search', '').strip()
    
    try:
        if search_query:
            # DynamoDB doesn't support case-insensitive search natively
            # We'll scan and filter manually for this example
            response = photographers_table.scan()
            photographers_list = [
                p for p in response.get('Items', [])
                if search_query.lower() in p.get('name', '').lower()
            ]
        else:
            response = photographers_table.scan()
            photographers_list = response.get('Items', [])
            
        return render_template('photographers.html', 
                             photographers=photographers_list, 
                             search=search_query)
        
    except ClientError as e:
        logger.error(f"Error fetching photographers: {e}")
        return render_template('photographers.html', photographers=[], search=search_query)

@app.route('/profile')
@login_required
def profile():
    try:
        response = users_table.get_item(Key={'user_id': session['user_id']})
        user = response.get('Item')
        if user and 'created_at' in user:
            # Convert ISO string to datetime for template
            user['created_at'] = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
        return render_template('profile.html', user=user)
    except ClientError as e:
        logger.error(f"Error fetching user profile: {e}")
        flash("Error loading profile.", "danger")
        return redirect(url_for('index'))

@app.route('/my-bookings')
@login_required
def my_bookings():
    try:
        # Get user's bookings using GSI
        response = bookings_table.query(
            IndexName='user-id-index',
            KeyConditionExpression=Key('user_id').eq(session['user_id'])
        )
        
        bookings = []
        for booking in response.get('Items', []):
            # Get photographer details for each booking
            photographer_response = photographers_table.get_item(
                Key={'photographer_id': booking['photographer_id']}
            )
            if photographer_response.get('Item'):
                booking['photographer'] = photographer_response['Item']
                bookings.append(booking)
        
        # Sort by created_at (newest first)
        bookings.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return render_template('my_bookings.html', bookings=bookings)
        
    except ClientError as e:
        logger.error(f"Error fetching bookings: {e}")
        return render_template('my_bookings.html', bookings=[])

@app.template_filter('format_date')
def format_date(date):
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            return date
    return date.strftime('%B %d, %Y')

@app.route('/book/<photographer_id>', methods=['GET', 'POST'])
@login_required
def book(photographer_id):
    try:
        # Get photographer details
        response = photographers_table.get_item(Key={'photographer_id': photographer_id})
        photographer = response.get('Item')
        
        if not photographer:
            flash("Photographer not found.", "danger")
            return redirect(url_for('photographers'))

        if request.method == 'POST':
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            event_type = request.form.get('event_type')
            location = request.form.get('location')
            notes = request.form.get('notes', '')

            # Basic validation
            if not all([start_date, end_date, event_type, location]):
                flash("Please fill in all required fields.", "danger")
                return render_template('book.html', photographer=photographer)
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                current_dt = datetime.utcnow()

                # Validate dates
                if start_dt < current_dt.replace(hour=0, minute=0, second=0, microsecond=0):
                    flash("Start date cannot be in the past.", "danger")
                    return render_template('book.html', photographer=photographer)

                if end_dt < start_dt:
                    flash("End date must be after start date.", "danger")
                    return render_template('book.html', photographer=photographer)

                if (end_dt - start_dt).days > 14:
                    flash("Booking duration cannot exceed 14 days.", "danger")
                    return render_template('book.html', photographer=photographer)

                # Check for conflicting bookings using photographer GSI
                response = bookings_table.query(
                    IndexName='photographer-id-index',
                    KeyConditionExpression=Key('photographer_id').eq(photographer_id)
                )
                
                for existing_booking in response.get('Items', []):
                    existing_start = existing_booking['start_date']
                    existing_end = existing_booking['end_date']
                    
                    # Check for date overlap
                    if not (end_date < existing_start or start_date > existing_end):
                        flash(f"This photographer is already booked from {existing_start} to {existing_end}.", "danger")
                        return render_template('book.html', photographer=photographer)

                # Create booking
                booking_id = str(uuid.uuid4())
                booking = {
                    'booking_id': booking_id,
                    'user_id': session['user_id'],
                    'photographer_id': photographer_id,
                    'event_type': event_type,
                    'start_date': start_date,
                    'end_date': end_date,
                    'location': location,
                    'notes': notes,
                    'status': 'confirmed',
                    'created_at': datetime.utcnow().isoformat()
                }

                bookings_table.put_item(Item=booking)
                logger.info(f"Booking created: {booking_id} for user {session['username']}")
                flash("Booking successful!", "success")
                return redirect(url_for('booking_success'))

            except ValueError:
                flash("Invalid date format.", "danger")
                return render_template('book.html', photographer=photographer)

        return render_template('book.html', photographer=photographer)

    except ClientError as e:
        logger.error(f"Booking error: {e}")
        flash("An error occurred while processing your request.", "danger")
        return redirect(url_for('photographers'))

@app.route('/booking-success')
@login_required
def booking_success():
    return render_template('success.html')

# Helper function to populate sample photographers (run once)
def populate_sample_photographers():
    """Run this function once to add sample photographers to DynamoDB"""
    sample_photographers = [
        {
            'photographer_id': str(uuid.uuid4()),
            'name': 'Alex Johnson',
            'specialty': 'Wedding Photography',
            'bio': 'Capturing timeless wedding memories with artistic vision and 10+ years of experience.',
            'image': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=300&h=300&fit=crop&crop=face',
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'photographer_id': str(uuid.uuid4()),
            'name': 'Sarah Miller',
            'specialty': 'Portrait Photography',
            'bio': 'Telling stories through expressive portraits and lifestyle photography.',
            'image': 'https://images.unsplash.com/photo-1494790108755-2616b332c3ae?w=300&h=300&fit=crop&crop=face',
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'photographer_id': str(uuid.uuid4()),
            'name': 'Michael Chen',
            'specialty': 'Event Photography',
            'bio': 'Professional event coverage with attention to detail and creative moments.',
            'image': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=300&h=300&fit=crop&crop=face',
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'photographer_id': str(uuid.uuid4()),
            'name': 'Emma Wilson',
            'specialty': 'Fashion Photography',
            'bio': 'High-fashion and commercial photography with creative flair.',
            'image': 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=300&h=300&fit=crop&crop=face',
            'created_at': datetime.utcnow().isoformat()
        },
        {
            'photographer_id': str(uuid.uuid4()),
            'name': 'David Rodriguez',
            'specialty': 'Corporate Photography',
            'bio': 'Professional corporate headshots and business event photography.',
            'image': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=300&h=300&fit=crop&crop=face',
            'created_at': datetime.utcnow().isoformat()
        }
    ]
    
    try:
        for photographer in sample_photographers:
            photographers_table.put_item(Item=photographer)
            logger.info(f"Added photographer: {photographer['name']}")
        print("Sample photographers added successfully!")
    except ClientError as e:
        logger.error(f"Error adding sample photographers: {e}")

if __name__ == '__main__':
    logger.info("Starting Capture Moments app with AWS DynamoDB")
    
    # Uncomment the line below to populate sample photographers (run only once)
    populate_sample_photographers()
    
    app.run(host='0.0.0.0', port=5000, debug=True)