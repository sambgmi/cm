from flask import Flask, jsonify, request

# Step 1: Create the Flask app instance
app = Flask(__name__)

# Step 2: Dummy data for photographers (simulating database)
photographers = [
    {"id": "p1", "name": "Amit Lensman", "skills": ["Wedding", "Portrait"]},
    {"id": "p2", "name": "Sara Clickz", "skills": ["Fashion", "Event"]}
]

# Step 3: Dummy availability data mapped by photographer ID
availability_data = {
    "p1": ["2025-06-20", "2025-06-23"],
    "p2": ["2025-06-19", "2025-06-22"]
}

# Step 4: Define routes

@app.route('/photographers', methods=['GET'])
def get_photographers():
    """Return all photographers"""
    return jsonify(photographers)

@app.route('/photographers/<photographer_id>', methods=['GET'])
def get_photographer(photographer_id):
    """Return details of a specific photographer"""
    photographer = next((p for p in photographers if p["id"] == photographer_id), None)
    if photographer:
        return jsonify(photographer)
    return jsonify({"error": "Photographer not found"}), 404

@app.route('/availability/<photographer_id>', methods=['GET'])
def get_availability(photographer_id):
    """Return availability dates for a specific photographer"""
    if photographer_id in availability_data:
        return jsonify({"id": photographer_id, "available_dates": availability_data[photographer_id]})
    return jsonify({"error": "Photographer not found"}), 404

@app.route('/booking', methods=['POST'])
def create_booking():
    """Simulate creating a booking"""
    if not request.json:
        return jsonify({"error": "Invalid request data"}), 400
        
    data = request.json
    required_fields = ['photographer_id', 'date', 'client_name', 'event_type']
    
    # Check if required fields are present
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
        
    # Check if photographer exists
    if data['photographer_id'] not in [p['id'] for p in photographers]:
        return jsonify({"error": "Photographer not found"}), 404
        
    # Check if date is available
    if data['date'] not in availability_data.get(data['photographer_id'], []):
        return jsonify({"error": "Date not available"}), 400
        
    # In a real app, we would save the booking to a database here
    # For this demo, we just return success
    booking_id = "b" + str(hash(data['photographer_id'] + data['date']))[:6]
    
    return jsonify({
        "message": "Booking created successfully",
        "booking_id": booking_id,
        "details": data
    }), 201

# Step 5: Add a health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

# Run the application
if __name__ == '__main__':
    app.run(debug=True)