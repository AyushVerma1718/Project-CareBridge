from django.contrib import admin
from django.urls import path, include
from frontend_views import login_page, dashboard_page

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("records.urls")),
    path("", login_page, name="login"),
    path("dashboard/", dashboard_page, name="dashboard"),
]
