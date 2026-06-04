"""
config/urls.py
--------------
Ana URL yönlendirici.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
import os

from apps.patients.urls import admission_urlpatterns, report_urlpatterns


@login_required
def dashboard_view(request):
    html_path = os.path.join(settings.BASE_DIR.parent, 'dashboard.html')
    return FileResponse(open(html_path, 'rb'), content_type='text/html')


urlpatterns = [
    # Dashboard Ana Sayfa (giriş zorunlu)
    path('', dashboard_view, name='dashboard'),

    # Giriş / Çıkış
    path('login/',  auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Django Admin
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/auth/',       include('apps.accounts.urls')),
    path('api/v1/icd10/',      include('apps.icd10.urls')),
    path('api/v1/patients/',   include('apps.patients.urls')),
    path('api/v1/admissions/', include(admission_urlpatterns)),
    path('api/v1/reports/',    include(report_urlpatterns)),
    path('api/v1/treatments/', include('apps.treatments.urls')),
    path('api/v1/analysis/',   include('apps.analysis.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
