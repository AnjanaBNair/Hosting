import pandas as pd
import random

# Define course data based on the provided dataset
course_data = [
    (8, 'Cloud Computing', 'Basics of Cloud Computing', 'free', 'Basic'),
    (9, 'CPP', 'Introduction to CPP', 'free', 'Basic'),
    (10, 'Mobile Computing', 'Fundamentals', 'free', 'Intermediate'),
    (11, 'Introduction to Data Science', 'The Data Science Foundations course...', 'free', 'Basic'),
    (12, 'Cyber Security', 'Cyber Security Fundamental', 'free', 'Intermediate'),
    (14, 'Python', 'Python is a powerful and easy-to-learn language...', 'free', 'Basic'),
    (21, 'Introduction to Management', 'Foundational understanding of management principles...', 'paid', 'Basic'),
]

# Create a DataFrame for the courses
courses_df = pd.DataFrame(course_data, columns=['course_id', 'course_name', 'description', 'price', 'difficulty'])

# Save the course data to course.csv
courses_df.to_csv('course_synthetic.csv', index=False)

# Create synthetic enrollment data for 1000 students
enrollments_data = []

for student_id in range(1, 1001):  # Create 1000 synthetic students
    # Randomly choose the number of courses a student will enroll in (1 to 5)
    num_courses = random.randint(1, 5)
    
    # Randomly select courses for the student without replacement
    enrolled_courses = random.sample([course[0] for course in course_data], k=num_courses)

    # Add each enrollment to the list
    for course_id in enrolled_courses:
        enrollments_data.append({'student_id': student_id, 'course_id': course_id})

# Create a DataFrame for the enrollments
enrollments_df = pd.DataFrame(enrollments_data)

# Save the enrollment data to enrollment.csv
enrollments_df.to_csv('enrollment_synthetic.csv', index=False)

# Display the first few entries of the synthetic enrollment data
print(enrollments_df.head())
