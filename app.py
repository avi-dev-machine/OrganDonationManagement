from flask import Flask, render_template, request, redirect
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
import joblib
import pandas as pd
import sqlite3

app = Flask(__name__)

# Load pre-trained model, scaler, and label encoder
model = joblib.load('organ_matching_model.pkl')
scaler = joblib.load('scaler.pkl')
label_encoder = joblib.load('label_encoder.pkl')

# SQLite database file name
DB_FILE = 'organ_donation.db'



#distance

import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in kilometers
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c  # in kilometers
    return distance


@app.route('/')
def index():
    return render_template('home.html')

@app.route('/form')
def form():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    form_type = request.form.get('form_type')  # Identify donor/recipient form
    full_name = request.form.get('fullName')
    email = request.form.get('email')
    password = request.form.get('password')
    blood_type = request.form.get('bloodType')
    age = int(request.form.get('age'))

    # Fetch longitude and latitude conditionally based on form type
    longitude = float(request.form.get(f'longitude_{form_type}'))
    latitude = float(request.form.get(f'latitude_{form_type}'))

    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    if form_type == 'donor':
        organ = request.form.get('organs')
        query = """
            INSERT INTO donors (full_name, email, password, blood_type, organ, age, longitude, latitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = (full_name, email, password, blood_type, organ, age, longitude, latitude)
        cursor.execute(query, data)
        connection.commit()
        cursor.close()
        connection.close()
        return render_template('confirmation_card.html', user_type='donor', full_name=full_name, 
                               email=email, blood_type=blood_type, organ=organ, age=age,
                               longitude=longitude, latitude=latitude)
    elif form_type == 'recipient':
        needed_organ = request.form.get('neededOrgan')
        urgency_level = int(request.form.get('urgencyLevel'))
        query = """
            INSERT INTO recipients (full_name, email, password, blood_type, needed_organ, urgency_level, age, longitude, latitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        data = (full_name, email, password, blood_type, needed_organ, urgency_level, age, longitude, latitude)
        cursor.execute(query, data)

        # Fetch the recipient ID of the inserted record
        recipient_id = cursor.lastrowid
        connection.commit()
        cursor.close()
        connection.close()

        # Redirect to the match page for the new recipient
        return redirect(f'/match/{recipient_id}')

@app.route('/match/<int:recipient_id>', methods=['GET', 'POST'])
def match(recipient_id):
    # Fetch recipient data from the database
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    recipient_query = """
        SELECT full_name, blood_type, needed_organ, urgency_level, age, latitude, longitude
        FROM recipients
        WHERE id = ?
    """
    cursor.execute(recipient_query, (recipient_id,))
    recipient = cursor.fetchone()

    if not recipient:
        return "Recipient not found", 404

    recipient_data = {
        'full_name': recipient[0],
        'blood_type': recipient[1],
        'needed_organ': recipient[2],
        'urgency_score': recipient[3],
        'age': recipient[4],
        'latitude': float(recipient[5]),
        'longitude': float(recipient[6])
    }

    # Fetch all donors matching the needed organ
    donor_query = """
        SELECT id,full_name, blood_type, organ, age, latitude, longitude
        FROM donors
        WHERE organ = ?
    """
    cursor.execute(donor_query, (recipient_data['needed_organ'],))
    donors = cursor.fetchall()
    cursor.close()
    connection.close()

    if not donors:
        return "No matching donors found", 404

    # Compatibility calculation
    results = []
    for donor in donors:
        donor_data = {
            'donor_id': donor[0],
            'full_name': donor[1],
            'blood_type': donor[2],
            'organ': donor[3],
            'age': donor[4],
            'latitude': float(donor[5]),
            'longitude': float(donor[6])
        }

        # Encode blood types
        donor_blood_type_encoded = label_encoder.transform([donor_data['blood_type']])[0]
        receiver_blood_type_encoded = label_encoder.transform([recipient_data['blood_type']])[0]

        # Calculate distance (simplified Euclidean distance)
        location_distance = haversine(recipient_data['latitude'], recipient_data['longitude'],
                              donor_data['latitude'], donor_data['longitude'])


        # Calculate age similarity
        age_similarity = 1 / (1 + abs(donor_data['age'] - recipient_data['age']))

        # Prepare input for the model
        # Calculate compatibility
        input_data = pd.DataFrame([{
        'age_similarity': 1 / (1 + abs(donor_data['age'] - recipient_data['age'])),
        'distance_score': 1 / (1 + location_distance),
        'urgency_level': recipient_data['urgency_score']
        }])

# Scale the input data
        input_data_scaled = scaler.transform(input_data)

# Predict compatibility score
        compatibility_score = model.predict(input_data_scaled)[0]


        # Append result
        results.append({
            'donor_id': donor_data['donor_id'],
            'donor_name': donor_data['full_name'],
            'organ': donor_data['organ'],
            'distance': round(location_distance, 2),
            'urgency_score': recipient_data['urgency_score'],
            'compatibility_score': round(compatibility_score, 2)
        })

    # Sort and filter
    
    if request.method == 'POST':
        sort_by = request.form.get('sort_by', 'compatibility_score')  # Default sorting by compatibility score
        min_score_str = request.form.get('min_score', '')
        max_distance_str = request.form.get('max_distance', '')

    # Convert min_score and max_distance to float only if they are not empty
        min_score = float(min_score_str) if min_score_str else 0  # Default to 0 if empty
        max_distance = float(max_distance_str) if max_distance_str else float('inf')  # Default to infinity if empty

    # Filter results
        results = [
            result for result in results
            if result['compatibility_score'] >= min_score and result['distance'] <= max_distance
    ]

    # Sort results
        results.sort(key=lambda x: x[sort_by], reverse=(sort_by != 'distance'))

    # Render results
    return render_template(
        'match.html',
        recipient_id=recipient_id,
        recipient_name=recipient_data['full_name'],
        results=results,
        sort_by=request.form.get('sort_by', 'compatibility_score'),
        min_score=request.form.get('min_score', ''),
        max_distance=request.form.get('max_distance', '')
    )


@app.route('/card/<int:donor_id>', methods=['GET'])
def card(donor_id):
    # Fetch donor details from the database
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    query = """
        SELECT full_name, email, blood_type, organ, age, longitude, latitude
        FROM donors
        WHERE id = ?
    """
    cursor.execute(query, (donor_id,))
    donor = cursor.fetchone()
    cursor.close()
    connection.close()

    if not donor:
        return "Donor not found", 404

    # Unpack donor details
    full_name, email, blood_type, organ, age, longitude, latitude = donor

    # Render the confirmation card template
    return render_template(
        'confirmation_card.html',
        user_type='donor',
        full_name=full_name,
        email=email,
        blood_type=blood_type,
        organ=organ,
        age=age,
        longitude=longitude,
        latitude=latitude
    )


@app.route('/map-matches/<int:recipient_id>')
def map_matches(recipient_id):
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    
    recipient_query = """
        SELECT full_name, latitude, longitude, needed_organ
        FROM recipients
        WHERE id = ?
    """
    cursor.execute(recipient_query, (recipient_id,))
    recipient = cursor.fetchone()

    if not recipient:
        return "Recipient not found", 404

    recipient_data = {
        'full_name': recipient[0],
        'latitude': float(recipient[1]),
        'longitude': float(recipient[2]),
        'needed_organ': recipient[3]
    }

    # Fetch donors matching the needed organ
    donor_query = """
        SELECT id,full_name, latitude, longitude, organ
        FROM donors
        WHERE organ = ?
    """
    cursor.execute(donor_query, (recipient_data['needed_organ'],))
    donors = cursor.fetchall()
    cursor.close()
    connection.close()

    if not donors:
        return "No matching donors found", 404

    # Prepare data for map rendering
    matches = [
        {
            'name': donor[1],
            'latitude': float(donor[2]),
            'longitude': float(donor[3]),
            'organ': donor[4]
        }
        for donor in donors
    ]

    return render_template('map_matches.html', 
                           recipient=recipient_data, 
                           matches=matches)



if __name__ == '__main__':
    app.run(debug=True)
