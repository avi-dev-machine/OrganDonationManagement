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
        return redirect('/')
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

@app.route('/match/<int:recipient_id>')
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
        SELECT full_name, blood_type, organ, age, latitude, longitude
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
            'full_name': donor[0],
            'blood_type': donor[1],
            'organ': donor[2],
            'age': donor[3],
            'latitude': float(donor[4]),
            'longitude': float(donor[5])
        }

        # Encode blood types
        donor_blood_type_encoded = label_encoder.transform([donor_data['blood_type']])[0]
        receiver_blood_type_encoded = label_encoder.transform([recipient_data['blood_type']])[0]

        # Calculate distance (simplified Euclidean distance)
        location_distance = ((recipient_data['latitude'] - donor_data['latitude']) ** 2 +
                             (recipient_data['longitude'] - donor_data['longitude']) ** 2) ** 0.5

        # Calculate age similarity
        age_similarity = 1 / (1 + abs(donor_data['age'] - recipient_data['age']))

        # Prepare input for the model
        input_data = pd.DataFrame([{
            'donor_blood_type_encoded': donor_blood_type_encoded,
            'recipient_blood_type_encoded': receiver_blood_type_encoded,
            'urgency_level': recipient_data['urgency_score'],
            'age_similarity': age_similarity,
            'distance_score': 1 / (1 + location_distance)
        }])

        # Scale input data
        input_data_scaled = scaler.transform(input_data)

        # Predict compatibility score
        compatibility_score = model.predict(input_data_scaled)[0]

        # Append result
        results.append({
            'donor_name': donor_data['full_name'],
            'organ': donor_data['organ'],
            'compatibility_score': round(compatibility_score, 2)
        })

    # Render results
    return render_template('match.html', recipient_name=recipient_data['full_name'], results=results)

if __name__ == '__main__':
    app.run(debug=True)
