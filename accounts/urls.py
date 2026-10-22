"""
URL patterns for accounts app.
"""

from django.urls import path
from accounts import views

urlpatterns = [
    path("", views.LandingView.as_view(), name="landing"),
    path("kirish/", views.DemoLoginView.as_view(), name="demo_login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("accounts/profile/", views.ProfileView.as_view(), name="profile"),
]
