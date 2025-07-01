
from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = "supersecretkey"

client = MongoClient("mongodb://localhost:27017")
db = client['capturemoments']

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
    photographers = list(db.photographers.find().limit(3))
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
            "password": hashed_pw,
            "created_at": datetime.utcnow()
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
    search_query = request.args.get('search', '').strip()

    if search_query:
        photographers = list(db.photographers.find({
            "name": {"$regex": search_query, "$options": "i"}
        }))
    else:
        photographers = list(db.photographers.find())

    return render_template('photographers.html', photographers=photographers, search=search_query)

@app.route('/profile')
@login_required
def profile():
    user = db.users.find_one({"_id": ObjectId(session['user_id'])})
    return render_template('profile.html', user=user)

@app.route('/my-bookings')
@login_required
def my_bookings():
    bookings = list(db.bookings.aggregate([
        {
            "$match": {
                "user_id": ObjectId(session['user_id'])
            }
        },
        {
            "$lookup": {
                "from": "photographers",
                "localField": "photographer_id",
                "foreignField": "_id",
                "as": "photographer"
            }
        },
        {
            "$unwind": "$photographer"
        },
        {
            "$sort": {"created_at": -1}
        }
    ]))
    return render_template('my_bookings.html', bookings=bookings)

@app.template_filter('format_date')
def format_date(date):
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    return date.strftime('%B %d, %Y')

@app.route('/book/<photographer_id>', methods=['GET', 'POST'])
@login_required
def book(photographer_id):
    try:
        photographer = db.photographers.find_one({"_id": ObjectId(photographer_id)})
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

            # Convert dates for validation
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

                # Check for existing bookings in the date range
                existing_booking = db.bookings.find_one({
                    "photographer_id": ObjectId(photographer_id),
                    "$or": [
                        {
                            "start_date": {"$lte": end_date},
                            "end_date": {"$gte": start_date}
                        }
                    ]
                })

                if existing_booking:
                    available_after = existing_booking['end_date']
                    if isinstance(available_after, str):
                        available_after = datetime.strptime(available_after, '%Y-%m-%d')
                    available_str = available_after.strftime('%B %d, %Y')
                    flash(f"This photographer is already booked and will be available after {available_str}.", "danger")
                    return render_template('book.html', photographer=photographer)


                # Create booking
                booking = {
                    "user_id": ObjectId(session['user_id']),
                    "photographer_id": ObjectId(photographer_id),
                    "event_type": event_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "location": location,
                    "notes": notes,
                    "status": "confirmed",
                    "created_at": datetime.utcnow()
                }

                db.bookings.insert_one(booking)
                flash("Booking successful!", "success")
                return redirect(url_for('booking_success'))

            except ValueError:
                flash("Invalid date format.", "danger")
                return render_template('book.html', photographer=photographer)

        return render_template('book.html', photographer=photographer)

    except Exception as e:
        print(f"Booking error: {e}")
        flash("An error occurred while processing your request.", "danger")
        return redirect(url_for('photographers'))

@app.route('/booking-success')
@login_required
def booking_success():
    return render_template('success.html')


# @app.route('/my-bookings')
# @login_required
# def my_bookings():
#     bookings = list(db.bookings.aggregate([
#         {
#             "$match": {
#                 "user_id": ObjectId(session['user_id'])
#             }
#         },
#         {
#             "$lookup": {
#                 "from": "photographers",
#                 "localField": "photographer_id",
#                 "foreignField": "_id",
#                 "as": "photographer"
#             }
#         },
#         {
#             "$unwind": "$photographer"
#         },
#         {
#             "$sort": {"created_at": -1}
#         }
#     ]))
#     return render_template('my_bookings.html', bookings=bookings)

@app.template_filter('format_date')
def format_date(date):
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d')
    return date.strftime('%B %d, %Y')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)