from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

from api.views import *

urlpatterns = [
    # React
    re_path(r".*", TemplateView.as_view(template_name="index.html")),
    path("googlelogin/", GoogleLogin.as_view()),
    path("googleconnect/", GoogleConnect.as_view()),
    path("accounts/", include("allauth.urls")),
    path("rest-auth/", include("rest_auth.urls")),
    path("rest-auth/registration/", include("rest_auth.registration.urls")),
    # Django
    path("api/library/", LibraryListView.as_view()),
    path("api/language/", LanguageListView.as_view()),
    path("api/day/", DayListView.as_view()),
    path("api/time/", TimeListView.as_view()),
    path("api/available/", AvailableAppointmentTimeList.as_view()),
    path("api/myappointments/", MyAppointmentListView.as_view()),
    path("api/booking/", book_appointment),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("admin/", admin.site.urls),
]
