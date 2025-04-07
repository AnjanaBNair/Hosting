import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics import mean_squared_error
import joblib
import numpy as np
import os
from django.conf import settings

# ----------- Data Preprocessing Utilities -----------

def load_data():
    """Load enrollment data from a CSV file."""
    enrollments_path = os.path.join(os.path.dirname(__file__), 'enrollments.csv')
    enrollments_df = pd.read_csv(enrollments_path)
    return enrollments_df

def encode_data(enrollments_df):
    """Encode categorical data and create numerical columns."""
    le_courses = LabelEncoder()
    le_students = LabelEncoder()
    
    # Encode 'Course Name' and 'Student ID'
    enrollments_df['Course Name Encoded'] = le_courses.fit_transform(enrollments_df['Course Name'])
    enrollments_df['Student ID Encoded'] = le_students.fit_transform(enrollments_df['Student ID'])

    # Encode 'Completion Status'
    enrollments_df['Completion Status Encoded'] = enrollments_df['Completion Status'].apply(
        lambda x: 1 if x == 'Completed' else 0
    )
    
    return enrollments_df, le_courses, le_students

def create_user_course_matrix(enrollments_df):
    """Create a pivot table of students and their course enrollments."""
    user_course_matrix = enrollments_df.pivot_table(
        index='Student ID Encoded',
        columns='Course Name Encoded',
        values='Completion Status Encoded',
        fill_value=0
    )
    return user_course_matrix

# ----------- Model Training Utilities -----------

def train_svd_model(user_course_matrix, n_components=15):
    """Train an SVD model on the user-course matrix."""
    svd = TruncatedSVD(n_components=n_components)
    user_factors = svd.fit_transform(user_course_matrix)
    course_factors = svd.components_
    
    return svd, user_factors, course_factors

# ----------- Model Prediction Utilities -----------

def generate_recommendations(user_vector, course_factors, le_courses, top_n=5):
    """Generate course recommendations for a given student vector."""
    predicted_scores = user_vector @ course_factors
    recommended_course_idx = predicted_scores.argsort()[::-1][:top_n]  # Sort in descending order
    
    # Convert course indices back to course names
    recommended_courses = le_courses.inverse_transform(recommended_course_idx)
    
    return recommended_courses

# ----------- Model Evaluation Utilities -----------

def evaluate_model(user_factors, course_factors, test_data):
    """Evaluate the SVD model using RMSE on the test dataset."""
    y_true = test_data.values.flatten()
    y_pred = (user_factors @ course_factors).flatten()
    
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    return rmse

# ----------- Model Persistence Utilities -----------

def save_model(model, filename):
    """Save a model to a file using joblib."""
    joblib.dump(model, filename)

def load_model(filename):
    """Load a model from a file using joblib."""
    model = joblib.load(filename)
    return model

# ----------- Main Execution -----------

if __name__ == "__main__":
    # Step 1: Load and prepare the data
    enrollments_df = load_data()
    encoded_df, le_courses, le_students = encode_data(enrollments_df)
    user_course_matrix = create_user_course_matrix(encoded_df)

    # Step 2: Train the SVD model
    svd_model, user_factors, course_factors = train_svd_model(user_course_matrix)

    # Optional Step: Evaluate the model if you have test data
    # rmse = evaluate_model(user_factors, course_factors, test_data)
    # print(f"Model RMSE: {rmse}")

    # Step 3: Generate recommendations for a specific student
    student_index = 0  # Change this for different students
    user_vector = user_factors[student_index]
    recommended_courses = generate_recommendations(user_vector, course_factors, le_courses)

    print(f"Recommended courses for Student {student_index + 1}: {recommended_courses}")

    # Step 4: Save the model for future use
    save_model(svd_model, 'svd_model.pkl')
    

