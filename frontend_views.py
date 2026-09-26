"""
frontend_views.py
-----------------
Simple Django views that serve the HTML frontend templates.
"""
from django.shortcuts import render, redirect


def login_page(request):
    """Serve the login page. If already authenticated, go to dashboard."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'login.html')


def dashboard_page(request):
    """Serve the dashboard. Redirect to login if not authenticated."""
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'dashboard.html')
