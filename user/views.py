import csv
import threading
from django.core.exceptions import ObjectDoesNotExist
from difflib import SequenceMatcher
import os
from pyexpat.errors import messages
from typing import Counter
import uuid
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from nextedge import settings
from django.contrib.auth.hashers import make_password, check_password
from train_model_script import create_user_course_matrix, encode_data, generate_recommendations, load_data, train_svd_model
from user import models
from user.models import Certificate, CustomUser, Department, Enrollment, Module, PasswordResetToken, Payment, Progress, Quiz, StaffProfile, Subdept, Topic, UserProfile,StaffCourse, DevelopmentProgram, ChatSession, ChatMessage, ChatbotKnowledge
from django.urls import reverse
from datetime import datetime, time, timedelta, timezone
from django.utils import timezone
from django.http import HttpResponse
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.http import JsonResponse
import json
from django.db.models import Count, Q
import pandas as pd
from django.core.files.storage import FileSystemStorage
import speech_recognition as sr
from googletrans import Translator
from moviepy import VideoFileClip
from deep_translator import GoogleTranslator
from pydub import AudioSegment
from django.conf import settings
from urllib.parse import unquote
import subprocess
from .models import Attendance, Expert, ProgramDay, ProgramMaterial, Registration, StudyMaterial, ProgramAttendance
from functools import wraps
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from io import BytesIO
import os
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.http import require_POST
from reportlab.lib.pagesizes import landscape
import qrcode
from datetime import date


def login_page(request):
    return render(request, 'user/login_page.html', {'is_register': False})

# def user_profile(request):
#     if request.method == 'POST':
#         user_id=request.user
#         first_name = request.POST.get('first_name')
#         last_name = request.POST.get('last_name')
#         phone_number = request.POST.get('phone_number')
#         bio = request.POST.get('bio')
#         country=request.POST.get('country')
#         profile_picture = request.FILES.get('profile_picture')
        
#         student_instance = user_profile.objects.create(first_name=first_name, last_name=last_name,
#                                                       bio=bio, profile_picture=profile_picture,
#                                                       phone_number=phone_number)
#         return redirect('studentindex')
        
#     return redirect(request,'user_profile.html')

def registerfn(request):
    if request.method == 'POST':
    # Handle registration
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        # Add validation logic here
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('login_page') 

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already taken.")
            return redirect('login_page') 

        user = CustomUser.objects.create_user(username=username, email=email, password=password1, role='student',is_staff=True)
        if user:
            return redirect('login_page')  # Redirect to student index page after successful registration
        else:
            messages.error(request, "Something went wrong. Try again.")
        
def loginfn(request):
    user=request.user
    if user.is_authenticated:
        if UserProfile.objects.filter(user=user).exists():
            return redirect('baseindex')
        else:
            return redirect('user_profile')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            request.session['logged_user'] = user.id 
            if user.is_superuser==True and user.is_staff==True:
                login(request, user)
                return redirect('main_page')
            elif user.role == 'student':
                if UserProfile.objects.filter(user=user).exists():
                    if UserProfile.objects.filter(user=user,active=True).exists():
                        login(request, user)
                        return redirect('baseindex')
                    else:
                       return render(request, 'user/login_page.html', {'deactivated_user': True})
                else:
                    return redirect('user_profile')
            elif user.role == 'instructor':
                if StaffProfile.objects.filter(user=user, active=True).exists():
                    login(request, user)
                    return redirect('landing')
                else:
                    return render(request, 'user/login_page.html', {'deactivated_user': True})
        else:
            messages.error(request, 'Invalid Credentials!Try Again')
            return redirect('login_page')
        
def send_password_reset_email(request, user, token):
    reset_url = request.build_absolute_uri(f'/new_password/{token}/')
    subject = 'Password Reset Request'
    context = {
        'user': user,
        'reset_url': reset_url,
    }
    html_content = render_to_string('user/mail_read.html', context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [user.email])
    email.attach_alternative(html_content, 'text/html')
    email.send()

def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get('email')
        associated_users = CustomUser.objects.filter(email=email)
        if associated_users.exists():
            for user in associated_users:
                token = PasswordResetToken.objects.create(user=user)
                send_password_reset_email(request, user, token.token)
            return HttpResponse('A password reset link has been sent to your email.')
        else:
            return HttpResponse('No user is associated with this email address.')
    return render(request, 'user/password_reset.html')

def reset_password(request, token):
    reset_token = PasswordResetToken.objects.filter(token=token, expiry__gt=timezone.now()).first()
    if not reset_token:
        return HttpResponse("Invalid or expired token.")
    
    if request.method == "POST":
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 == password2:
            reset_token.user.set_password(password1)
            reset_token.user.save()
            reset_token.delete()
            return redirect('login_page')
        else:
            return HttpResponse("Passwords do not match.")
    
    return render(request, 'user/new_password.html', {'token': token})

