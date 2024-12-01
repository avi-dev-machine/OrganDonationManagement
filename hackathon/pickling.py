import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
import joblib

# Sample data: Replace with your actual dataset
data = {
    'donor_age': [25, 45, 60, 30, 50],
    'recipient_age': [30, 50, 70, 28, 48],
    'urgency_level': [5, 8, 10, 3, 7],
    'distance': [50, 100, 200, 10, 60],  # in km
    'donor_blood_type': ['A+', 'B-', 'O+', 'AB+', 'A-'],
    'recipient_blood_type': ['A+', 'B-', 'O+', 'AB+', 'A-'],
    'compatibility_score': [85, 70, 55, 95, 80]  # Target scores scaled to 0-100
}

# Create a DataFrame
df = pd.DataFrame(data)

# Encode blood types
label_encoder = LabelEncoder()
df['donor_blood_type_encoded'] = label_encoder.fit_transform(df['donor_blood_type'])
df['recipient_blood_type_encoded'] = label_encoder.transform(df['recipient_blood_type'])

# Feature Engineering
df['age_similarity'] = 1 / (1 + abs(df['donor_age'] - df['recipient_age']))
df['distance_score'] = 1 / (1 + df['distance'])

# Features and Target
features = [
    'donor_blood_type_encoded',
    'recipient_blood_type_encoded',
    'urgency_level',
    'age_similarity',
    'distance_score'
]
X = df[features]
y = df['compatibility_score']

# Scale features
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# Train the model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_scaled, y)

# Save the model, scaler, and label encoder
joblib.dump(model, 'organ_matching_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
joblib.dump(label_encoder, 'label_encoder.pkl')

print("Model, scaler, and label encoder saved!")
