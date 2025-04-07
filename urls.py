from django.urls import path, include

urlpatterns = [
    # ... other paths ...
    path('', include('user.urls')),  # Make sure this is included
] 