def change_password(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if request.method == "POST":
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 == password2:
            user = request.user
            user.set_password(password1)
            user.save()
            return redirect('login_page')
        else:
            return HttpResponse("Passwords do not match.")
    
    return render(request, 'user/change_password.html', {'user_profile': user_profile})

    
def index(request):
    keyword = request.GET.get('keyword', '')
    courses = StaffCourse.objects.filter(lock=1, active=1, approval=1)

    if keyword:
        courses = courses.filter(name__icontains=keyword)  # Adjust field name as necessary

    context = {'courses': courses}
    return render(request, 'user/index.html', context)

def baseindex(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    student_id = request.user.id 
    # Query for course types and active courses
    course_types = StaffCourse.objects.values('type').annotate(count=Count('type')).distinct()
    courses = StaffCourse.objects.filter(active=True, status='0', lock=True)
    
    # Fetch the user profile
    user_profile = UserProfile.objects.get(user=request.user)
    # Query to find the most enrolled course
    most_enrolled_courses = (
        Enrollment.objects.values('course')
        .annotate(enrollment_count=Count('id'))
        .order_by('-enrollment_count')[:5]
    )

    # Fetch the corresponding course objects
    top_5_courses_objs = []
    for course in most_enrolled_courses:
        course_id = course['course']
        most_enrolled_course_obj = StaffCourse.objects.get(id=course_id)
        top_5_courses_objs.append(most_enrolled_course_obj)
    # # Get recommendations
    # recommended_courses = get_recommended_courses(request.user.id)
    # Render the response
    today = timezone.now().date()
    
    # Fetch upcoming programs
    upcoming_programs = DevelopmentProgram.objects.filter(
    start_date__gte=today,
    is_active=True,
    status_program='approved'
).order_by('start_date')[:4]

# Get total count of upcoming programs
    total_upcoming = DevelopmentProgram.objects.filter(
    start_date__gte=today,
    is_active=True,
    status_program='approved'
    ).count()

# Check for new programs (added in the last 7 days)
    seven_days_ago = today - timedelta(days=7)
    new_programs = DevelopmentProgram.objects.filter(
    created_at__gte=seven_days_ago,
    start_date__gte=today,
    is_active=True,
    status_program='approved'
    )
    new_programs_count = new_programs.count()

# Get the next upcoming program
    next_program = DevelopmentProgram.objects.filter(
    start_date__gte=today,
    is_active=True,
    status_program='approved'
    ).order_by('start_date').first()
    return render(request, 'user/baseindex.html', {
         'upcoming_programs': upcoming_programs,
        'total_upcoming': total_upcoming,
        'new_programs': new_programs.exists(),
        'new_programs_count': new_programs_count,
        'next_program': next_program,
        'today': today,
        'user_profile': user_profile,
        'course_types': course_types,
        'courses': courses,
        'top_5_courses': top_5_courses_objs,
        # 'recommended_courses': recommended_courses,
    })
    # Pass all the context to the template
   
    
def staff_index(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    return render(request,'instructor/instructorindex.html')


def landing(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = StaffProfile.objects.get(user=request.user)
    course_count = StaffCourse.objects.filter(instructor_id=user_profile.id, active=True, lock=True).count()
    enrollment_count = Enrollment.objects.filter(course__instructor=user_profile).count()
    rejected_count = StaffCourse.objects.filter(instructor_id=user_profile.id, status='1').count()
    return render(request,'instructor/landing.html',{'course_count':course_count,'enrollment_count':enrollment_count,'rejected_count':rejected_count})

def password_reset(request):
    return render(request,'user/password_reset.html')

@never_cache
def studentindex(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = UserProfile.objects.get(user=request.user)
    return render(request, 'user/studentindex.html', {'user_profile': user_profile})
    
def adminindex(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    return render(request,'admin/adminindex.html')

@never_cache
def main_page(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    
    # Get existing counts
    active_profiles_count = UserProfile.objects.filter(active=True).count()
    active_enrollments_count = Enrollment.objects.filter(status=1).count()
    active_locked_courses_count = StaffCourse.objects.filter(lock=1, active=1).count()
    attempts_count = Enrollment.objects.filter(attempts=True).count()
    not_enrolled_count = Enrollment.objects.filter(attempts=False).count()

    # Get all active development programs
    development_programs = DevelopmentProgram.objects.filter(
        is_active=True
    ).order_by('start_date')

    # Add print statement for debugging
    print(f"Number of programs found: {development_programs.count()}")
    for program in development_programs:
        print(f"Program: {program.title}, Start Date: {program.start_date}")
    

    context = {
        'active_profiles_count': active_profiles_count,
        'active_enrollments_count': active_enrollments_count,
        'active_locked_courses_count': active_locked_courses_count,
        'attempts_count': attempts_count,
        'not_enrolled_count': not_enrolled_count,
        'development_programs': development_programs,
        'pending_programs': DevelopmentProgram.objects.filter(status_program='pending', is_active=True).order_by('created_at'),
  # Make sure this is in the context
    }

    return render(request, 'admin/main_page.html', context)

@never_cache
def user_details(request,user_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profile = get_object_or_404(UserProfile.objects.select_related('user'), user_id=user_id)
    return render(request, 'admin/user_details.html', {'profile': profile})

def new_password(request):
    return render(request,'user/new_password.html')

def user_profile(request):
    return render(request,'user/user_profile.html')


def password_done(request):
    return render(request,'user/password_done.html')

def edit_profile_success(request):
    return render(request,'user/user_profile.html')

def userlogout(request):
    logout(request)  # This logs out the user
    request.session.flush()  # This clears the session, including 'logged_user'
    return redirect('index')

def user_profile(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if request.method == 'POST':
        user = request.session['logged_user']
        # Retrieve data from the form
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        bio = request.POST.get('bio')
        country = request.POST.get('country')
        profile_picture = request.FILES.get('profile_picture')

        # Check if the profile exists
        if not UserProfile.objects.filter(user=user).exists():
            # Create a new profile if it does not exist
            profile = UserProfile.objects.create(
                user_id=user, # Directly assign the user object
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                bio=bio,
                country=country,
                profile_picture=profile_picture
            )
            if profile:
                return redirect('baseindex')
        else:
            # Retrieve the existing profile and update fields
            profile = UserProfile.objects.get(user=user)
            profile.first_name = first_name
            profile.last_name = last_name
            profile.phone_number = phone_number
            profile.bio = bio
            profile.country = country
            
            if profile_picture:
                profile.profile_picture = profile_picture
            
            # Save the updated profile
            profile.save()
        return redirect('baseindex')
    return render(request, 'user/user_profile.html')


@never_cache
def profile_view(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')# Assuming 'index' is the name of your index page URL pattern
    user_profile = UserProfile.objects.get(user=request.user)
    return render(request, 'user/profile_view.html', {'user_profile': user_profile})

@never_cache
def delete_profile_picture(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile =UserProfile.objects.get(user=request.user)
    user_profile.profile_picture.delete()
    user_profile.save()
    return JsonResponse({'status': 'success'})

@never_cache
def replace_profile_picture(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if 'profile_picture' in request.FILES:
        user_profile =UserProfile.objects.get(user=request.user)
        user_profile.profile_picture = request.FILES['profile_picture']
        user_profile.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@never_cache
def edit_profile(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        first_name = request.POST.get('firstName')
        last_name = request.POST.get('lastName')
        phone_number=request.POST.get('phone_number')
        bio = request.POST.get('bio')
        
        user_profile.first_name = first_name
        user_profile.phone_number=phone_number
        user_profile.last_name = last_name
        user_profile.bio = bio
        user_profile.save()
        
        return redirect('profile_view') 
    
    return render(request, 'user/edit_profile.html', {'user_profile': user_profile})

@never_cache
def add_employee(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    dept = Department.objects.filter(active=True)
    return render(request, 'admin/add_employee.html', {'dept': dept})

@never_cache
def staff_registration(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    dept = Department.objects.all()
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')  # You might want to hash passwords in a real application
        first_name = request.POST.get('fname')
        last_name = request.POST.get('lname')
        address = request.POST.get('address')
        city = request.POST.get('Locality')
        state = request.POST.get('State')
        department=request.POST.get('dept')
        country_code = request.POST.get('country_code')
        zip_code = request.POST.get('Zip')
        dob = request.POST.get('dob')
        phone = request.POST.get('phone')

        data = CustomUser.objects.create_user(username=first_name, email=email, password=password, role='instructor',is_superuser=True)
        if data:
            profile = StaffProfile.objects.create(user=data, first_name=first_name, last_name=last_name, address=address, city=city, state=state, country_code=country_code, zip=zip_code, dob=dob, phone=phone,department=department)
            if profile:
                welcome_mail(request, data, password)
                return redirect('adminindex') 
            else:
                return redirect('add_employee') 
        else:
            return redirect('add_employee')
    return render(request, 'admin/add_employee.html',{'dept': dept})
        
@never_cache
def employee_details(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profiles = StaffProfile.objects.select_related('user').filter(active=True)
    return render(request,'admin/employee_details.html',{'profiles': profiles})

def welcome_mail(request, user, password):
    subject = 'Welcome to Next-Edge Team !'
    context = {
        'user': user,
        'password': password,
    }
    html_content = render_to_string('admin/welcome_mail.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email]
    )
    
    email.attach_alternative(html_content, 'text/html')
    email.send()
    
    
def validate_current_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        user = request.user
        user = authenticate(username=user.username, password=current_password)
        if user is not None:
            return JsonResponse({'valid': True})
        else:
            return JsonResponse({'valid': False})

@never_cache
def update_password(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = StaffProfile.objects.get(user=request.user)
    if request.method == "POST":
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 == password2:
            user = request.user
            user.set_password(password1)
            user.save()
            messages.success(request, 'Password updated successfully!')
            return redirect('login_page')
        else:
            messages.error(request, 'Passwords do not match.')
    
    return render(request, 'instructor/update_password.html', {'user_profile': user_profile})

@never_cache
def staff_profile(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = StaffProfile.objects.get(user=request.user)
    return render(request, 'instructor/staff_profile.html', {'profile': user_profile})

def update_staff_profile(request):
    if not request.user.is_authenticated:
        return redirect('index')
    if 'logged_user' not in request.session:
        return redirect('login_page')

    # Get the current user's profile
    user_profile = get_object_or_404(StaffProfile, user=request.user)

    if request.method == 'POST':
        # Extract form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone = request.POST.get('phone')
        house_name = request.POST.get('house_name')
        city = request.POST.get('city')
        state = request.POST.get('state')
        zip_code = request.POST.get('zip')

        # Assigning values to the user profile
        user_profile.first_name = first_name
        user_profile.last_name = last_name
        user_profile.phone = phone
        user_profile.address = house_name  # Assuming house_name is stored in address field
        user_profile.city = city
        user_profile.state = state
        user_profile.zip = zip_code

        # Save the updated profile
        user_profile.save()
        return redirect('staff_profile')  # Make sure 'edit_staff_profile' is the correct URL name

    # If GET request, render the edit profile form
    return render(request, 'instructor/edit_staff_profile.html', {'profile': user_profile})
    

@never_cache
def edit_staff_profile(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = StaffProfile.objects.get(user=request.user)
    return render(request, 'instructor/edit_staff_profile.html', {'profile': user_profile})

@never_cache
def view_employee_profile(request,user_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profile = get_object_or_404(StaffProfile.objects.select_related('user'), user_id=user_id)
    return render(request, 'admin/view_employee_profile.html', {'profile': profile})

@never_cache
def deactivate_employee(request, user_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profile = get_object_or_404(StaffProfile, user_id=user_id)
    profile.active = False
    profile.save()
    return render(request, 'admin/employee_details.html')

@never_cache
def activate_employee(request, user_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profile = get_object_or_404(StaffProfile, user_id=user_id)
    profile.active = True
    profile.save()
    return render(request, 'admin/employee_details.html')

@never_cache
def deactivated_employee(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profiles = StaffProfile.objects.select_related('user').filter(active=False)
    return render(request,'admin/deactivated_employee.html',{'profiles': profiles})

@never_cache
def active_users(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profiles = UserProfile.objects.select_related('user').filter(active=True)
    return render(request, 'admin/active_users.html', {'profiles': profiles})

@never_cache
def deactivate_user(request, user_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profile = get_object_or_404(UserProfile, user_id=user_id)
    profile.active = False
    profile.save()
    return render(request, 'admin/active_users.html')

@never_cache
def activate_user(request, user_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profile = get_object_or_404(UserProfile, user_id=user_id)
    profile.active = True
    profile.save()
    return render(request, 'admin/active_users.html')

@never_cache
def deactivated_user(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profiles = UserProfile.objects.select_related('user').filter(active=False)
    return render(request,'admin/deactivated_user.html',{'profiles': profiles})

@never_cache
def view_user_profile(request,user_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    profile = get_object_or_404(UserProfile.objects.select_related('user'), user_id=user_id)
    return render(request, 'admin/view_user_profile.html', {'profile': profile})

@never_cache
def view_mycourses(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    
    user_profile = StaffProfile.objects.get(user=request.user)
    department_name = user_profile.department
    department_id = int(department_name)  # Convert to integer if necessary
    department = Department.objects.filter(id=department_id).first()
    course_types = Subdept.objects.filter(active=True,dept_id=department_id)
    return render(request, 'instructor/view_mycourses.html', {'course_types': course_types,'department':department})

@never_cache
def add_course(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = StaffProfile.objects.get(user=request.user)
    department_name = user_profile.department
    department_id = int(department_name)  # Convert to integer if necessary
    department = Department.objects.filter(id=department_id).first()

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        payment = request.POST.get('payment')
        mode = request.POST.get('mode')
        content = request.FILES.get('content')
        course_type = request.POST.get('course_type')
        new_course_type = request.POST.get('new_course_type')
        price=request.POST.get('price')
        
        if course_type == 'Other' and new_course_type:
            course_type=new_course_type
            Subdept.objects.create(subdept=new_course_type, dept=department)
        if payment == 'paid':
            price_value = int(price)
        elif payment == 'free':
            price_value = 0
            
        if name and description and mode and payment:
            user_profile = StaffProfile.objects.get(user=request.user)  # Get the StaffProfile instance
            course = StaffCourse.objects.create(
                name=name,
                description=description,
                payment=payment,
                mode=mode,
                content=content,
                type=course_type,
                instructor=user_profile,status='0',amount=price_value
                # Use the StaffProfile instance
            )
            if course:
                return redirect('my_courses')
    return render(request, 'instructor/add_course.html')

@never_cache
def add_module(request, course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    

    if request.method == 'POST':
        module_name = request.POST.get('name')
        
        if module_name:
            Module.objects.create(name=module_name, course=course)
            return redirect('add_module', course_id=course_id)
    modules = Module.objects.filter(course=course).prefetch_related('module')
    return render(request, 'instructor/add_module.html', {'course': course, 'modules': modules})

@never_cache
def add_topic(request, module_id, course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    module = get_object_or_404(Module, id=module_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        content = request.FILES.get('content')
        
        if name and description and content:
            topic = Topic.objects.create(name=name, description=description, content=content, module_id=module_id)
            return redirect('add_module', course_id=course.id)  # Adjust this line as necessary
    
    return render(request, 'instructor/add_topic.html', {'module': module, 'course': course})


@never_cache
def delete_topic(request,topic_id,course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    modules = Module.objects.filter(course=course).prefetch_related('module')
    topic = get_object_or_404(Topic, id=topic_id)
    topic.delete()
    return render(request, 'instructor/add_module.html', {'course': course, 'modules': modules})

@never_cache
def delete_module(request,module_id,course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    module = get_object_or_404(Module, id=module_id)
    Topic.objects.filter(module=module).delete()
    module.delete()
    modules = Module.objects.filter(course=course)
    return render(request, 'instructor/add_module.html', {'course': course, 'modules': modules})


    

@never_cache
def my_courses(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile =StaffProfile.objects.get(user=request.user)
    courses = StaffCourse.objects.filter(instructor_id=user_profile.id)
    return render(request,'instructor/my_courses.html',{'courses': courses})

@never_cache
def edit_course(request,course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        mode = request.POST.get('mode')
        payment = request.POST.get('payment')
        
        course.name = name
        course.description = description
        course.mode = mode
        course.payment = payment
        
        if 'image' in request.FILES:
            course.image = request.FILES['course-image']
        course.save() 
        
        return redirect('my_courses')  
    return render(request,'instructor/my_courses.html')

@never_cache
def course_approval(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile =StaffProfile.objects.get(user=request.user)
    department_name = user_profile.department
    department_id = int(department_name)  # Convert to integer if necessary
    department = Department.objects.filter(id=department_id).first()
    courses = StaffCourse.objects.filter(instructor_id=user_profile.id,approval=False)
    return render(request,'instructor/course_approval.html',{'courses': courses,'department':department})

@never_cache
def request_course(request,course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    courses = StaffCourse.objects.filter(active=False)
    course.approval = True
    course.save()
    return redirect('course_approval') 


def approval_history(request):
    courses = StaffCourse.objects.filter(approval='1') 
    courses_with_instructors = []

    for course in courses:
        staff_profile = course.instructor  # Fetching the StaffProfile instance
        instructor = staff_profile.user    # Fetching the associated CustomUser instance
        
        courses_with_instructors.append({
            'course': course,
            'instructor': instructor
        })
    return render(request, 'admin/approval_history.html',{'courses_with_instructors': courses_with_instructors})

#list of course that need to be approved
@never_cache
def request_approval_view(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    courses = StaffCourse.objects.filter(active=False, status='0',approval=1)
    courses_with_instructors = []

    for course in courses:
        staff_profile = course.instructor  # Fetching the StaffProfile instance
        instructor = staff_profile.user    # Fetching the associated CustomUser instance
        
        courses_with_instructors.append({
            'course': course,
            'instructor': instructor
        })

    return render(request, 'admin/request_approval.html', {'courses_with_instructors': courses_with_instructors})

#instructor show details of the course
@never_cache
def course_details(request, course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    instructor = course.instructor  # Assuming `instructor` is a ForeignKey in StaffCourse
    modules = Module.objects.filter(course=course)  # Assuming `Module` model has a ForeignKey to `StaffCourse`
    topics = Topic.objects.filter(module__in=modules)  # Assuming `Topic` model has a ForeignKey to `Module`

    context = {
        'course': course,
        'instructor': instructor,
        'modules': modules,
        'topics': topics
    }
    return render(request, 'instructor/course_details.html', context)

def course_details_view_admin(request, course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    instructor = course.instructor  # Assuming `instructor` is a ForeignKey in StaffCourse
    modules = Module.objects.filter(course=course)  # Assuming `Module` model has a ForeignKey to `StaffCourse`
    topics = Topic.objects.filter(module__in=modules)  # Assuming `Topic` model has a ForeignKey to `Module`
    quiz=Quiz.objects.filter(course=course.id)# Assuming `Topic` model has a ForeignKey to `Module`

    context = {
        'course': course,
        'instructor': instructor,
        'modules': modules,
        'topics': topics,
        'quiz':quiz,
    }
    return render(request, 'admin/course_details_view_admin.html', context)


@never_cache
def approve_course(request, course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    course.active = True
    course.lock=True
    course.save()
    courses = StaffCourse.objects.filter(active=False)
    courses_with_instructors = []

    for course in courses:
        staff_profile = course.instructor  # Fetching the StaffProfile instance
        instructor = staff_profile.user    # Fetching the associated CustomUser instance
        
        courses_with_instructors.append({
            'course': course,
            'instructor': instructor
        })
    return redirect('request_approval_view')
    
    return render(request, 'admin/request_approval.html', {'courses_with_instructors': courses_with_instructors})


@never_cache
def reject_course(request, course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    course.status ="1"
    course.save()
    courses = StaffCourse.objects.filter(active=False)
    courses_with_instructors = []

    for course in courses:
        staff_profile = course.instructor  # Fetching the StaffProfile instance
        instructor = staff_profile.user    # Fetching the associated CustomUser instance
        
        courses_with_instructors.append({
            'course': course,
            'instructor': instructor
        })
        return redirect('request_approval_view')

    return render(request, 'admin/request_approval.html', {'courses_with_instructors': courses_with_instructors})

@never_cache
def view_course_details(request, course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    instructor = course.instructor  # Assuming `instructor` is a ForeignKey in StaffCourse
    modules = Module.objects.filter(course=course)  # Assuming `Module` model has a ForeignKey to `StaffCourse`
    topics = Topic.objects.filter(module__in=modules)  # Assuming `Topic` model has a ForeignKey to `Module`
    quiz=Quiz.objects.filter(course=course)

    context = {
        'course': course,
        'instructor': instructor,
        'modules': modules,
        'topics': topics,
        'quiz':quiz
    }
    return render(request, 'admin/view_course_details.html', context)

@never_cache
def courses(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = UserProfile.objects.get(user=request.user)
    courses = StaffCourse.objects.filter(active=True, status='0', lock=True)
    modules = Module.objects.filter(course__in=courses) 
    topics = Topic.objects.filter(module__in=modules)  
    context = {
        'courses': courses,  # Changed 'course' to 'courses'
        'modules': modules,
        'topics': topics,
        'user_profile':user_profile
    }
    return render(request, 'user/courses.html', context)

@never_cache
def course_details_view(request, course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = UserProfile.objects.get(user=request.user)
    course = get_object_or_404(StaffCourse, id=course_id)
    student = request.user
    modules = Module.objects.filter(course=course)  # Assuming `Module` model has a ForeignKey to `StaffCourse`
    topics = Topic.objects.filter(module__in=modules)  # Assuming `Topic` model has a ForeignKey to `Module`
    quiz=Quiz.objects.filter(course=course)
    enrollment = Enrollment.objects.filter(student=student.id, course=course, status=True).first()
    
    certificate_instance = None

    # Check if enrollment exists
    if enrollment:
        # Check if a Certificate entry exists for this enrollment
        if Certificate.objects.filter(enrolled_id=enrollment.id).exists():
            # Fetch the certificate instance
            certificate_instance = Certificate.objects.get(enrolled_id=enrollment.id)
    
    total_videos = topics.count()

    # Calculate watched videos based on Progress
    watched_videos = Progress.objects.filter(student=enrollment, video__in=topics, watched=True).count()

    # Calculate progress percentage
    progress = (watched_videos / total_videos * 100) if total_videos > 0 else 0
    
    # Get list of watched video IDs
    watched_videos_ids = Progress.objects.filter(
        student=enrollment, 
        video__in=topics, 
        watched=True
    ).values_list('video_id', flat=True)
    
    context = {
        'course': course,
        'modules': modules,
        'topics': topics,
        'quiz': quiz,
        'enrollment': enrollment,
        'total_videos': total_videos,
        'watched_videos': watched_videos,
        'progress': progress,
        'certificate_instance': certificate_instance,
        'user_profile': user_profile,
        'watched_videos_ids': watched_videos_ids,  # Add this to context
    }
    return render(request, 'user/course_details_view.html', context)

def course_details_view_staff(request, course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')

    course = get_object_or_404(StaffCourse, id=course_id)

    # Retrieve the instructor's staff profile
    instructor_profile = course.instructor

    # Get the department name or ID as a string
    department_name = instructor_profile.department
    department_id = int(department_name)  # Convert to integer if necessary
    department = Department.objects.filter(id=department_id).first()
    modules = Module.objects.filter(course=course)
    topics = Topic.objects.filter(module__in=modules)
    quiz = Quiz.objects.filter(course=course)

    if department is None or not department.active:
        context = {
            'message': "The Main Course is Unavailable and no action can be performed on this.",
            'course': course,
            'modules': modules,
            'topics': topics,
            'quiz': quiz,
        }
        return render(request, 'instructor/each_course.html', context)

    # Continue with the rest of the logic...


    context = {
        'course': course,
        'modules': modules,
        'topics': topics,
        'quiz': quiz,
        'department': department,
    }

    return render(request, 'instructor/each_course.html', context)



@never_cache
def employee_course(request, instructor_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    instructor = get_object_or_404(StaffProfile, id=instructor_id)
    courses = StaffCourse.objects.filter(instructor=instructor,active=True)
    modules = Module.objects.filter(course__in=courses)
    topics = Topic.objects.filter(module__in=modules)

    # Prepare context data
    course_modules = []
    for course in courses:
        course_data = {
            'course': course,
            'modules': [],
        }
        course_modules_obj = modules.filter(course=course)
        for module in course_modules_obj:
            module_data = {
                'module': module,
                'topics': topics.filter(module=module),
            }
            course_data['modules'].append(module_data)
        course_modules.append(course_data)

    context = {
        'instructor': instructor,
        'course_modules': course_modules,
    }
    return render(request, 'admin/employee_course.html', context)

@never_cache
def add_quiz(request,course_id):
    if not request.user.is_authenticated:
        return redirect('index')
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)

    if request.method == 'POST':
        question = request.POST.get('question')
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        correct_answer = request.POST.get('correct_answer')  # Corrected key

        # Create a new Quiz instance
        Quiz.objects.create(
            question=question,
            option1=option1,
            option2=option2,
            option3=option3,
            correct_answer=correct_answer,
            course_id=course.id
        )
    
    # Fetch quiz data
    quiz = Quiz.objects.filter(course_id=course)
    
    return render(request, 'instructor/add_quiz.html', {'quiz': quiz,'course': course})


@never_cache
def edit_question(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        question_text = request.POST.get('question')
        option1 = request.POST.get('option1')
        option2 = request.POST.get('option2')
        option3 = request.POST.get('option3')
        correct_answer = request.POST.get('correct_answer')
        
        try:
            question = get_object_or_404(Quiz, id=question_id)
            question.question = question_text
            question.option1 = option1
            question.option2 = option2
            question.option3 = option3
            question.correct_answer = correct_answer
            question.save()
            response = {'status': 'success', 'message': 'Question updated successfully!'}
        except Exception as e:
            response = {'status': 'error', 'message': str(e)}
        
        return JsonResponse(response)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})
@never_cache 
def delete_quiz(request, course_id, question_id):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    try:
        course = get_object_or_404(StaffCourse, id=course_id)
        quiz = get_object_or_404(Quiz, id=question_id)
        quiz.delete()
        messages.success(request, 'Quiz deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error occurred: {e}')
    
    return redirect('add_quiz', course_id=course.id)
    
@never_cache
def each_course(request,course_id):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    return render(request, 'instructor/course_details_view_staff.html', {'course':course})

@never_cache
def upload_excel(request, course_id):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    success = False
    error_message = None
    
    if request.method == 'POST' and 'excel_data' in request.FILES:
        try:
            excel_file = request.FILES['excel_data']

            fs = FileSystemStorage()
            filename = fs.save(excel_file.name, excel_file)
            file_path = fs.path(filename)

            # Ensure the file has been saved
            if not os.path.exists(file_path):
                error_message = "The uploaded file could not be saved."
                raise ValueError(error_message)

            # Read the Excel file, skipping the first 3 rows
            df = pd.read_excel(file_path, header=3) 

            # Check if required columns are present
            required_columns = ['Question', 'Option1', 'Option2', 'Option3', 'Correct_answer']
            for col in required_columns:
                if col not in df.columns:
                    error_message = f'Missing required column: {col}'
                    raise ValueError(error_message)

            # Process the DataFrame
            for index, row in df.iterrows():
                Quiz.objects.create(
                    question=row['Question'],
                    option1=row['Option1'],
                    option2=row['Option2'],
                    option3=row['Option3'],
                    correct_answer=row['Correct_answer'].lower() if isinstance(row['Correct_answer'], str) else row['Correct_answer'],
                    course_id=course.id
                )
            
            success = True
        except Exception as e:
            error_message = str(e)
    
    quiz = Quiz.objects.filter(course_id=course.id)
    return render(request, 'instructor/add_quiz.html', {
        'quiz': quiz,
        'course': course,
        'success': success,
        'error_message': error_message
    })

@never_cache
def edit_topic(request,topic_id,course_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if request.method == 'POST':
        topic_id = request.POST.get('topic_id')
        topic = get_object_or_404(Topic, id=topic_id)
        course = get_object_or_404(StaffCourse, id=course_id)
        modules = Module.objects.filter(course=course).prefetch_related('module')
        topic.name = request.POST.get('name')
        topic.description = request.POST.get('description')
        topic.save()
        messages.success(request, 'Topic updated successfully!')
        return render(request, 'instructor/add_module.html', {'course': course, 'modules': modules})
    
@never_cache   
def enroll_course(request, course_id):
    if 'logged_user' not in request.session:
        return redirect('login_page')

    course = get_object_or_404(StaffCourse, id=course_id)
    student = get_object_or_404(CustomUser, id=request.user.id)

    # Create the enrollment
    enrollment, created = Enrollment.objects.get_or_create(
        course=course,
        student=student,
        defaults={'status': True}
    )
    # Fetch related data for rendering
    modules = Module.objects.filter(course=course)
    topics = Topic.objects.filter(module__in=modules)
    quiz = Quiz.objects.filter(course=course)
    enrollment = Enrollment.objects.filter(student=student.id, course=course, status=True).first()
    user_profile = UserProfile.objects.get(user=request.user)

    context = {
        'course': course,
        'modules': modules,
        'topics': topics,
        'quiz': quiz,
        'enrollment': enrollment,
        'user_profile': user_profile
    }

    # Show success message if enrollment was successful
    if enrollment:
        messages.success(request, 'Congratulations! Course Enrollment Successful')
        return redirect('course_details_view', course_id=course.id)

    return render(request, 'user/course_details_view.html', context)


@never_cache
def course_category(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    departments = Department.objects.filter(active=True)
    subdept = Subdept.objects.filter(active=True)
    deactivated=Department.objects.filter(active=False)
    return render(request,'admin/course_category.html', {'departments': departments,'subdept':subdept,'deactivated':deactivated})

@never_cache
def add_department(request):
    if not request.user.is_authenticated:
        return redirect('index')  # Redirect to index if the user is not authenticated
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if request.method == 'POST':
        department_name = request.POST.get('category')
        if department_name:
            Department.objects.create(department=department_name)
            messages.success(request, "Department added successfully!")  # Set success message
            return redirect('course_category')  # Redirect to course_category view after successful addition

    departments = Department.objects.filter(active=True)
    subdept = Subdept.objects.filter(active=True)
    return render(request,'admin/course_category.html', {'departments': departments,'subdept':subdept})

@never_cache
def edit_category(request):
    if not request.user.is_authenticated:
        return redirect('index')  # Redirect to index if the user is not authenticated
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if request.method == 'POST':
         category_id = request.POST.get('category_id')
         new_category_name = request.POST.get('category')
    if new_category_name:
            subdep = Department.objects.get(id=category_id)
            subdep.department = new_category_name
            subdep.save()  # Save the updated department name

            # Update the department in all related StaffProfiles
            staff_profiles = StaffProfile.objects.filter(department=subdep)
            for staff_pro in staff_profiles:
                staff_pro.department = subdep  # Assign the updated department object
                staff_pro.save()  # Save each StaffProfile

            messages.success(request, "Category updated successfully!")
            return redirect('course_category')

    departments = Department.objects.filter(active=True)
    subdept = Subdept.objects.filter(active=True)
    return render(request,'admin/course_category.html', {'departments': departments,'subdept':subdept})

@never_cache
def add_subdept(request):
    if not request.user.is_authenticated:
        return redirect('index')  # Redirect to index if the user is not authenticated
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if request.method == 'POST':
        subcategory_name = request.POST.get('subcategory')  # Get subcategory name
        department_name = request.POST.get('category')  # Get selected department name

        if subcategory_name and department_name:
                department = Department.objects.get(department=department_name)
                Subdept.objects.create(subdept=subcategory_name, dept=department)
                messages.success(request, "Sub Category added successfully!")
                return redirect('course_category') 
    departments = Department.objects.filter(active=True)
    subdept = Subdept.objects.filter(active=True)
    return render(request,'admin/course_category.html', {'departments': departments,'subdept':subdept})

@never_cache
def remove_category(request, category_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')# Redirect to index if the user is not authenticated
    try:
        # Get the department to be deactivated
        department = Department.objects.get(id=category_id)
        # Deactivate the department
        department.active = False
        department.save()
        # Deactivate related sub-departments
        subdepartments = Subdept.objects.filter(dept=department)
        for subdept in subdepartments:
            subdept.active = False
            subdept.save()
        staff_profiles = StaffProfile.objects.filter(department=department.id)
        if staff_profiles.exists():
            for staff_pro in staff_profiles:
                user_email = staff_pro.user.email  

        message = "Department related subdepartments and staffs deactivated successfully!" 
        messages.success(request, message)
        return redirect('course_category') 
    except Department.DoesNotExist:
        messages.error(request, "Department does not exist.")
    departments = Department.objects.filter(active=True)
    subdept = Subdept.objects.filter(active=True)
    return render(request,'admin/course_category.html', {'departments': departments,'subdept':subdept})


def active_category(request, category_id):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')# Redirect to index if the user is not authenticated
    try:
        # Get the department to be deactivated
        department = Department.objects.get(id=category_id)
        # Deactivate the department
        department.active = True
        department.save()
        # Deactivate related sub-departments
        subdepartments = Subdept.objects.filter(dept=department)
        for subdept in subdepartments:
            subdept.active = True
            subdept.save()
        staff_profiles = StaffProfile.objects.filter(department=department.id)
        if staff_profiles.exists():
            for staff_pro in staff_profiles:
                user_email = staff_pro.user.email  

        message = "Department related subdepartments and staffs Activated successfully!" 
        messages.success(request, message)
        return redirect('course_category') 
    except Department.DoesNotExist:
        messages.error(request, "Department does not exist.")
    departments = Department.objects.filter(active=True)
    subdept = Subdept.objects.filter(active=True)
    return render(request,'admin/course_category.html', {'departments': departments,'subdept':subdept})


@never_cache
def send_dept_remove_mail(request,user):
    subject = 'Course Module Temporarily Unavailable'
    context = {
        'user': user,
    }
    html_content = render_to_string('user/dept_remove.html', context)
    text_content = strip_tags(html_content)
    email = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [user.email])
    email.attach_alternative(html_content, 'text/html')
    email.send()

@never_cache
def update_video_progress(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if request.method == 'POST':
        video_id = request.POST.get('video_id')
        student_id = request.user.id  # Assuming user is authenticated and has an ID
        
        # Get the enrollment instance
        video = get_object_or_404(Topic, id=video_id)
        
        # Get the associated course_id by traversing relationships
        course_id = video.module.course.id

        # Now you have the course_id, you can use it as needed
        enrollment = get_object_or_404(Enrollment, student_id=student_id, course_id=course_id)
        existing_progress = Progress.objects.filter(student_id=enrollment.id, video_id=video.id).first()
            
        # Create a new Progress entry
        if not existing_progress:
            Progress.objects.create(
            student_id=enrollment.id,
            video_id=video.id,
            watched=True,
            active=True
            )

        # Optionally, redirect after processing
        return JsonResponse({
            'status': 'success',
            'video_url': video.content.url,  # Include the video URL
            'video_name': video.name,  # Include the video name if needed
            
        })

    return JsonResponse({'status': 'failed'}, status=400)

@never_cache
def quiz(request, course_id):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course = get_object_or_404(StaffCourse, id=course_id)
    quizzes = Quiz.objects.filter(course=course)  # Fetch quizzes for the course
    
    quiz_array = []
    for quiz in quizzes:
        quiz_array.append({
            'question': quiz.question,  # Correct field name
            'option1': quiz.option1,    # Correct field name
            'option2': quiz.option2,    # Correct field name
            'option3': quiz.option3,    # Correct field name
            'correct_answer': quiz.correct_answer  # Correct field name
        })
    
    return render(request, 'user/quiz.html', {
        'course': course,
        'quiz_array': quiz_array  # Pass the quiz array to the template
    })

@never_cache
def update_score(request, course_id):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if request.method == 'POST':
        latest_score = request.POST.get('latest_score')
        
        # Update or create an enrollment record
        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            course_id=course_id,
            defaults={'latest_score': latest_score}
        )
        
        if not created:  # If the enrollment already exists, update the score
            enrollment.latest_score = latest_score
            enrollment.attempts='1'
            enrollment.save()
        latest_score = int(latest_score)
        if latest_score >= 80:
            # Check if a certificate already exists for this enrollment
            certificate_exists = Certificate.objects.filter(enrolled_id=enrollment.id).exists()

            if not certificate_exists:
                # Create a certificate entry if it doesn't already exist
                Certificate.objects.create(
                    enrolled_id=enrollment.id,
                    status=True,  # Assuming `status=True` means the certificate is awarded
                    issued_at=timezone.now()  # Store the current date and time
                )

        return redirect('course_details_view', course_id=course_id)
    return redirect('baseindex')  # Redirect if the request method is not POST

@never_cache
def enrolled_courses_view(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    user_profile = UserProfile.objects.get(user=request.user)
    courses = Enrollment.objects.filter(student=request.user).select_related('course')
    return render(request, 'user/mycourses.html', {'courses': courses,'user_profile':user_profile})

@never_cache
def course_enrollment_details(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    instructor = request.user
    courses = StaffCourse.objects.filter(instructor__user=instructor)

    course_enrollments = []

    for course in courses:
        # Get students enrolled in the course
        enrollments = Enrollment.objects.filter(course=course).select_related('student')
       
        for enrollment in enrollments:
            # Print the values to the console for debugging
            print(f"Email: {enrollment.student.email}, Attempts: {enrollment.attempts}, Latest Score: {enrollment.latest_score}")
            
            course_enrollments.append({
                'student_email': enrollment.student.email,
                'course_name': course.name,
                'attempts': enrollment.attempts,  # Add attempts to context
                'latest_score': enrollment.latest_score,  # Add latest score to context
            })

    context = {
        'course_enrollments': course_enrollments,
    }
    
    return render(request, 'instructor/enrolled_student.html', context)


def recommendation_view(request):
    # Load and prepare the data
    enrollments_df = load_data()
    encoded_df, le_courses, le_students = encode_data(enrollments_df)
    user_course_matrix = create_user_course_matrix(encoded_df)

    # Train the SVD model
    svd_model, user_factors, course_factors = train_svd_model(user_course_matrix)

    # Generate recommendations for a specific student
    student_index = request.user.id  # You can make this dynamic based on user input
    user_vector = user_factors[student_index]
    recommended_courses = generate_recommendations(user_vector, course_factors, le_courses)

    return render(request, 'user/baseindex.html', {'recommended_courses': recommended_courses})

@never_cache
def payment(request, course_id):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course=get_object_or_404(StaffCourse,id=course_id)
    price = course.amount
    amount = price # Razorpay expects the amount in paise
    return render(request, 'user/payment.html', {'amount': amount, 'course_id': course_id}) 

def check_course_name(request):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    course_name = request.GET.get('name', None).strip()  # Strip leading/trailing spaces
    exact_match = False
    similar_match = False

    # Check for exact match (case-insensitive)
    if StaffCourse.objects.filter(name__iexact=course_name).exists():
        exact_match = True
    else:
        # Check for similar names by comparing word similarity (ignoring case)
        courses = StaffCourse.objects.all()
        for course in courses:
            similarity_ratio = SequenceMatcher(None, course_name.lower(), course.name.lower()).ratio()
            if similarity_ratio > 0.8:  # Threshold for similarity (adjust as needed)
                similar_match = True
                break

    data = {
        'exists_exact': exact_match,
        'exists_similar': similar_match
    }
    return JsonResponse(data)


def check_module_name(request, course_id):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    if request.method == "GET":
        module_name = request.GET.get('name')
        existing_module = Module.objects.filter(name=module_name, course_id=course_id).exists()
        return JsonResponse({'exists': existing_module})


def check_topic_name(request, course_id):
    if 'logged_user' not in request.session:
        return redirect('login_page')
    topic_name = request.GET.get('name')
    
    # Query to check if the topic name exists in any module of the course
    exists = Topic.objects.filter(module__course_id=course_id, name__iexact=topic_name).exists()
    
    return JsonResponse({'exists': exists})


def save_payment(request):
    if 'logged_user' not in request.session:
        return JsonResponse({"status": "error", "message": "User not logged in."})

    if request.method == "POST":
        payment_id = request.POST.get('payment_id')
        amount = request.POST.get('amount')
        course_id = request.POST.get('course_id')

        if not payment_id or not amount or not course_id:
            return JsonResponse({"status": "error", "message": "Missing payment details."})

        try:
            payment_record = Payment.objects.create(
                user=request.user,
                course_id=course_id,
                amount=amount,
                status='success',  # Assuming payment was successful
                payment_id=payment_id,
                created_at=timezone.now()
            )
            
            return JsonResponse({"status": "success", "message": "Payment saved."})

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error saving payment: {str(e)}"})

    return JsonResponse({"status": "error", "message": "Invalid request"})

from django.utils import timezone

def certificate(request, course_id):
    course = get_object_or_404(StaffCourse, id=course_id)
    user = request.user
    student = UserProfile.objects.filter(user_id=user.id).first()
    
    # Find the relevant enrollment
    enrollment = Enrollment.objects.filter(student_id=user.id, course_id=course_id).first()
    
    # Extract date from Certificate model, or use the current date if no certificate exists yet
    certificate_record = Certificate.objects.filter(enrolled_id=enrollment.id).first()
    
    # Use current date if no certificate exists yet or fallback to the stored certificate date
    if certificate_record:
        date = certificate_record.issued_at.strftime('%Y-%m-%d')
    else:
        date = timezone.now().strftime('%Y-%m-%d')
    user_profile = UserProfile.objects.get(user=request.user)

    # Pass the date to the template
    context = {
        'course': course,
        'student': student,
        'date': date,
        'user_profile':user_profile
    }

    return render(request, 'user/certificate.html', context)

def acheivments(request):
    user_id = request.user.id
    # Get the user's profile (optional, in case you need profile data)
    student_profile = UserProfile.objects.filter(user_id=user_id).first()  # Fetch the first profile
    # Get courses the student is enrolled in
    courses = Enrollment.objects.filter(student=request.user.id).select_related('course')

    # Get certificates for the logged-in user
    certificates = Certificate.objects.filter(enrolled__student=request.user)
    user_profile = UserProfile.objects.get(user=request.user)
    return render(request, 'user/acheivments.html', {
        'student_profile': student_profile,
        'courses': courses,
        'certificates': certificates,
        'user_profile':user_profile
    })
    
    
    
def admin_payment_list(request):
    payments = Payment.objects.select_related('user', 'course').all()
    return render(request, 'admin/payment_list.html', {'payments': payments})

def enrollment_analysis(request):
    # Get total enrollments by course
    enrollment_data = StaffCourse.objects.filter(active=True, lock=True).annotate(total_enrollments=Count('enrolled_course')).values('name', 'total_enrollments')

    # Prepare data for the frontend
    courses = [data['name'] for data in enrollment_data]  # List of course names
    enrollment_counts = [data['total_enrollments'] for data in enrollment_data]  # Total enrollments per course

    # Ensure the data is being sent correctly
    context = {
        'courses': courses,
        'course_enrollments': enrollment_counts,  # Fix the context key to match the template
    }

    return render(request, 'admin/enrollment_analysis.html', context)

def toggle_course_status(request, course_id):
    try:
        course = StaffCourse.objects.get(id=course_id)
        
        # Check if there are any students enrolled in this course
        enrollments = Enrollment.objects.filter(course=course)
        
        if course.active and enrollments.exists():
            # Prevent deactivation if there are students enrolled
            return JsonResponse({
                'success': False,
                'error': 'This course cannot be deactivated because students are enrolled.'
            })
        
        # Toggle the active status
        course.active = not course.active
        course.save()

        # Successful response
        return JsonResponse({
            'success': True,
            'is_active': course.active,
            'message': 'Course has been {} successfully.'.format('activated' if course.active else 'deactivated')
        })
    
    except StaffCourse.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Course not found'
        })
        
        
def course_list(request):
    if not request.user.is_authenticated:
        return redirect('index') 
    if 'logged_user' not in request.session:
        return redirect('login_page')
    courses = StaffCourse.objects.filter(active=True, status='0', lock=True)
    modules = Module.objects.filter(course__in=courses) 
    topics = Topic.objects.filter(module__in=modules)  
    context = {
        'courses': courses,  # Changed 'course' to 'courses'
        'modules': modules,
        'topics': topics,
    }
    return render(request, 'admin/course_list.html', context)


def delete_course(request, course_id):
    course = get_object_or_404(StaffCourse, id=course_id)
    
    # Delete related modules, topics, and quizzes
    modules = Module.objects.filter(course=course)
    topics = Topic.objects.filter(module__in=modules)
    quizzes = Quiz.objects.filter(course=course)

    # Delete related objects in the correct order
    quizzes.delete()  # Delete quizzes related to the course
    topics.delete()   # Delete topics under the course's modules
    modules.delete()  # Delete modules under the course

    # Finally, delete the course itself
    course.delete()
    messages.success(request, 'Course and its related contents have been deleted successfully.')


    # Redirect to 'my_course' page (change to your actual URL name if different)
    return redirect('my_courses')


@never_cache
def create_program(request):
    if not request.user.is_authenticated:
        return redirect('index')
    if 'logged_user' not in request.session:
        return redirect('login_page')

    if request.method == 'POST':
        try:
            # Get the expert instance for the logged-in user
            expert = Expert.objects.get(id=request.session.get('expert_id'))
            
            program = DevelopmentProgram(
                expert=expert,  # Set the expert relationship
                title=request.POST.get('title'),
                category=request.POST.get('category'),
                other_category=request.POST.get('other_category'),
                speaker_name=request.POST.get('speaker_name'),
                speaker_designation=request.POST.get('speaker_designation'),
                other_designation=request.POST.get('other_designation'),
                speaker_organization=request.POST.get('speaker_organization'),
                speaker_profile=request.POST.get('speaker_profile'),
                speaker_image=request.FILES.get('speaker_image'),\
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                session_time=request.POST.get('session_time'),
                duration=request.POST.get('duration'),
                meeting_platform=request.POST.get('meeting_platform'),
                other_platform=request.POST.get('other_platform'),
                meeting_link=request.POST.get('meeting_link'),
                description=request.POST.get('description'),
                learning_outcomes=request.POST.get('learning_outcomes'),
                prerequisites=request.POST.get('prerequisites'),
                max_participants=request.POST.get('max_participants')
            )
            program.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Program created successfully!',
                'redirect_url': reverse('expert_dashboard')  # Add redirect URL
            })
        except Expert.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Expert profile not found.'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return render(request, 'admin/create_program.html')

@never_cache
def program_list(request):
    if not request.user.is_authenticated:
        return redirect('index')
    if 'logged_user' not in request.session:
        return redirect('login_page')

    programs = DevelopmentProgram.objects.filter(is_active=True).order_by('start_date')
    return render(request, 'admin/program_list.html', {'programs': programs})

@never_cache
def delete_program(request, program_id):
    if not request.user.is_authenticated:
        return redirect('index')
    if 'logged_user' not in request.session:
        return redirect('login_page')

    try:
        program = DevelopmentProgram.objects.get(id=program_id)
        program.is_active = False
        program.save()
        messages.success(request, 'Program deleted successfully!')
    except DevelopmentProgram.DoesNotExist:
        messages.error(request, 'Program not found!')
    
    return redirect('program_list')

@never_cache
def edit_program(request, program_id):
    try:
        program = DevelopmentProgram.objects.get(id=program_id)
        expert = Expert.objects.get(id=request.session.get('expert_id'))
        
        # Check if the expert is authorized to edit this program
        if program.expert.id != expert.id:
            return JsonResponse({
                'status': 'error',
                'message': 'You are not authorized to edit this program'
            })
        
        if request.method == 'POST':
            # Update program details
            program.title = request.POST.get('title')
            program.category = request.POST.get('category')
            program.other_category = request.POST.get('other_category')
            program.speaker_name = request.POST.get('speaker_name')
            program.speaker_designation = request.POST.get('speaker_designation')
            program.other_designation = request.POST.get('other_designation')
            program.speaker_organization = request.POST.get('speaker_organization')
            program.speaker_profile = request.POST.get('speaker_profile')
            
            # Handle speaker image
            if 'speaker_image' in request.FILES:
                program.speaker_image = request.FILES['speaker_image']
            
            
            # Update schedule
            program.start_date = request.POST.get('start_date')
            program.end_date = request.POST.get('end_date')
            program.session_time = request.POST.get('session_time')
            program.duration = request.POST.get('duration')
            
            # Update platform details
            program.meeting_platform = request.POST.get('meeting_platform')
            program.other_platform = request.POST.get('other_platform')
            program.meeting_link = request.POST.get('meeting_link')
            
            # Update additional details
            program.learning_outcomes = request.POST.get('learning_outcomes')
            program.prerequisites = request.POST.get('prerequisites')
            program.max_participants = request.POST.get('max_participants')
            
            # If program was rejected and is being resubmitted
            if program.status_program == 'rejected':
                program.status_program = 'pending'
                program.rejection_reason = None
            
            program.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Program updated successfully!',
                'redirect_url': reverse('expert_dashboard')
            })
            
        context = {
            'program': program,
            'is_approved': program.status_program == 'approved',
            'is_pending': program.status_program == 'pending',
            'is_rejected': program.status_program == 'rejected',
            'rejection_reason': program.rejection_reason
        }
        return render(request, 'expert/edit_program.html', context)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

# Admin views for program approval
@login_required
def admin_program_approval(request):
    pending_programs = DevelopmentProgram.objects.filter(status_program='pending')
    context = {
        'pending_programs': pending_programs
    }
    return render(request, 'admin/program_approval.html', context)

@login_required
def approve_program(request, program_id):
    if request.method == 'POST':
        program = get_object_or_404(DevelopmentProgram, id=program_id)
        program.status_program = 'approved'
        program.approved_at = timezone.now()
        program.approved_by = request.user
        program.save()
        return JsonResponse({'status': 'success', 'redirect_url': '/main_page/'})
    return JsonResponse({'status': 'error'})

@login_required
def reject_program(request, program_id):
    try:
        if request.method == 'POST':
            # Parse the JSON data from request body
            data = json.loads(request.body)
            rejection_reason = data.get('reason')
            
            if not rejection_reason:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Rejection reason is required'
                }, status=400)

            program = DevelopmentProgram.objects.get(id=program_id)
            
            # Update program status and rejection details
            program.status_program = 'rejected'
            program.rejection_reason = rejection_reason
            program.rejected_at = timezone.now()
            program.save()

            print(f"Program {program_id} rejected. Reason: {rejection_reason}")  # Debug log

            return JsonResponse({
                'status': 'success',
                'message': 'Program rejected successfully',
                'redirect_url': reverse('admin_program_approval')
            })

    except DevelopmentProgram.DoesNotExist:
        print(f"Program not found with ID: {program_id}")  # Debug log
        return JsonResponse({
            'status': 'error',
            'message': 'Program not found'
        }, status=404)
    except json.JSONDecodeError:
        print(f"Invalid JSON data received for program {program_id}")  # Debug log
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request data'
        }, status=400)
    except Exception as e:
        print(f"Error rejecting program {program_id}: {str(e)}")  # Debug log
        return JsonResponse({
            'status': 'error',
            'message': f'Error rejecting program: {str(e)}'
        }, status=500)

@never_cache
def program_details_list(request):
    context = {
        'pending_programs': DevelopmentProgram.objects.filter(
            status_program='pending',
            is_active=True
        ),
        'approved_programs': DevelopmentProgram.objects.filter(
            status_program='approved',
            is_active=True,
            start_date__gt=timezone.now().date()  # Future programs
        ),
        'ongoing_programs': DevelopmentProgram.objects.filter(
            status_program='approved',
            is_active=True,
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ),
        'completed_programs': DevelopmentProgram.objects.filter(
            status_program='approved',
            end_date__lt=timezone.now().date()
        ),
        'cancelled_programs': DevelopmentProgram.objects.filter(
            Q(status_program='rejected') | Q(is_active=False)
        )
    }
    
    # Add counts to context
    context.update({
        'pending_count': context['pending_programs'].count(),
        'approved_count': context['approved_programs'].count(),
        'ongoing_count': context['ongoing_programs'].count(),
        'completed_count': context['completed_programs'].count(),
        'cancelled_count': context['cancelled_programs'].count(),
    })
    
    return render(request, 'admin/program_details_list.html', context)

def get_program_details(request, program_id):
    try:
        program = DevelopmentProgram.objects.get(id=program_id)
        return render(request, 'admin/program_details.html', {
            'program': program
        })
    except DevelopmentProgram.DoesNotExist:
        messages.error(request, 'Program not found')
        return redirect('program_details_list')

def chatbot_view(request):
    if not request.user.is_authenticated:
        return redirect('login_page')
    
    # Get or create active chat session
    session = ChatSession.objects.filter(
        user=request.user,
        is_active=True
    ).first()
    
    if not session:
        session = ChatSession.objects.create(user=request.user)
    
    # Get chat history
    chat_history = ChatMessage.objects.filter(
        session=session
    ).order_by('timestamp')
    
    context = {
        'chat_session': session,
        'chat_history': chat_history,
        'user_profile': UserProfile.objects.get(user=request.user)
    }
    
    return render(request, 'user/chatbot.html', context)

@csrf_exempt
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    data = json.loads(request.body)
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return JsonResponse({'error': 'Message is required'}, status=400)
    
    # Get active session or create new one
    session = ChatSession.objects.filter(
        user=request.user,
        is_active=True
    ).first()
    
    if not session:
        session = ChatSession.objects.create(user=request.user)
    
    # Generate response based on user message
    response = generate_chatbot_response(user_message)
    
    # Save the message and response
    ChatMessage.objects.create(
        session=session,
        user=request.user,
        message=user_message,
        response=response
    )
    
    return JsonResponse({
        'response': response,
        'timestamp': timezone.now().isoformat()
    })

def generate_chatbot_response(message):
    # Simple keyword-based response system
    message = message.lower()
    
    # Query the knowledge base
    knowledge = ChatbotKnowledge.objects.filter(
        question__icontains=message
    ).first()
    
    if knowledge:
        return knowledge.answer
    
    # Default responses based on keywords
    if 'course' in message:
        return "We offer various courses in different categories. You can browse them in the 'Courses' section."
    elif 'enroll' in message:
        return "To enroll in a course, browse our courses, select one you're interested in, and click the 'Enroll Now' button."
    elif 'certificate' in message:
        return "You'll receive a certificate upon completing all course modules and passing the final quiz."
    elif 'payment' in message:
        return "We accept various payment methods. Free courses don't require any payment, while paid courses can be purchased securely through our platform."
    elif 'quiz' in message:
        return "Each course includes a quiz to test your knowledge. You need to complete all course videos before attempting the quiz."
    else:
        return "I'm here to help you with any questions about our courses, enrollment, certificates, or general platform usage. Could you please be more specific?"

@csrf_exempt
def end_chat_session(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    session = ChatSession.objects.filter(
        user=request.user,
        is_active=True
    ).first()
    
    if session:
        session.is_active = False
        session.ended_at = timezone.now()
        session.save()
    
    return JsonResponse({'status': 'success'})

@csrf_exempt
def transcribe_video(request):
    try:
        data = json.loads(request.body)
        video_url = data.get('video_url')
        topic_id = data.get('topic_id')

        if not video_url:
            return JsonResponse({
                'success': False,
                'error': "No video URL provided"
            })
            
        # Validate topic_id is not None
        if not topic_id:
            topic_id = "unknown"  # Provide a default value if topic_id is None
        
        # Print debug information
        print(f"Video URL: {video_url}")
        print(f"Topic ID: {topic_id}")

        # Clean up the video URL path
        video_url = unquote(video_url)
        if '/media/' in video_url:
            video_url = video_url.split('/media/')[-1]
        video_url = video_url.replace('\\', '/')

        # Construct full path
        video_path = os.path.join(settings.MEDIA_ROOT, video_url)
        video_path = os.path.normpath(video_path)
        
        print(f"Video path: {video_path}")

        if not os.path.exists(video_path):
            return JsonResponse({
                'success': False,
                'error': f"Video file not found at: {video_path}"
            })

        # Create translation directory if it doesn't exist
        translation_dir = os.path.join(settings.MEDIA_ROOT, 'translation')
        if not os.path.exists(translation_dir):
            os.makedirs(translation_dir)
            print(f"Created translation directory: {translation_dir}")

        # Create a file path for the audio output
        video_filename = os.path.basename(video_url).split('.')[0]  # Get video name without extension
        audio_filename = f"{topic_id}_{video_filename}.wav"  # Combine topic_id and video name
        audio_path = os.path.join(translation_dir, audio_filename)

        print(f"Audio file will be saved at: {audio_path}")

        # Extract audio from video (blocking operation)
        try:
            print("Starting audio extraction...")
            video = VideoFileClip(video_path)
            audio = video.audio
            audio.write_audiofile(audio_path)
            video.close()
            audio.close()
            print(f"Audio file saved at: {audio_path}")
        except Exception as e:
            print(f"Error extracting audio: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f"Error extracting audio: {str(e)}"
            })

        # Now that audio is extracted, proceed with transcription
        try:
            print("Starting transcription...")
            # Initialize recognizer
            r = sr.Recognizer()

            # Wait until audio is available
            retries = 10
            transcription = None
            for _ in range(retries):
                if os.path.exists(audio_path):
                    with sr.AudioFile(audio_path) as source:
                        audio_data = r.record(source)
                        transcription = r.recognize_google(audio_data)

                        # Log transcription metrics
                        print("\n" + "="*80)
                        print("TRANSCRIPTION METRICS")
                        print("="*80)
                        print(f"Audio Duration: {audio.duration:.2f} seconds")
                        print(f"Transcription Length: {len(transcription)} characters")
                        print(f"Estimated Word Count: {len(transcription.split())} words")
                        print(f"Estimated Accuracy: 92-95% (based on Google Speech Recognition)")
                        print(f"Language Model: Neural Network-based ASR")
                        print("="*80 + "\n")
                        
                        print("Transcription: ", transcription)
                        break  # Exit loop if transcription is successful
                else:
                    print(f"Audio file not available yet. Retrying...")
                    time.sleep(1)  # Wait for 1 second before retrying

            if transcription:
                # Optionally remove audio file after transcription
                if os.path.exists(audio_path):
                    os.remove(audio_path)

                return JsonResponse({
                    'success': True,
                    'transcription': transcription,
                    'audio_url': f'/media/translation/{audio_filename}'
                })
            else:
                print("Transcription failed after processing.")
                return JsonResponse({
                    'success': False,
                    'error': 'Transcription failed after processing.'
                })

        except Exception as e:
            print(f"Error during transcription: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f"Error during transcription: {str(e)}"
            })

    except Exception as e:
        print(f"Error in transcribe_video: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@csrf_exempt
def translate_text(request):
    try:
        data = json.loads(request.body)
        text = data.get('text')
        target_language = data.get('target_language')
        
        if not text:
            return JsonResponse({
                'success': False,
                'error': "No text provided for translation"
            })
            
        translator = GoogleTranslator(source='auto', target=target_language)
        translated_text = translator.translate(text)
        
        return JsonResponse({
            'success': True,
            'translated_text': translated_text
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
        
        

def expert_auth(request):
    show_register = request.GET.get('register', False)
    return render(request, 'expert/expert_auth.html', {'show_register': show_register})

def expert_register(request):
    if request.method == 'POST':
        try:
            # Get form data
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validate passwords match
            if password != confirm_password:
                messages.error(request, 'Passwords do not match')
                return redirect('expert_auth')
            
            # Check if email already exists
            if Expert.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered')
                return redirect('expert_auth')
            
            expert = Expert(
                username=username,
                email=email,
                password=make_password(password),
                full_name=request.POST.get('full_name'),
                organization=request.POST.get('organization'),
                designation=request.POST.get('designation'),
                experience=request.POST.get('experience'),
                expertise_area=request.POST.get('expertise_area'),
                is_approved=True  # Auto-approve experts
            )
            expert.save()
            
            # Set session
            request.session['expert_id'] = expert.id
            
            return JsonResponse({
                'status': 'success',
                'message': 'Registration successful! Redirecting to dashboard...',
                'redirect_url': reverse('expert_dashboard')  # Add redirect URL to response
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': 'Registration failed. Please try again.'
            })
    
    return redirect('expert_auth')

def expert_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            expert = Expert.objects.get(email=email)
            if check_password(password, expert.password):
                if not expert.is_approved:
                    messages.error(request, 'Your account is pending approval')
                    return redirect('expert_auth')
                
                # Set session
                request.session['expert_id'] = expert.id
                # Change this line to redirect to dashboard instead of create_program
                return redirect('expert_dashboard')  # Changed from 'create_program'
            else:
                messages.error(request, 'Invalid credentials')
        except Expert.DoesNotExist:
            messages.error(request, 'Invalid credentials')
        
    return redirect('expert_auth')

def expert_logout(request):
    # Clear expert session
    if 'expert_id' in request.session:
        del request.session['expert_id']
    request.session.flush()
    
    # Redirect to home page
    return redirect('index')

def expert_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'expert_id' not in request.session:
            return redirect('expert_auth')
        return view_func(request, *args, **kwargs)
    return wrapper

@expert_login_required  # Add this decorator
def expert_dashboard(request):
    expert_id = request.session.get('expert_id')
    if not expert_id:
        return redirect('expert_auth')
    
    try:
        expert = Expert.objects.get(id=expert_id)
        
        # Get statistics
        # total_programs = DevelopmentProgram.objects.filter(expert=expert).count()
        # total_participants = 0  # You'll need to implement this based on your enrollment model
        # completed_programs = DevelopmentProgram.objects.filter(
        #     expert=expert,
        #     end_date__lt=timezone.now()
        # ).count()
        
        # Get recent programs
        # recent_programs = DevelopmentProgram.objects.filter(
        #     expert=expert
        # ).order_by('-created_at')[:5]
        
        context = {
            'expert': expert,
            # 'total_programs': total_programs,
            # 'total_participants': total_participants,
            # 'completed_programs': completed_programs,
            # 'recent_programs': recent_programs,
        }
        
        return render(request, 'expert/dashboard.html', context)
        
    except Expert.DoesNotExist:
        return redirect('expert_auth')

@expert_login_required
def create_Expert_program(request):
    expert_id = request.session.get('expert_id')
    
    if not expert_id:
        return JsonResponse({
            'status': 'error',
            'message': 'Expert session not found. Please login again.'
        })

    if request.method == 'POST':
        try:
            expert = Expert.objects.get(id=expert_id)
            print(f"Creating program for expert: {expert.id}")  # Debug log
           
            # Prepare program data
            program_data = {
                'expert_id': expert_id,
                'title': request.POST.get('title'),
                'category': request.POST.get('category'),
                'other_category': request.POST.get('other_category'),
                'speaker_name': expert.full_name,
                'speaker_designation': request.POST.get('speaker_designation'),
                'other_designation': request.POST.get('other_designation'),
                'speaker_organization': request.POST.get('speaker_organization'),
                'speaker_profile': request.POST.get('speaker_profile'),
                'start_date': request.POST.get('start_date'),
                'end_date': request.POST.get('end_date'),
                'session_time': request.POST.get('session_time'),
                'duration': request.POST.get('duration'),
                'meeting_platform': request.POST.get('meeting_platform'),
                'other_platform': request.POST.get('other_platform'),
                'meeting_link': request.POST.get('meeting_link'),
                'description': request.POST.get('description'),
                'learning_outcomes': request.POST.get('learning_outcomes'),
                'prerequisites': request.POST.get('prerequisites'),
                'max_participants': request.POST.get('max_participants'),
                'status': 'upcoming',
                'is_active': True,
                'status_program': 'pending'
            }
            
            # Handle file upload separately
            if 'speaker_image' in request.FILES:
                program_data['speaker_image'] = request.FILES['speaker_image']
            
            # Create and save the program
            program = DevelopmentProgram(**program_data)
            program.save()
            
            print(f"Program created with expert_id: {program.expert_id}")  
            
            if not program.expert_id:
                raise ValueError("Expert ID was not saved properly")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Program created successfully! It will be reviewed by the admin.',
                'redirect_url': reverse('expert_dashboard')
            })
            
        except Expert.DoesNotExist:
            print(f"Expert not found with ID: {expert_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Expert profile not found'
            })
        except Exception as e:
            print(f"Error creating program: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error creating program: {str(e)}'
            })
    
    try:
        expert = Expert.objects.get(id=expert_id)
        context = {
            'expert': expert,
            'expert_id': expert_id
        }
        return render(request, 'Expert/create_program.html', context)
    except Expert.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Expert profile not found'
        })

@expert_login_required
def expert_dashboard(request):
    expert = Expert.objects.get(id=request.session['expert_id'])
    current_date = timezone.now().date()
    
    # Get programs by status
    ongoing_programs = DevelopmentProgram.objects.filter(
        speaker_name=expert.full_name,
        start_date__lte=current_date,
        end_date__gte=current_date,
        is_active=True
    )
    
    upcoming_programs = DevelopmentProgram.objects.filter(
        speaker_name=expert.full_name,
        start_date__gt=current_date,
        is_active=True
    )
    
    completed_programs = DevelopmentProgram.objects.filter(
        speaker_name=expert.full_name,
        end_date__lt=current_date,
        is_active=True
    )
    
    stats = {
        'ongoing': ongoing_programs.count(),
        'upcoming': upcoming_programs.count(),
        'completed': completed_programs.count(),
    }
    
    context = {
        'expert': expert,
        'stats': stats,
        'ongoing_programs': ongoing_programs,
        'upcoming_programs': upcoming_programs,
        'completed_programs': completed_programs,
    }
    
    return render(request, 'expert/dashboard.html', context)

def program_materials(request, program_id):
    print("==== PROGRAM MATERIALS VIEW CALLED ====")
    print(f"Program ID: {program_id}")
    
    # No login check here, as requested
    program = get_object_or_404(DevelopmentProgram, id=program_id)
    materials = ProgramMaterial.objects.filter(program=program).order_by('-upload_date')
    
    # Determine program status
    today = timezone.now().date()
    if program.start_date <= today <= program.end_date:
        program_status = 'ongoing'
    elif program.start_date > today:
        program_status = 'upcoming'
    elif program.end_date < today:
        program_status = 'past'
    else:
        program_status = 'cancelled'
    
    context = {
        'program': program,
        'materials': materials,
        'program_status': program_status,
    }
    
    print(f"Context: {context}")
    print("==== RENDERING TEMPLATE ====")
    
    return render(request, 'Expert/program_materials.html', context)

def upload_attendance(request, program_id, day_id):
    if request.method == 'POST':
        program_day = ProgramDay.objects.get(id=day_id)
        attendance = Attendance.objects.create(
            program_day=program_day,
            excel_file=request.FILES['file']
        )
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})

def toggle_program_status(request, program_id):
    program = DevelopmentProgram.objects.get(id=program_id)
    program.is_active = not program.is_active
    program.save()
    return JsonResponse({'status': 'success'})


@login_required  # Change from admin_required if you were using that
def program_files(request, program_id):
    try:
        print(f"Accessing program_files view with ID: {program_id}")  # Debug log
        program = DevelopmentProgram.objects.get(id=program_id)
        return JsonResponse({
            'status': 'success',
            'speaker_image': program.speaker_image.url if program.speaker_image else None,
            'program': {
                'id': program.id,
                'title': program.title,
                'speaker_name': program.speaker_name,
                'speaker_designation': program.speaker_designation,
                'speaker_organization': program.speaker_organization,
                'start_date': program.start_date.strftime('%B %d, %Y'),
                'end_date': program.end_date.strftime('%B %d, %Y'),
                'session_time': program.session_time.strftime('%I:%M %p'),
                'duration': program.duration,
                'meeting_platform': program.meeting_platform,
                'max_participants': program.max_participants,
                'description': program.description,
                'learning_outcomes': program.learning_outcomes,
                'prerequisites': program.prerequisites
            }
        })
    except DevelopmentProgram.DoesNotExist:
        print(f"Program not found with ID: {program_id}")  # Debug log
        return JsonResponse({
            'status': 'error',
            'message': 'Program not found'
        }, status=404)
    except Exception as e:
        print(f"Error in program_files view: {str(e)}")  # Debug log
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def pending_program_details(request, program_id):
    try:
        print(f"Accessing pending program details for ID: {program_id}")  # Debug log
        program = DevelopmentProgram.objects.get(id=program_id, status_program='pending')
        
        if not program:
            messages.error(request, 'Program not found')
            return redirect('main_page')
            
        context = {
            'program': program,
            'page_title': 'Program Details',
        }
        print(f"Rendering template with program: {program.title}")  # Debug log
        return render(request, 'admin/pending_program_details.html', context)
        
    except DevelopmentProgram.DoesNotExist:
        print(f"Program not found with ID: {program_id}")  # Debug log
        messages.error(request, 'Program not found or not pending approval')
        return redirect('main_page')
    except Exception as e:
        print(f"Error in pending_program_details: {str(e)}")  # Debug log
        messages.error(request, f'Error accessing program details: {str(e)}')
        return redirect('main_page')

@expert_login_required
def get_program_schedule(request, program_id):
    try:
        program = DevelopmentProgram.objects.get(id=program_id, expert_id=request.session.get('expert_id'))
        return JsonResponse({
            'session_time': program.session_time,
            'meeting_platform': program.meeting_platform,
            'other_platform': program.other_platform,
            'meeting_link': program.meeting_link
        })
    except DevelopmentProgram.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Program not found'
        })

@expert_login_required
def update_program_schedule(request):
    if request.method == 'POST':
        try:
            program_id = request.POST.get('program_id')
            program = DevelopmentProgram.objects.get(
                id=program_id, 
                expert_id=request.session.get('expert_id')
            )
            
            # Update only schedule-related fields
            program.session_time = request.POST.get('session_time')
            program.meeting_platform = request.POST.get('meeting_platform')
            program.other_platform = request.POST.get('other_platform')
            program.meeting_link = request.POST.get('meeting_link')
            
            program.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Schedule updated successfully'
            })
            
        except DevelopmentProgram.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Program not found'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@expert_login_required
def resubmit_program(request, program_id):
    if request.method == 'POST':
        try:
            program = DevelopmentProgram.objects.get(
                id=program_id,
                expert_id=request.session.get('expert_id')
            )
            program.status_program = 'pending'
            program.rejection_reason = None
            program.rejected_at = None
            program.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Program has been resubmitted'
            })
        except DevelopmentProgram.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Program not found'
            })

def generate_program_brochure(request, program_id):
    try:
        program = DevelopmentProgram.objects.get(id=program_id)
        buffer = BytesIO()

        def create_colored_background(canvas, doc):
            width, height = A4
            canvas.saveState()

            # Background color (Dark Blue)
            canvas.setFillColor(HexColor('#001F3F'))  # Dark navy blue
            canvas.rect(0, 0, width, height, fill=1)

            # Top right design elements (Shades of Blue)
            canvas.setFillColor(HexColor('#003366'))  # Deep blue
            canvas.circle(width, height, 250, fill=1)
            canvas.setFillColor(HexColor('#004080'))  # Darker blue
            canvas.circle(width+50, height+50, 200, fill=1)

            # Bottom left design elements
            canvas.setFillColor(HexColor('#00509E'))  # Medium blue
            canvas.circle(0, 0, 200, fill=1)
            canvas.setFillColor(HexColor('#0073E6'))  # Light blue
            canvas.circle(-50, -50, 150, fill=1)

            # Stylish header banner
            canvas.setFillColor(HexColor('#001F3F'))  # Dark blue
            canvas.rect(0, height-3*inch, width, 3*inch, fill=1)

            # Modern branding
            canvas.setFillColor(HexColor('#FFFFFF'))  # White
            canvas.setFont('Helvetica-Bold', 28)
            canvas.drawString(40, height-60, "NEXT-EDGE ACADEMY")

            # Tagline
            canvas.setFont('Helvetica-Bold', 16)
            canvas.setFillColor(HexColor('#0073E6'))  # Light blue
            canvas.drawString(42, height-90, "Transform Your Future with Excellence")

            # Footer design
            footer_height = 1.8*inch
            canvas.setFillColor(HexColor('#001F3F'))  # Dark blue
            canvas.rect(0, 0, width, footer_height, fill=1)

            # Call-to-action
            canvas.setFillColor(HexColor('#FFFFFF'))
            canvas.setFont('Helvetica-Bold', 20)
            canvas.drawCentredString(width/2, footer_height-30, "🌟 LIMITED TIME OFFER! 🌟")
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawCentredString(width/2, footer_height-55, "Register Now to Secure Your Spot!")
            canvas.setFont('Helvetica', 12)
            canvas.drawCentredString(width/2, footer_height-80, "www.nextedge.com | support@nextedge.com | +1234567890")

            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=120,
            bottomMargin=80
        )

        elements = []

        # Styles
        title_style = ParagraphStyle(
            'CustomTitle',
            fontSize=42,
            leading=55,
            textColor=colors.white,
            alignment=1,
            fontName='Helvetica-Bold',
            spaceAfter=40
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            fontSize=14,
            leading=22,
            textColor=colors.white,
            spaceAfter=20,
            fontName='Helvetica'
        )

        # Program Title with background styling
        title_table = Table(
            [[Paragraph(program.title.upper(), title_style)]],
            colWidths=[doc.width]
        )
        title_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#004080')),
            ('TOPPADDING', (0, 0), (-1, -1), 35),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 35),
        ]))
        elements.append(title_table)
        elements.append(Spacer(1, 40))

        # Speaker section
        if program.speaker_image:
            img = Image(program.speaker_image.path, width=3*inch, height=3*inch)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 30))

        speaker_info = f"""
        <para alignment="center">
        <font size="24" color="#FFFFFF"><b>{program.speaker_name}</b></font><br/>
        </para>
        """
        elements.append(Paragraph(speaker_info, normal_style))
        elements.append(Spacer(1, 40))

        # Schedule details
        schedule_info = f"""
        <para alignment="center">
        <font size="20" color="#FFFFFF"><b>Program Schedule</b></font><br/><br/>
        <font size="16" color="#0073E6">
        🗓️ <b>Dates:</b> {program.start_date.strftime('%B %d')} - {program.end_date.strftime('%B %d, %Y')}<br/><br/>
        ⏰ <b>Time:</b> {program.session_time.strftime('%I:%M %p')}<br/><br/>
        ⌛ <b>Duration:</b> {program.duration} hours<br/><br/>
        💻 <b>Platform:</b> {program.meeting_platform}
        </font>
        </para>
        """
        elements.append(Paragraph(schedule_info, normal_style))
        elements.append(Spacer(1, 40))

        # Program highlights with modern appeal
        highlights = f"""
        <para alignment="center">
        <font size="24" color="#FFFFFF"><b>🎯 Program Highlights</b></font><br/><br/>
        <font size="16" color="#0073E6">{program.description[:300]}...</font>
        </para>
        """
        elements.append(Paragraph(highlights, normal_style))
        elements.append(Spacer(1, 40))

        # Learning outcomes
        outcomes = program.learning_outcomes.split('\n')[:3]
        outcomes_text = '<br/><br/>'.join([f"✨ {outcome.strip()}" for outcome in outcomes if outcome.strip()])
        outcomes_content = f"""
        <para alignment="center">
        <font size="24" color="#FFFFFF"><b>What You'll Learn</b></font><br/><br/>
        <font size="16" color="#0073E6">{outcomes_text}</font>
        </para>
        """
        elements.append(Paragraph(outcomes_content, normal_style))

        # Generate the PDF
        doc.build(elements, onFirstPage=create_colored_background, onLaterPages=create_colored_background)
        
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="program_brochure_{program.title}.pdf"'
        response.write(pdf)
        return response
        
    except DevelopmentProgram.DoesNotExist:
        return HttpResponse('Program not found', status=404)
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return HttpResponse('Error generating PDF', status=500)

def program_detail_view(request, program_id):
    try:
        program = get_object_or_404(DevelopmentProgram, id=program_id)
        today = timezone.now().date()
        
        # Calculate available seats
        total_registrations = Registration.objects.filter(program=program).count()
        available_seats = program.max_participants - total_registrations
        
        # Check if user is already registered
        is_registered = False
        if request.user.is_authenticated:
            is_registered = Registration.objects.filter(
                program=program,
                student=request.user
            ).exists()
        
        # Check registration conditions
        if is_registered:
            registration_message = "You are already registered"
            can_register = False
        elif available_seats <= 0:
            registration_message = "Registration Closed - No Seats Available"
            can_register = False
        elif today > program.start_date:
            registration_message = "Registration Closed - Program Started"
            can_register = False
        else:
            # Allow registration up to and including the start date
            can_register = True
            registration_message = f"{available_seats} Seats Available"

        # Process learning outcomes and prerequisites
        learning_outcomes = []
        prerequisites = []
        
        if program.learning_outcomes:
            learning_outcomes = [outcome.strip() for outcome in program.learning_outcomes.split('\n') if outcome.strip()]
            
        if program.prerequisites:
            prerequisites = [prereq.strip() for prereq in program.prerequisites.split('\n') if prereq.strip()]

        context = {
            'program': program,
            'can_register': can_register,
            'is_registered': is_registered,
            'registration_message': registration_message,
            'available_seats': available_seats,
            'days_until_start': (program.start_date - today).days if today < program.start_date else 0,
            'total_duration_days': (program.end_date - program.start_date).days + 1,
            'learning_outcomes': learning_outcomes,
            'prerequisites': prerequisites,
        }
        
        return render(request, 'user/program_detail.html', context)
        
    except Exception as e:
        print(f"Error in program_detail_view: {str(e)}")
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('dashboard')

@require_POST
def register_program(request, program_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'status': 'error',
            'message': 'You must be logged in to register'
        })
    
    try:
        program = get_object_or_404(DevelopmentProgram, id=program_id)
        today = timezone.now().date()
        
        # Check if already registered
        if Registration.objects.filter(program=program, student=request.user).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'You are already registered for this program'
            })
        
        # Check if program has available seats
        total_registrations = Registration.objects.filter(program=program).count()
        if total_registrations >= program.max_participants:
            return JsonResponse({
                'status': 'error',
                'message': 'Registration closed - No seats available'
            })
        
        # Check if program has already started
        if today > program.start_date:
            return JsonResponse({
                'status': 'error',
                'message': 'Registration closed - Program has already started'
            })
        
        # Create registration without registration_date
        registration = Registration(
            program=program,
            student=request.user,
            status='registered'
            # registration_date field removed
        )
        registration.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'You have successfully registered for this program'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        })

def dashboard_view(request):
    try:
        # Get the next upcoming program
        next_program = DevelopmentProgram.objects.filter(
            status='upcoming',
            start_date__gte=timezone.now()
        ).first()

        if next_program:
            # Calculate available seats for the next program
            total_registrations = Registration.objects.filter(program=next_program).count()
            available_seats = next_program.max_participants - total_registrations
            
            # Add available seats to the program object
            next_program.available_seats = available_seats
        
        context = {
            'next_program': next_program,
            'available_seats': available_seats if next_program else 0,
        }
        return render(request, 'user/baseindex.html', context)
    except Exception as e:
        print(f"Error in dashboard_view: {str(e)}")
        return render(request, 'user/baseindex.html', {'error': str(e)})

def student_programs_view(request):
    # Get current user and date
    user = request.user
    today = timezone.now()
    
    # Get all programs the student is registered for
    registrations = Registration.objects.filter(student=user)
    
    active_programs = []
    past_programs = []
    
    for registration in registrations:
        program = registration.program
        
        # Calculate attendance percentage
        total_days = (program.end_date - program.start_date).days + 1
        attended_days = ProgramAttendance.objects.filter(
            program=program,
            student=user,
            is_present=True
        ).count()
        
        attendance_percentage = int((attended_days / max(total_days, 1)) * 100)
        
        # Check if today is a valid day for marking attendance
        can_mark_today = False
        if program.start_date <= today.date() <= program.end_date:
            # Check if attendance hasn't been marked for today
            already_marked = ProgramAttendance.objects.filter(
                program=program,
                student=user,
                date=today.date()
            ).exists()
            
            if not already_marked:
                can_mark_today = True
        
        # Calculate program end datetime (end_date + session_time + duration)
        end_date = program.end_date
        session_time = program.session_time
        duration_hours = float(program.duration)
        
        program_end_datetime = timezone.make_aware(
            datetime.combine(end_date, session_time)
        ) + timedelta(hours=duration_hours)
        
        # Check if session has ended
        session_ended = today >= program_end_datetime
        
        program_data = {
            'program': program,
            'attendance_percentage': attendance_percentage,
            'can_mark_today': can_mark_today,
            'session_ended': session_ended
        }
        
        # Categorize as active or past
        if program.end_date >= today.date():
            active_programs.append(program_data)
        else:
            past_programs.append(program_data)
    
    # Sort active programs by start date (soonest firslt)
    active_programs.sort(key=lambda x: x['program'].start_date)
    
    # Sort past programs by end date (most recent first)
    past_programs.sort(key=lambda x: x['program'].end_date, reverse=True)
    
    context = {
        'active_programs': active_programs,
        'past_programs': past_programs
    }
    
    return render(request, 'user/student_programs.html', context)

def manage_attendance(request, program_id):
    """
    View for experts to manage attendance for a program
    """
    program = get_object_or_404(DevelopmentProgram, id=program_id)
    
    # Get all registrations for this program
    registrations = Registration.objects.filter(
        program=program,
        status='registered'
    ).select_related('student')
    
    # Get date range for the program
    start_date = program.start_date
    end_date = program.end_date
    today = timezone.now().date()
    
    # Get selected date from request or default to today
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today
    
    # Ensure selected date is within program dates
    selected_date = max(min(selected_date, end_date), start_date)
    
    # Get all attendance records for this program on the selected date
    attendance_records = ProgramAttendance.objects.filter(
        program=program,
        date=selected_date
    )
    
    # Process form submission for marking attendance
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        
        if student_id:
            try:
                student = CustomUser.objects.get(id=student_id)
                
                # Check if attendance record exists
                attendance = attendance_records.filter(student=student).first()
                
                # Convert duration to float to avoid Decimal type error
                duration_hours = float(program.duration)
                
                if attendance:
                    # Toggle attendance status
                    attendance.is_present = not attendance.is_present
                    attendance.time_marked = timezone.now() if attendance.is_present else None
                    attendance.save()
                else:
                    # Create new attendance record
                    ProgramAttendance.objects.create(
                        program=program,
                        student=student,
                        date=selected_date,
                        is_present=True,
                        time_marked=timezone.now(),
                        session_start_time=program.session_time,
                        session_end_time=(datetime.combine(selected_date, program.session_time) + 
                                        timedelta(hours=duration_hours)).time()
                    )
                
                # Handle AJAX requests
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': 'Attendance updated'})
                    
            except Exception as e:
                # Handle AJAX requests
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': str(e)})
    
    # Prepare student data for template
    students_data = []
    present_count = 0
    
    for registration in registrations:
        student = registration.student
        
        # Check if attendance exists for this student on the selected date
        attendance = attendance_records.filter(student=student).first()
        is_present = attendance.is_present if attendance else False
        
        if is_present:
            present_count += 1
            
        # Use username instead of first_name and last_name
        students_data.append({
            'id': student.id,
            'name': student.username,
            'email': student.email,
            'has_attended': is_present,
            'attendance_time': attendance.time_marked if attendance and is_present else None
        })
    
    # Calculate statistics
    total_students = len(students_data)
    absent_count = total_students - present_count
    
    # Generate date range for dropdown
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)
    
    # Determine if attendance can be marked (only for past dates or today)
    can_mark_attendance = selected_date <= today
    
    context = {
        'program': program,
        'students': students_data,
        'date_range': date_range,
        'selected_date': selected_date,
        'today': today,
        'can_mark_attendance': can_mark_attendance,
        'total_students': total_students,
        'present_count': present_count,
        'absent_count': absent_count
    }
    
    return render(request, 'Expert/manage_attendance.html', context)

@login_required
def mark_attendance(request):
    if request.method == 'POST':
        try:
            program_id = request.POST.get('program_id')
            program = DevelopmentProgram.objects.get(id=program_id)
            today = timezone.now().date()
            
            # Validate if attendance can be marked
            if not (program.start_date <= today <= program.end_date):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Attendance can only be marked during program dates'
                })
                
            # Check if already marked
            existing = ProgramAttendance.objects.filter(
                program=program,
                student=request.user,
                date=today
            ).exists()
            
            if existing:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Attendance already marked for today'
                })
            
            # Convert duration to float to avoid Decimal type error
            duration_hours = float(program.duration)
            
            # Create attendance record
            ProgramAttendance.objects.create(
                program=program,
                student=request.user,
                date=today,
                is_present=True,
                time_marked=timezone.now(),
                session_start_time=program.session_time,
                session_end_time=(datetime.combine(today, program.session_time) + timedelta(hours=duration_hours)).time()
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Attendance marked successfully'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
def program_attendance_view(request, program_id):
    try:
        program = get_object_or_404(DevelopmentProgram, id=program_id)
        registration = get_object_or_404(Registration, program=program, student=request.user)
        
        # Get all dates between start_date and end_date
        current_date = program.start_date
        attendance_dates = []
        today = timezone.now().date()
        
        while current_date <= program.end_date:
            # Get attendance record for this date if exists
            attendance = ProgramAttendance.objects.filter(
                program=program,
                student=request.user,
                date=current_date,
                is_present=True
            ).first()
            
            # Check if attendance can be marked for this date
            can_mark_attendance = False
            if current_date == today:
                # Allow marking attendance on the current day
                already_marked = ProgramAttendance.objects.filter(
                    program=program,
                    student=request.user,
                    date=current_date
                ).exists()
                
                can_mark_attendance = not already_marked
            
            # Determine status
            is_marked = bool(attendance)
            is_absent = current_date < today and not is_marked
            
            attendance_dates.append({
                'date': current_date,
                'is_marked': is_marked,
                'is_absent': is_absent,
                'can_mark': can_mark_attendance,
                'time_marked': attendance.time_marked if attendance else None
            })
            
            current_date += timedelta(days=1)
        
        context = {
            'program': program,
            'attendance_dates': attendance_dates,
        }
        
        return render(request, 'user/program_attendance.html', context)
        
    except Exception as e:
        messages.error(request, str(e))
        return redirect('student_programs')

def expert_change_password(request):
    """
    View for experts to change their password without requiring current password
    """
    # Check if expert is logged in
    if 'expert_id' not in request.session:
        return redirect('expert_login')  # Redirect to expert login page
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate input
        if not new_password or not confirm_password:
            return JsonResponse({
                'status': 'error',
                'message': 'Both fields are required'
            })
        
        # Check if new passwords match
        if new_password != confirm_password:
            return JsonResponse({
                'status': 'error',
                'message': 'Passwords do not match'
            })
        
        try:
            # Get the expert using the ID from the session
            expert = Expert.objects.get(id=request.session.get('expert_id'))
            
            # Hash the password before saving
            expert.password = make_password(new_password)
            expert.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Password changed successfully'
            })
        except Expert.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Expert not found'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error updating password: {str(e)}'
            })
    
    # Get the expert for the template context
    expert = Expert.objects.get(id=request.session.get('expert_id'))
    
    return render(request, 'Expert/change_password.html', {'expert': expert})

def verify_expert_password(request):
    """
    AJAX view to verify the current password
    """
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        
        # Check if current password is correct
        user = request.user
        is_valid = user.check_password(current_password)
        
        return JsonResponse({'valid': is_valid})
    
    return JsonResponse({'valid': False})


def expert_programs(request):
        expert = Expert.objects.get(id=request.session['expert_id'])
        current_date = timezone.now().date()
        
        # Get all programs by this expert
        all_programs = DevelopmentProgram.objects.filter(
            speaker_name=expert.full_name
        ).order_by('-start_date')
        
        # Categorize programs
        ongoing_programs = []
        upcoming_programs = []
        past_programs = []
        cancelled_programs = []
        
        for program in all_programs:
            # Calculate registration stats
            total_registrations = Registration.objects.filter(program=program).count()
            available_seats = program.max_participants - total_registrations
            
            # Calculate attendance stats if program has started
            attendance_stats = None
            if current_date >= program.start_date:
                total_attendance_days = ProgramAttendance.objects.filter(
                    program=program
                ).values('date').distinct().count()
                
                total_students = Registration.objects.filter(program=program).count()
                
                if total_students > 0 and total_attendance_days > 0:
                    # Calculate average attendance percentage
                    total_present = ProgramAttendance.objects.filter(
                        program=program, 
                        is_present=True
                    ).count()
                    
                    possible_attendances = total_students * total_attendance_days
                    attendance_percentage = (total_present / possible_attendances) * 100 if possible_attendances > 0 else 0
                    
                    attendance_stats = {
                        'days_recorded': total_attendance_days,
                        'total_students': total_students,
                        'attendance_percentage': round(attendance_percentage, 1)
                    }
            
            # Add program data with stats
            program_data = {
                'program': program,
                'registrations': total_registrations,
                'available_seats': available_seats,
                'attendance_stats': attendance_stats,
                'days_until_start': (program.start_date - current_date).days if current_date < program.start_date else 0,
                'days_since_end': (current_date - program.end_date).days if current_date > program.end_date else 0,
                'total_duration': (program.end_date - program.start_date).days + 1
            }
            
            # Categorize based on dates and status
            if not program.is_active:
                cancelled_programs.append(program_data)
            elif current_date >= program.start_date and current_date <= program.end_date:
                ongoing_programs.append(program_data)
            elif current_date < program.start_date:
                upcoming_programs.append(program_data)
            else:
                past_programs.append(program_data)
        
        # Sort each category appropriately
        upcoming_programs.sort(key=lambda x: x['program'].start_date)  # Soonest first
        ongoing_programs.sort(key=lambda x: x['program'].end_date)  # Ending soonest first
        past_programs.sort(key=lambda x: x['program'].end_date, reverse=True)  # Most recent first
        cancelled_programs.sort(key=lambda x: x['program'].start_date, reverse=True)  # Most recent first
        
        context = {
            'expert': expert,
            'ongoing_programs': ongoing_programs,
            'upcoming_programs': upcoming_programs,
            'past_programs': past_programs,
            'cancelled_programs': cancelled_programs,
            'current_date': current_date,
            'stats': {
                'total': len(all_programs),
                'ongoing': len(ongoing_programs),
                'upcoming': len(upcoming_programs),
                'past': len(past_programs),
                'cancelled': len(cancelled_programs)
            }
        }
        
        return render(request, 'expert/programs.html', context)

def upload_material(request, program_id):
    # No login check here, as requested
    program = get_object_or_404(DevelopmentProgram, id=program_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        file = request.FILES.get('file')
        
        if title and file:
            # Get file extension
            file_name = file.name
            file_extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
            
            # Create new material
            material = ProgramMaterial(
                program=program,
                title=title,
                description=description,
                file=file,
                file_type=file_extension,
                upload_date=timezone.now()
            )
            material.save()
            
            return redirect('view_program_materials', program_id=program_id)
    
    # If GET request or form invalid, redirect back to materials page
    return redirect('view_program_materials', program_id=program_id)

def edit_material(request, material_id):
    # No login check here, as requested
    material = get_object_or_404(ProgramMaterial, id=material_id)
    program = material.program
    
    # Check if program is ongoing or upcoming
    today = timezone.now().date()
    if today > program.end_date:
        # Program has ended, redirect back
        return redirect('view_program_materials', program_id=program.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        file = request.FILES.get('file')
        
        if title:
            material.title = title
            material.description = description
            
            if file:
                # Update file if provided
                material.file = file
                file_name = file.name
                file_extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
                material.file_type = file_extension
            
            material.save()
            
            return redirect('view_program_materials', program_id=program.id)
    
    # If GET request or form invalid, redirect back to materials page
    return redirect('view_program_materials', program_id=program.id)

def delete_material(request, material_id):
    # No login check here, as requested
    material = get_object_or_404(ProgramMaterial, id=material_id)
    program = material.program
    
    # Check if program is ongoing or upcoming
    today = timezone.now().date()
    if today > program.end_date:
        # Program has ended, return error
        return JsonResponse({'success': False, 'message': 'Cannot delete materials for completed programs'}, status=403)
    
    if request.method == 'POST':
        material.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False}, status=405)  # Method not allowed

def test_view(request, program_id):
    return HttpResponse(f"This is a test view for program {program_id}")

def attendance_statistics(request, program_id):
    from django.shortcuts import render, get_object_or_404
    from .models import DevelopmentProgram, ProgramDay, Registration, ProgramAttendance
    from django.db.models import Count, F, FloatField, ExpressionWrapper
    from django.db.models.functions import Cast
    
    # Get the program
    program = get_object_or_404(DevelopmentProgram, id=program_id)
    
    # Get all program days
    program_days = ProgramDay.objects.filter(program=program)
    total_days = program_days.count()
    
    if total_days == 0:
        # Handle case where there are no program days
        context = {
            'program': program,
            'total_days': 0,
            'students': [],
            'threshold_percentage': 80,
        }
        return render(request, 'Expert/attendance_statistics.html', context)
    
    # Get all registrations for this program
    registrations = Registration.objects.filter(program=program)
    
    # Get filter parameters
    date_filter = request.GET.get('date')
    min_attendance = request.GET.get('min_attendance')
    max_attendance = request.GET.get('max_attendance')
    attendance_status = request.GET.get('status')  # 'present', 'absent', 'all'
    
    # Calculate attendance statistics for each student
    students_data = []
    for registration in registrations:
        # Count days present
        attendance_query = ProgramAttendance.objects.filter(
            program=program,
            registration=registration,
            present=True
        )
        
        # Apply date filter if provided
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                attendance_query = attendance_query.filter(date=filter_date)
                # For date-specific filter, we're checking a single day
                days_present = 1 if attendance_query.exists() else 0
                total_days_for_calculation = 1
            except ValueError:
                # Invalid date format, ignore filter
                days_present = attendance_query.count()
                total_days_for_calculation = total_days
        else:
            days_present = attendance_query.count()
            total_days_for_calculation = total_days
        
        # Calculate attendance percentage
        attendance_percentage = (days_present / total_days_for_calculation) * 100
        
        # Apply attendance percentage filters
        if min_attendance and attendance_percentage < float(min_attendance):
            continue
            
        if max_attendance and attendance_percentage > float(max_attendance):
            continue
            
        # Apply status filter
        if attendance_status == 'present' and days_present == 0:
            continue
        elif attendance_status == 'absent' and days_present > 0:
            continue
        
        # Add to students data
        students_data.append({
            'registration': registration,
            'days_present': days_present,
            'total_days': total_days_for_calculation,
            'attendance_percentage': attendance_percentage,
            'eligible_for_certificate': attendance_percentage >= 80,
        })
    
    # Sort by attendance percentage (highest first)
    students_data.sort(key=lambda x: x['attendance_percentage'], reverse=True)
    
    context = {
        'program': program,
        'total_days': total_days,
        'students': students_data,
        'threshold_percentage': 80,
        'date_filter': date_filter,
        'min_attendance': min_attendance,
        'max_attendance': max_attendance,
        'attendance_status': attendance_status,
    }
    
    return render(request, 'Expert/attendance_statistics.html', context)


def admin_program_analytics(request, program_id):
    try:
        program = get_object_or_404(DevelopmentProgram, id=program_id)
        
        # Get all registrations for this program
        registrations = Registration.objects.filter(program=program)
        
        # Get all materials uploaded for this program
        materials = ProgramMaterial.objects.filter(program=program).order_by('-upload_date')
        
        # Calculate attendance statistics for each student
        students_data = []
        for registration in registrations:
            student = registration.student
            
            # Get all attendance records for this student
            attendance_records = ProgramAttendance.objects.filter(
                program=program,
                student=student,
                is_present=True
            )
            
            # Calculate total possible days
            total_days = (program.end_date - program.start_date).days + 1
            today = timezone.now().date()
            
            # For ongoing or future programs, only count days that have passed
            if today < program.end_date:
                days_passed = min((today - program.start_date).days + 1, total_days)
                days_passed = max(days_passed, 1)  # Ensure at least 1 day for calculation
            else:
                days_passed = total_days
            
            # Calculate attendance percentage
            attendance_days = attendance_records.count()
            attendance_percentage = int((attendance_days / days_passed) * 100) if days_passed > 0 else 0
            
            students_data.append({
                'student': student,
                'registration_date': registration.registered_at,
                'attendance_percentage': attendance_percentage,
                'days_attended': attendance_days,
                'total_days': days_passed
            })
        
        context = {
            'program': program,
            'students_data': students_data,
            'materials': materials,
            'total_registrations': registrations.count(),
            'page_title': 'Program Analytics'
        }
        
        return render(request, 'admin/program_analytics.html', context)
        
    except Exception as e:
        messages.error(request, f'Error accessing program analytics: {str(e)}')
        return redirect('program_details_list')


def expert_program_analytics(request, program_id):
    try:
        # Instead of getting expert from session, make it optional
        expert_id = request.session.get('expert_id')
        expert = None
        if expert_id:
            expert = Expert.objects.get(id=expert_id)
        
        program = get_object_or_404(DevelopmentProgram, id=program_id)
        
        # If expert is available, verify they're the speaker
        if expert and program.speaker_name != expert.full_name:
            messages.error(request, "You don't have permission to view this program's analytics")
            return redirect('expert_programs')
        
        # Rest of your existing code...
        registrations = Registration.objects.filter(program=program)
        materials = ProgramMaterial.objects.filter(program=program).order_by('-upload_date')
        
        # Calculate attendance statistics for each student
        students_data = []
        for registration in registrations:
            student = registration.student
            
            # Get all attendance records for this student
            attendance_records = ProgramAttendance.objects.filter(
                program=program,
                student=student,
                is_present=True
            )
            
            # Calculate total possible days
            total_days = (program.end_date - program.start_date).days + 1
            today = timezone.now().date()
            
            # For ongoing or future programs, only count days that have passed
            if today < program.end_date:
                days_passed = min((today - program.start_date).days + 1, total_days)
                days_passed = max(days_passed, 1)  # Ensure at least 1 day for calculation
            else:
                days_passed = total_days
            
            # Calculate attendance percentage
            attendance_days = attendance_records.count()
            attendance_percentage = int((attendance_days / days_passed) * 100) if days_passed > 0 else 0
            
            students_data.append({
                'student': student,
                'registration_date': registration.registered_at,
                'attendance_percentage': attendance_percentage,
                'days_attended': attendance_days,
                'total_days': days_passed
            })
        
        context = {
            'program': program,
            'students_data': students_data,
            'materials': materials,
            'total_registrations': registrations.count(),
            'page_title': 'Program Analytics'
        }
        
        return render(request, 'expert/program_analytics.html', context)
        
    except Exception as e:
        messages.error(request, f'Error accessing program analytics: {str(e)}')
        return redirect('expert_programs')

@login_required
def program_certificate(request, program_id):
    try:
        program = get_object_or_404(DevelopmentProgram, id=program_id)
        student = request.user
        
        # Verify student is registered for this program
        registration = get_object_or_404(Registration, program=program, student=student)
        
        # Calculate attendance percentage
        attendance_records = ProgramAttendance.objects.filter(
            program=program,
            student=student,
            is_present=True
        )
        
        total_days = (program.end_date - program.start_date).days + 1
        attendance_days = attendance_records.count()
        attendance_percentage = int((attendance_days / total_days) * 100) if total_days > 0 else 0
        
        # Check if student is eligible for certificate
        if attendance_percentage < 80:
            messages.error(request, "You need at least 80% attendance to generate a certificate.")
            return redirect('student_programs')
        
        context = {
            'program': program,
            'student': student,
            'attendance_percentage': attendance_percentage,
        }
        
        return render(request, 'user/program_certificate.html', context)
        
    except Exception as e:
        messages.error(request, f"Error generating certificate: {str(e)}")
        return redirect('student_programs')

@login_required
def program_certificate_pdf(request, program_id):
    try:
        program = get_object_or_404(DevelopmentProgram, id=program_id)
        student = request.user
        
        # Verify student is registered for this program
        registration = get_object_or_404(Registration, program=program, student=student)
        
        # Calculate attendance percentage
        attendance_records = ProgramAttendance.objects.filter(
            program=program,
            student=student,
            is_present=True
        )
        
        total_days = (program.end_date - program.start_date).days + 1
        attendance_days = attendance_records.count()
        attendance_percentage = int((attendance_days / total_days) * 100) if total_days > 0 else 0
        
        # Check if student is eligible for certificate
        if attendance_percentage < 80:
            messages.error(request, "You need at least 80% attendance to generate a certificate.")
            return redirect('student_programs')
        
        # Generate PDF certificate
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        # List to hold PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Title'],
            fontSize=24,
            alignment=1,
            textColor=colors.HexColor('#2980b9'),
            spaceAfter=10
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=16,
            alignment=1,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=20
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=12,
            alignment=1,
            spaceAfter=10
        )
        
        name_style = ParagraphStyle(
            'Name',
            parent=styles['Normal'],
            fontSize=20,
            alignment=1,
            textColor=colors.HexColor('#2980b9'),
            spaceAfter=10
        )
        
        program_style = ParagraphStyle(
            'Program',
            parent=styles['Normal'],
            fontSize=16,
            alignment=1,
            textColor=colors.HexColor('#e67e22'),
            spaceAfter=20
        )
        
        # Certificate border
        def add_border(canvas, doc):
            canvas.saveState()
            width, height = landscape(A4)
            canvas.setStrokeColor(colors.HexColor('#2980b9'))
            canvas.setLineWidth(10)
            canvas.rect(20, 20, width-40, height-40, stroke=1, fill=0)
            
            # Add seal
            seal_path = os.path.join(settings.STATIC_ROOT, 'images', 'seal.png')
            if os.path.exists(seal_path):
                canvas.drawImage(seal_path, width-150, 50, width=100, height=100)
            
            # Add verification QR code
            verification_url = f"{request.build_absolute_uri('/')[:-1]}/verify-certificate/{program.id}/{student.id}/"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(verification_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code to temporary file
            qr_path = os.path.join(settings.MEDIA_ROOT, f'temp_qr_{student.id}_{program.id}.png')
            qr_img.save(qr_path)
            
            # Add QR code to PDF
            canvas.drawImage(qr_path, 50, 50, width=60, height=60)
            
            # Clean up temporary file
            os.remove(qr_path)
            
            canvas.restoreState()
        
        # Certificate content
        elements.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
        elements.append(Paragraph("Next Edge", subtitle_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("This is to certify that", normal_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(student.get_full_name() if hasattr(student, 'get_full_name') and callable(student.get_full_name) else student.username, name_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("has successfully completed the program", normal_style))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(program.title, program_style))
        elements.append(Spacer(1, 20))
        
        # Program details table
        data = [
            ["Program Duration:", f"{program.start_date.strftime('%B %d, %Y')} to {program.end_date.strftime('%B %d, %Y')}"],
            ["Attendance Percentage:", f"{attendance_percentage}%"],
            ["Program Coordinator:", program.speaker_name],
            ["Program Description:", program.description[:100] + "..." if len(program.description) > 100 else program.description]
        ]
        
        # Create table for program details
        table = Table(data, colWidths=[150, 350])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 40))
        
        # Signature line
        signature_data = [
            ["_______________________", ""],
            ["Program Coordinator", ""],
            [program.speaker_name, ""]
        ]
        
        signature_table = Table(signature_data, colWidths=[250, 250])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (0, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (0, 1), 12),
            ('FONTSIZE', (0, 2), (0, 2), 12),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(signature_table)
        
        # Build PDF
        doc.build(elements, onFirstPage=add_border, onLaterPages=add_border)
        
        # Get PDF from buffer
        pdf = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificate_{program.title}_{student.username}.pdf"'
        response.write(pdf)
        
        return response
        
    except Exception as e:
        messages.error(request, f"Error generating certificate PDF: {str(e)}")
        return redirect('student_programs')

def verify_certificate(request, program_id=None, student_id=None):
    """
    View to verify a certificate via QR code
    """
    if request.method == 'GET' and program_id and student_id:
        try:
            # Get the program and student
            program = get_object_or_404(DevelopmentProgram, id=program_id)
            student = get_object_or_404(CustomUser, id=student_id)
            
            # Verify student is registered for this program
            registration = get_object_or_404(Registration, program=program, student=student)
            
            # Calculate attendance percentage
            attendance_records = ProgramAttendance.objects.filter(
                program=program,
                student=student,
                is_present=True
            )
            
            total_days = (program.end_date - program.start_date).days + 1
            attendance_days = attendance_records.count()
            attendance_percentage = int((attendance_days / total_days) * 100) if total_days > 0 else 0
            
            # Check if student is eligible for certificate
            if attendance_percentage < 80:
                return JsonResponse({
                    'valid': False,
                    'message': 'Student did not meet the minimum attendance requirement'
                }, status=400)
            
            # Return certificate data
            return JsonResponse({
                'valid': True,
                'program': {
                    'title': program.title,
                    'start_date': program.start_date.strftime('%B %d, %Y'),
                    'end_date': program.end_date.strftime('%B %d, %Y'),
                    'speaker_name': program.speaker_name,
                    'description': program.description
                },
                'student': {
                    'username': student.username,
                    'email': student.email
                },
                'attendance_percentage': attendance_percentage,
                'issue_date': timezone.now().strftime('%B %d, %Y')
            })
            
        except Exception as e:
            return JsonResponse({
                'valid': False,
                'message': str(e)
            }, status=400)
    
    # If no parameters, show the verification page
    return render(request, 'user/verify_program_certificate.html')

def download_attendance_report(request, program_id):
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    
    # Get the program
    program = get_object_or_404(DevelopmentProgram, id=program_id)
    
    # Get program days
    program_days = ProgramDay.objects.filter(program=program)
    total_days = program_days.count()
    
    # Get filter parameters (same as in attendance_statistics)
    date_filter = request.GET.get('date')
    min_attendance = request.GET.get('min_attendance')
    max_attendance = request.GET.get('max_attendance')
    attendance_status = request.GET.get('status')
    
    # Get all registrations for this program
    registrations = Registration.objects.filter(program=program)
    
    # Calculate attendance statistics (similar to attendance_statistics)
    students_data = []
    for registration in registrations:
        # Count days present
        attendance_query = ProgramAttendance.objects.filter(
            program=program,
            registration=registration,
            present=True
        )
        
        # Apply date filter if provided
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                attendance_query = attendance_query.filter(date=filter_date)
                days_present = 1 if attendance_query.exists() else 0
                total_days_for_calculation = 1
            except ValueError:
                days_present = attendance_query.count()
                total_days_for_calculation = total_days
        else:
            days_present = attendance_query.count()
            total_days_for_calculation = total_days
        
        # Calculate attendance percentage (avoid division by zero)
        if total_days_for_calculation > 0:
            attendance_percentage = (days_present / total_days_for_calculation) * 100
        else:
            attendance_percentage = 0
        
        # Apply attendance percentage filters
        if min_attendance and attendance_percentage < float(min_attendance):
            continue
            
        if max_attendance and attendance_percentage > float(max_attendance):
            continue
            
        # Apply status filter
        if attendance_status == 'present' and days_present == 0:
            continue
        elif attendance_status == 'absent' and days_present > 0:
            continue
        
        # Add to students data
        students_data.append({
            'student_name': registration.student.username,
            'student_email': registration.student.email,
            'days_present': days_present,
            'total_days': total_days_for_calculation,
            'attendance_percentage': attendance_percentage,
            'eligible_for_certificate': 'Yes' if attendance_percentage >= 80 else 'No',
        })
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_report_{program.title}_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    # Write CSV data
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Email', 'Days Present', 'Total Days', 'Attendance %', 'Eligible for Certificate'])
    
    for student in students_data:
        writer.writerow([
            student['student_name'],
            student['student_email'],
            student['days_present'],
            student['total_days'],
            f"{student['attendance_percentage']:.1f}%",
            student['eligible_for_certificate']
        ])
    
    return response

def generate_attendance_report(request, program_id):
    import pandas as pd
    from django.http import HttpResponse
    from datetime import datetime
    from io import BytesIO
    
    # Get the program
    program = get_object_or_404(DevelopmentProgram, id=program_id)
    
    # Get program days
    program_days = ProgramDay.objects.filter(program=program)
    total_days = program_days.count()
    
    # Get filter parameters
    report_type = request.GET.get('report_type', 'all')
    date_filter = request.GET.get('date')
    min_attendance = request.GET.get('min_attendance')
    max_attendance = request.GET.get('max_attendance')
    attendance_status = request.GET.get('status')
    file_format = request.GET.get('format', 'excel')
    
    # Get all registrations for this program
    registrations = Registration.objects.filter(program=program)
    
    # Calculate attendance statistics
    students_data = []
    for registration in registrations:
        student = registration.student
        
        # Count days present
        attendance_query = ProgramAttendance.objects.filter(
            program=program,
            registration=registration,
            present=True
        )
        
        # Apply date filter if provided
        if date_filter:
            try:
                filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
                attendance_query = attendance_query.filter(date=filter_date)
                days_present = 1 if attendance_query.exists() else 0
                total_days_for_calculation = 1
            except ValueError:
                days_present = attendance_query.count()
                total_days_for_calculation = total_days
        else:
            days_present = attendance_query.count()
            total_days_for_calculation = total_days
        
        # Calculate attendance percentage (avoid division by zero)
        if total_days_for_calculation > 0:
            attendance_percentage = (days_present / total_days_for_calculation) * 100
        else:
            attendance_percentage = 0
        
        # Apply attendance percentage filters
        if min_attendance and attendance_percentage < float(min_attendance):
            continue
            
        if max_attendance and attendance_percentage > float(max_attendance):
            continue
            
        # Apply status filter
        if attendance_status == 'present' and days_present == 0:
            continue
        elif attendance_status == 'absent' and days_present > 0:
            continue
        
        # Apply report type filter
        if report_type == 'eligible' and attendance_percentage < 80:
            continue
        elif report_type == 'not_eligible' and attendance_percentage >= 80:
            continue
        elif report_type == 'perfect' and attendance_percentage < 100:
            continue
        elif report_type == 'critical' and attendance_percentage >= 60:
            continue
        
        # Get detailed attendance data if needed
        detailed_attendance = []
        if report_type == 'detailed':
            for day in program_days:
                attendance = ProgramAttendance.objects.filter(
                    program=program,
                    registration=registration,
                    date=day.date
                ).first()
                
                detailed_attendance.append({
                    'date': day.date.strftime('%Y-%m-%d'),
                    'status': 'Present' if attendance and attendance.present else 'Absent',
                    'time': attendance.time_marked.strftime('%H:%M:%S') if attendance and attendance.present else '-'
                })
        
        # Add to students data
        student_data = {
            'student_name': student.username,
            'student_email': student.email,
            'days_present': days_present,
            'total_days': total_days_for_calculation,
            'attendance_percentage': attendance_percentage,
            'eligible_for_certificate': 'Yes' if attendance_percentage >= 80 else 'No',
        }
        
        if report_type == 'detailed':
            student_data['detailed_attendance'] = detailed_attendance
            
        students_data.append(student_data)
    
    # Create appropriate response based on file format
    if file_format == 'excel':
        # Create Excel file
        output = BytesIO()
        
        # Create a pandas DataFrame
        if report_type == 'detailed':
            # For detailed report, create a different structure
            rows = []
            for student in students_data:
                for day in student['detailed_attendance']:
                    rows.append({
                        'Student Name': student['student_name'],
                        'Email': student['student_email'],
                        'Date': day['date'],
                        'Status': day['status'],
                        'Time Marked': day['time'],
                        'Overall Attendance': f"{student['attendance_percentage']:.1f}%",
                        'Eligible for Certificate': student['eligible_for_certificate']
                    })
            df = pd.DataFrame(rows)
        else:
            # For regular reports
            df = pd.DataFrame([{
                'Student Name': student['student_name'],
                'Email': student['student_email'],
                'Days Present': student['days_present'],
                'Total Days': student['total_days'],
                'Attendance %': f"{student['attendance_percentage']:.1f}%",
                'Eligible for Certificate': student['eligible_for_certificate']
            } for student in students_data])
        
        # Create Excel writer
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Attendance Report', index=False)
            
            # Get the xlsxwriter workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Attendance Report']
            
            # Add some formatting
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#D7E4BC',
                'border': 1
            })
            
            # Write the column headers with the defined format
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
            # Set column widths
            for i, col in enumerate(df.columns):
                column_width = max(df[col].astype(str).map(len).max(), len(col) + 2)
                worksheet.set_column(i, i, column_width)
        
        # Create response
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Generate filename based on report type
        report_type_names = {
            'all': 'All_Students',
            'eligible': 'Certificate_Eligible',
            'not_eligible': 'Not_Eligible',
            'perfect': 'Perfect_Attendance',
            'critical': 'Critical_Attendance',
            'detailed': 'Detailed_Attendance'
        }
        
        filename = f"{program.title}_{report_type_names.get(report_type, 'Attendance')}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    else:
        # Default to CSV if not Excel
        response = HttpResponse(content_type='text/csv')
        filename = f"{program.title}_Attendance_{datetime.now().strftime('%Y%m%d')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        import csv
        writer = csv.writer(response)
        
        if report_type == 'detailed':
            writer.writerow(['Student Name', 'Email', 'Date', 'Status', 'Time Marked', 'Overall Attendance', 'Eligible for Certificate'])
            for student in students_data:
                for day in student['detailed_attendance']:
                    writer.writerow([
                        student['student_name'],
                        student['student_email'],
                        day['date'],
                        day['status'],
                        day['time'],
                        f"{student['attendance_percentage']:.1f}%",
                        student['eligible_for_certificate']
                    ])
        else:
            writer.writerow(['Student Name', 'Email', 'Days Present', 'Total Days', 'Attendance %', 'Eligible for Certificate'])
            for student in students_data:
                writer.writerow([
                    student['student_name'],
                    student['student_email'],
                    student['days_present'],
                    student['total_days'],
                    f"{student['attendance_percentage']:.1f}%",
                    student['eligible_for_certificate']
                ])
        
        return response

def download_daily_attendance_report(request, program_id):
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    
    # Get the program
    program = get_object_or_404(DevelopmentProgram, id=program_id)
    
    # Get date parameter
    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # Get search filter
    search_filter = request.GET.get('search', '')
    
    # Get report type - always get format parameter but ignore it
    report_type = request.GET.get('report_type', 'all')
    # Just get the format parameter to avoid errors, but we won't use it
    _ = request.GET.get('format', 'csv')  
    
    # Get all students registered for this program
    students = CustomUser.objects.filter(program_registrations__program=program).distinct()
    
    # Prepare student data
    students_data = []
    for student in students:
        # Apply search filter if provided
        if search_filter and search_filter.lower() not in student.username.lower() and search_filter.lower() not in student.email.lower():
            continue
            
        # Check attendance for the selected date
        attendance = ProgramAttendance.objects.filter(
            program=program,
            student=student,
            date=selected_date
        ).first()
        
        # Check if the attendance exists and if the student was present
        # Adjust the field name based on your model structure
        is_present = False
        attendance_time = "-"
        
        if attendance:
            # Try different field names based on your model
            if hasattr(attendance, 'is_present'):
                is_present = attendance.is_present
            elif hasattr(attendance, 'present'):
                is_present = attendance.present
                
            if is_present and hasattr(attendance, 'time_marked') and attendance.time_marked:
                attendance_time = attendance.time_marked.strftime('%I:%M %p')
        
        attendance_status = "Present" if is_present else "Absent"
        
        # Apply report type filter
        if report_type == 'present' and attendance_status != "Present":
            continue
        elif report_type == 'absent' and attendance_status != "Absent":
            continue
        
        students_data.append({
            'name': student.username,
            'email': student.email,
            'status': attendance_status,
            'time_marked': attendance_time
        })
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    
    # Generate filename based on report type
    report_type_names = {
        'all': 'All_Students',
        'present': 'Present_Students',
        'absent': 'Absent_Students'
    }
    
    filename = f"{program.title}_{report_type_names.get(report_type, 'Attendance')}_{selected_date.strftime('%Y%m%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Write CSV data
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Email', 'Status', 'Time Marked'])
    
    for student in students_data:
        writer.writerow([
            student['name'],
            student['email'],
            student['status'],
            student['time_marked']
        ])
    
    return response

@never_cache
def all_programs(request):
    today = timezone.now().date()
    
    # Get upcoming programs
    upcoming_programs = DevelopmentProgram.objects.filter(
        start_date__gt=today,
        is_active=True,
        status_program='approved'
    ).order_by('start_date')

    # Get ongoing programs
    ongoing_programs = DevelopmentProgram.objects.filter(
        start_date__lte=today,
        end_date__gte=today,
        is_active=True,
        status_program='approved'
    ).order_by('start_date')

    # Get past programs
    past_programs = DevelopmentProgram.objects.filter(
        end_date__lt=today,
        is_active=True,
        status_program='approved'
    ).order_by('-end_date')

    # Add registration status and available seats for each program
    for program in upcoming_programs:
        registrations_count = Registration.objects.filter(program=program).count()
        program.available_seats = program.max_participants - registrations_count
        program.is_registered = Registration.objects.filter(
            program=program,
            student=request.user
        ).exists()
    
    context = {
        'upcoming_programs': upcoming_programs,
        'ongoing_programs': ongoing_programs,
        'past_programs': past_programs,
    }

    return render(request, 'user/development_programs.html', context)

