# user/utils/ml_utils.py
import pandas as pd
import joblib

def recommend_courses():
    # Load the model
    model = joblib.load('course_recommendation_model.pkl')

    # Load the enrollment data
    enrollments_df = pd.read_csv('enrollments.csv')

    # Count enrollments per course
    course_enrollment_counts = enrollments_df['Course Name'].value_counts().reset_index()
    course_enrollment_counts.columns = ['Course Name', 'Enrollment Count']

    # Prepare features for prediction
    features = course_enrollment_counts[['Enrollment Count']].values
    predicted_enrollments = model.predict(features)

    # Combine with course names
    recommendations = pd.DataFrame({
        'Course Name': course_enrollment_counts['Course Name'],
        'Predicted Enrollment Count': predicted_enrollments
    })

    # Sort by predicted enrollments
    recommendations = recommendations.sort_values(by='Predicted Enrollment Count', ascending=False).head(5)

    return recommendations.to_dict(orient='records')
