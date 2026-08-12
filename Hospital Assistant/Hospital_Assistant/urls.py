"""
Definition of urls for Hospital_Assistant.
"""

from datetime import datetime
from django.urls import path
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from app import forms, views


urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('staff/', views.staff_profile_list, name='staff_profile_list'),
    path('staff/register/', views.staff_register, name='staff_register'),
    path('staff/<int:pk>/edit/', views.staff_update, name='staff_update'),
    path('staff/me/', views.my_staff_profile_update, name='my_staff_profile_update'),
    path('nurse/dashboard/', views.nurse_dashboard, name='nurse_dashboard'),
    path('nurse/patients/', views.nurse_patient_list, name='nurse_patient_list'),
    path('nurse/patients/create/', views.nurse_patient_create, name='nurse_patient_create'),
    path('nurse/patient/<int:patient_id>/', views.nurse_patient_detail, name='nurse_patient_detail'),
    path('nurse/patient/<int:patient_id>/vitals/add/', views.nurse_vital_signs_create, name='nurse_vital_signs_create'),
    path('nurse/patient/<int:patient_id>/medication/add/', views.nurse_medication_create, name='nurse_medication_create'),

    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/register/', views.patient_create, name='patient_create'),
    path('patients/autocomplete/', views.patient_autocomplete, name='patient_autocomplete'),
    path('patients/<int:pk>/edit/', views.patient_update, name='patient_update'),
    
    path('patients/<int:patient_id>/appointments/', views.patient_appointments, name='patient_appointments'),
    path('encounters/', views.encounter_list, name='encounter_list'),
    path('encounters/create/', views.encounter_create, name='encounter_create'),
    path('encounters/<int:pk>/edit/', views.encounter_update, name='encounter_update'),
    path('next-of-kin/', views.next_of_kin_patient_list, name='next_of_kin_patient_list'),
    path('next-of-kin/patient/<int:patient_id>/', views.next_of_kin_list, name='next_of_kin_list'),
    path('next-of-kin/patient/<int:patient_id>/add/', views.next_of_kin_create, name='next_of_kin_create'),
    path('next-of-kin/<int:pk>/edit/', views.next_of_kin_update, name='next_of_kin_update'),
    path('ai/', views.ai_encounter_list, name='ai_encounter_list'),
    path('ai/encounter/<int:encounter_id>/', views.ai_suggestions, name='ai_suggestions'),
    path('ai/review/<str:suggestion_type>/<int:pk>/', views.ai_review_suggestion, name='ai_review_suggestion'),
    path('login/',
         LoginView.as_view
         (
             template_name='app/login.html',
             authentication_form=forms.BootstrapAuthenticationForm,
             extra_context=
             {
                 'title': 'Log in',
                 'year' : datetime.now().year,
             }
         ),
         name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('admin/', admin.site.urls),
]
