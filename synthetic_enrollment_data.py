import os
from click import BaseCommand
import django
# Set the environment variable for Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextedge.settings')
# Import Django
django.setup()

import pandas as pd
import csv
from user.models import CustomUser, StaffCourse, Enrollment  # Adjust the import according to your project structure
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

def predict_enrollment(student_id, new_course_info, enrollment_data, user_data, course_data):
    # Prepare features for prediction
    features = {
        'student_id': student_id,
        'course_mode': new_course_info['mode'],
        'course_payment': new_course_info['payment']
    }

    # Convert features to a DataFrame
    feature_df = pd.DataFrame([features])

    # Split the data into features (X) and target (y)
    X = enrollment_data[['student_id', 'course_id']]  # Adjust based on your actual data structure
    y = enrollment_data['status'].apply(lambda x: 1 if x == 'enrolled' else 0)

    # Split the data for training and testing to evaluate accuracy
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Train a model
    model = RandomForestClassifier()
    model.fit(X_train, y_train)

    # Make predictions on the test set
    y_pred = model.predict(X_test)

    # Calculate accuracy
    accuracy = accuracy_score(y_test, y_pred)
    
    # Print the accuracy in the command line
    print(f"Model accuracy: {accuracy * 100:.2f}%")

    # Make a prediction for the new course
    prediction = model.predict(feature_df)

    return prediction[0], accuracy  # Return both prediction and accuracy


def generate_enrollment_csv(file_path='enrollment_data.csv'):
    # Fetch all students and active courses
    students = CustomUser.objects.filter(role=CustomUser.STUDENT)
    courses = StaffCourse.objects.filter(active=True)

    # Prepare the data
    enrollment_data = pd.DataFrame(list(Enrollment.objects.values('student_id', 'course_id', 'status')))
    course_data = pd.DataFrame(list(StaffCourse.objects.values('id', 'name', 'mode', 'payment')))
    user_data = pd.DataFrame(list(CustomUser.objects.filter(role=CustomUser.STUDENT).values('id')))

    # Open CSV file for writing
    with open(file_path, mode='w', newline='') as file:
        writer = csv.writer(file)

        # Write CSV header
        writer.writerow(['student_id', 'course_name', 'course_mode', 'course_payment', 'department', 'enrolled', 'accuracy'])

        # Iterate over all students and active courses
        for student in students:
            for course in courses:
                # Check if the student is enrolled in this course
                is_enrolled = Enrollment.objects.filter(student=student, course=course).exists()

                # Predict enrollment for new courses
                if not is_enrolled:
                    # Predict enrollment
                    new_course_info = {
                        'mode': course.mode,
                        'payment': course.payment  # Ensure 'payment' is defined in your course model
                    }
                    prediction, accuracy = predict_enrollment(student.id, new_course_info, enrollment_data, user_data, course_data)

                    if prediction == 1:
                        # Recommend if the user is likely to enroll
                        recommended_courses = StaffCourse.objects.filter(department=course.department).exclude(id=course.id)
                        for rec_course in recommended_courses:
                            writer.writerow([
                                student.id,                # student_id
                                rec_course.name,           # course_name
                                rec_course.mode,           # course_mode
                                rec_course.payment,        # course_payment
                                rec_course.department.name,  # Assuming 'department' is a related object and has a 'name' field
                                'No',                      # enrollment status
                                accuracy                   # accuracy of the model
                            ])
                else:
                    # User is already enrolled, add to CSV
                    writer.writerow([
                        student.id,                # student_id
                        course.name,               # course_name
                        course.mode,               # course_mode
                        course.payment,            # course_payment
                        course.department.name,    # department
                        'Yes',                     # enrollment status
                        1.0                        # accuracy, can set to 1.0 as they are already enrolled
                    ])

class Command(BaseCommand):
    help = 'Generate a CSV file with student enrollment data'

    def handle(self, *args, **kwargs):
        generate_enrollment_csv('enrollment_data.csv')  # Call your function here
