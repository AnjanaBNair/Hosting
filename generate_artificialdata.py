import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextedge.settings')  # Replace 'nextedge' with the correct project name
django.setup()

# Now you can import your Django models
from user.models import StaffCourse  # Adjust the import according to your app structure

import random
from datetime import datetime, timedelta
import pandas as pd

# Provided list of course names from the StaffCourse model
course_objects = StaffCourse.objects.filter(lock=True, active=True)
course_names = [course.name for course in course_objects]  # Assuming 'course_name' is the field in StaffCourse

# Parameters
num_students = 2000  # Number of different students
num_enrollments = 5000  # Total number of enrollments

# Generate student data
students = [{'Student ID': i+1, 'Name': f'Student {i+1}'} for i in range(num_students)]
students_df = pd.DataFrame(students)

# Generate enrollment data
enrollments = []
for _ in range(num_enrollments):
    course_id = random.randint(0, len(course_names) - 1)  # Select a valid course index
    student_id = random.randint(1, num_students)
    
    # Generate a random timestamp within the past 365 days
    enrollment_timestamp = datetime.now() - timedelta(days=random.randint(0, 365))
    completion_status = random.choice(['Completed', 'In Progress'])  # Random completion status
    
    # Look up the course name based on the course ID
    course_name = course_names[course_id]
    
    enrollments.append({
        'Enrollment ID': len(enrollments) + 1,
        'Course Name': course_name,
        'Student ID': student_id,
        'Enrollment Timestamp': enrollment_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'Completion Status': completion_status
    })

# Save to CSV files
enrollments_df = pd.DataFrame(enrollments)
enrollments_df.to_csv('enrollments.csv', index=False)
students_df.to_csv('students.csv', index=False)

# Confirm files are saved
print("CSV files 'enrollments.csv' and 'students.csv' generated successfully!")
