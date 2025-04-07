from django.urls import path, include

urlpatterns = [
    # ... other patterns ...
    path('user/', include('user.urls')),
] 