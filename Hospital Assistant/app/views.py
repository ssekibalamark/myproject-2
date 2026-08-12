"""Definition of views."""

from datetime import datetime
import profile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .forms import (
    AIDiagnosisSuggestionForm,
    AILabTestSuggestionForm,
    AIMedicationSuggestionForm,
    AIReviewForm,
    DoctorEncounterForm,
    EncounterForm,
    HospitalStaffUpdateForm,
    ICTStaffRegistrationForm,
    LabTestOrderForm,
    LabTestResultForm,
    NextOfKinForm,
    PathologistFindingForm,
    PatientRegistrationForm,
    NextOfKinFormSet,
    PrescribedMedicationForm,
    RadiographyStudyForm,
    VitalSignsForm,
)
from .models import (
    AIDiagnosisSuggestion,
    AILabTestSuggestion,
    AIMedicationSuggestion,
    Encounter,
    LabTestCategory,
    LabTestOrder,
    LabTestResult,
    NextOfKin,
    PathologistFinding,
    Patient,
    PrescribedMedication,
    RadiographyStudy,
    StaffProfile,
    StaffRole,
    VitalSigns,
)

def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/index.html',
        {
            'title':'Home Page',
            'year':datetime.now().year,
        }
    )

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/contact.html',
        {
            'title':'Contact',
            'message':'Your contact page.',
            'year':datetime.now().year,
        }
    )

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/about.html',
        {
            'title':'About',
            'message':'Your application description page.',
            'year':datetime.now().year,
        }
    )


def _require_role(request, allowed_roles):
   """Require that the user has a staff profile with one of the allowed roles.
    Superusers must also have a valid staff profile – no unconditional bypass.
    """
   if not request.user.is_authenticated:
        raise PermissionDenied

   staff_profile = getattr(request.user, "staff_profile", None)
   if staff_profile is None:
        raise PermissionDenied("You do not have a staff profile.")

   if staff_profile.role not in allowed_roles:
        raise PermissionDenied("You do not have permission for this action.")

   return staff_profile
def _require_medical_staff(request):
    
    """Require that the user has a clinical staff role (not ICT_ADMIN)."""
    if not request.user.is_authenticated:
        raise PermissionDenied

    staff_profile = getattr(request.user, "staff_profile", None)
    if staff_profile is None:
        raise PermissionDenied("You do not have a staff profile.")

    # Define the set of medical (non‑ICT) roles – all roles except ICT_ADMIN
    medical_roles = {role for role, _ in StaffRole.choices if role != StaffRole.ICT_ADMIN}

    if staff_profile.role not in medical_roles:
        raise PermissionDenied("Only medical staff can access patient data.")

    return staff_profile

@login_required
def staff_profile_list(request):
    """List staff profiles for ICT Admin management."""
    _require_role(request, {"ICT_ADMIN"})
    staff_profiles = StaffProfile.objects.select_related("user").all()
    return render(
        request,
        "app/staff_profile_list.html",
        {
            "title": "Staff Management",
            "year": datetime.now().year,
            "staff_profiles": staff_profiles,
        },
    )


@login_required
def staff_register(request):
    """Register a hospital staff profile (ICT Admin only)."""
    _require_role(request, {"ICT_ADMIN"})

    if request.method == "POST":
        form = ICTStaffRegistrationForm(request.POST)
        if form.is_valid():
            staff_profile = form.save(commit=False)
            staff_profile.registered_by = request.user
            staff_profile.registered_at = timezone.now()
            staff_profile.save()
            messages.success(request, "Staff profile registered successfully.")
            return redirect("staff_profile_list")
    else:
        form = ICTStaffRegistrationForm()

    return render(
        request,
        "app/staff_profile_form.html",
        {
            "title": "Register Staff Profile",
            "year": datetime.now().year,
            "form": form,
            "submit_label": "Register Staff",
        },
    )


@login_required
def staff_update(request, pk):
    """Update any staff profile details (ICT Admin only)."""
    _require_role(request, {"ICT_ADMIN"})
    staff_profile = get_object_or_404(StaffProfile, pk=pk)

    if request.method == "POST":
        form = HospitalStaffUpdateForm(request.POST, instance=staff_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff profile updated successfully.")
            return redirect("staff_profile_list")
    else:
        form = HospitalStaffUpdateForm(instance=staff_profile)

    return render(
        request,
        "app/staff_profile_form.html",
        {
            "title": "Update Staff Profile",
            "year": datetime.now().year,
            "form": form,
            "submit_label": "Save Changes",
        },
    )


@login_required
def my_staff_profile_update(request):
    """Allow authenticated hospital staff to update their own profile details."""
    staff_profile = _require_role(
        request,
        {
            "ICT_ADMIN",
            "DOCTOR",
            "SPECIALIST",
            "NURSE",
            "PHARMACIST",
            "PATHOLOGIST",
            "LAB_TECH",
            "RADIOGRAPHER",
            "RECEPTIONIST",
        },
    )

    if request.method == "POST":
        form = HospitalStaffUpdateForm(request.POST, instance=staff_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("my_staff_profile_update")
    else:
        form = HospitalStaffUpdateForm(instance=staff_profile)

    return render(
        request,
        "app/staff_profile_form.html",
        {
            "title": "My Staff Profile",
            "year": datetime.now().year,
            "form": form,
            "submit_label": "Update My Profile",
        },
    )


@login_required
def patient_list(request):
    """List patient profiles."""
    _require_medical_staff(request)
    patients = Patient.objects.all()
    # Provide a list of hospital departments (from staff profiles) for UI/context
    departments = (
        StaffProfile.objects.order_by("department")
        .values_list("department", flat=True)
        .distinct()
    )
    return render(
        request,
        "app/patient_list.html",
        {
            "title": "Patients",
            "year": datetime.now().year,
            "patients": patients,
            "departments": departments,
        },
    )


@login_required
def patient_create(request):
     _require_medical_staff(request)
     if request.method == 'POST':
        patient_form = PatientRegistrationForm(request.POST)
        nok_formset = NextOfKinFormSet(request.POST, instance=Patient())  # empty instance
        if patient_form.is_valid() and nok_formset.is_valid():
            patient = patient_form.save()
            nok_forms = nok_formset.save(commit=False)
            for nok_form in nok_forms:
                nok_form.patient = patient
                nok_form.save()
            messages.success(request, "Patient and next‑of‑kin records created.")
            return redirect('patient_list')
     else:
        patient_form = PatientRegistrationForm()
        nok_formset = NextOfKinFormSet(instance=Patient())
     return render(request, 'app/patient_form.html', {
        'form': patient_form,
        'nok_formset': nok_formset,
        'title': 'Register Patient',
        'submit_label': 'Create Patient',
    })


@require_GET
def patient_autocomplete(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    patients = Patient.objects.filter(patient_number__icontains=q)[:10]
    data = [{
        "id": p.id, 
        "text": f"{p.patient_number} - {p.first_name} {p.last_name}",
        'patient_number': p.patient_number } 
            for p in patients]
    return JsonResponse(data, safe=False)


@login_required
def patient_update(request, pk):
    """Update an existing patient profile."""
    _require_medical_staff(request)
    patient = get_object_or_404(Patient, pk=pk)

    if request.method == "POST":
        form = PatientRegistrationForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "Patient profile updated successfully.")
            return redirect("patient_list")
    else:
        form = PatientRegistrationForm(instance=patient)

    return render(
        request,
        "app/patient_form.html",
        {
            "title": f"Update Patient - {patient.patient_number}",
            "year": datetime.now().year,
            "form": form,
            "submit_label": "Save Changes",
        },
    )
@login_required
def patient_appointments(request, patient_id):
    """List encounters for a specific patient."""
    _require_medical_staff(request)
    patient = get_object_or_404(Patient, pk=patient_id)
    appointments = patient.encounters.filter(status=Encounter.EncounterStatus.SCHEDULED).order_by("started_at")
    is_receptionist = request.user.staff_profile.role == StaffRole.RECEPTIONIST
    return render(
        request,
        "app/patient_appointments.html",
        {
            "title": f"Appointments - {patient.first_name} {patient.last_name}",
            "year": datetime.now().year,
            "patient": patient,
            "appointments": appointments,
            "is_receptionist": is_receptionist,
            "patient_id": patient.id,
        },
    )


@login_required
def encounter_list(request):
   
    _require_medical_staff(request)
    encounters = Encounter.objects.select_related('patient', 'attending_doctor', 'specialist_reviewer').all()
    
    return render(request, 'app/encounter_list.html', {
        'encounters': encounters,
        
        'title': 'Encounters',
        'year': datetime.now().year,
    })


@login_required
def encounter_create(request):
    staff_profile = _require_medical_staff(request)

    # Auto-fill the attending doctor with the logged-in doctor/specialist.
    initial = {}
    if staff_profile.role in {StaffRole.DOCTOR, StaffRole.SPECIALIST}:
        initial["attending_doctor"] = staff_profile

    if request.method == 'POST':
        form = EncounterForm(request.POST)
        if form.is_valid():
            encounter = form.save()
            messages.success(request, "Encounter created successfully.")
            return redirect('encounter_list')
    else:
        form = EncounterForm(initial=initial)

    return render(request, 'app/encounter_form.html', {
        'form': form,
        'title': 'Schedule Appointment',
        'submit_label': 'Schedule',
        'year': datetime.now().year,
    })
   


@login_required
def encounter_update(request, pk):
    _require_medical_staff(request)
    encounter = get_object_or_404(Encounter, pk=pk)
    

    # Receptionists can only edit scheduled/cancelled appointments
    

    if request.method == 'POST':
        
        
        form = EncounterForm(request.POST, instance=encounter)
        if form.is_valid():
            form.save()
            messages.success(request, "Encounter updated successfully.")
            return redirect('encounter_list')
    else:
       
         form = EncounterForm(instance=encounter)

    return render(request, 'app/encounter_form.html', {
        'form': form,
       
        'title': 'Update Appointment',
        'submit_label': 'Save Changes',
        'year': datetime.now().year,
    })


@login_required
def next_of_kin_patient_list(request):
    """List patients for next-of-kin management."""
    _require_medical_staff(request)
    patients = Patient.objects.all()
    return render(
        request,
        "app/next_of_kin_patient_list.html",
        {
            "title": "Patients - Next of Kin",
            "year": datetime.now().year,
            "patients": patients,
        },
    )


@login_required
def next_of_kin_list(request, patient_id):
    """List next-of-kin contacts for a selected patient."""
    _require_medical_staff(request)
    patient = get_object_or_404(Patient, pk=patient_id)
    next_of_kins = NextOfKin.objects.filter(patient=patient).order_by("slot")
    return render(
        request,
        "app/next_of_kin_list.html",
        {
            "title": f"Next of Kin - {patient.patient_number}",
            "year": datetime.now().year,
            "patient": patient,
            "next_of_kins": next_of_kins,
        },
    )


@login_required
def next_of_kin_create(request, patient_id):
    """Create a next-of-kin contact for a selected patient."""
    _require_role(
        request,
        {
            "ICT_ADMIN",
            "DOCTOR",
            "SPECIALIST",
            "NURSE",
            "PHARMACIST",
            "PATHOLOGIST",
            "LAB_TECH",
            "RADIOGRAPHER",
            "RECEPTIONIST",
        },
    )
    patient = get_object_or_404(Patient, pk=patient_id)

    if request.method == "POST":
        form = NextOfKinForm(request.POST, patient=patient)
        if form.is_valid():
            next_of_kin = form.save(commit=False)
            next_of_kin.patient = patient
            next_of_kin.save()
            messages.success(request, "Next-of-kin contact added successfully.")
            return redirect("next_of_kin_list", patient_id=patient.id)
    else:
        form = NextOfKinForm(patient=patient)

    return render(
        request,
        "app/next_of_kin_form.html",
        {
            "title": f"Add Next of Kin - {patient.patient_number}",
            "year": datetime.now().year,
            "patient": patient,
            "form": form,
            "submit_label": "Add Next of Kin",
        },
    )


@login_required
def next_of_kin_update(request, pk):
    """Update an existing next-of-kin contact."""
    _require_role(
        request,
        {
            "ICT_ADMIN",
            "DOCTOR",
            "SPECIALIST",
            "NURSE",
            "PHARMACIST",
            "PATHOLOGIST",
            "LAB_TECH",
            "RADIOGRAPHER",
            "RECEPTIONIST",
        },
    )
    next_of_kin = get_object_or_404(NextOfKin, pk=pk)
    patient = next_of_kin.patient

    if request.method == "POST":
        form = NextOfKinForm(request.POST, instance=next_of_kin, patient=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "Next-of-kin contact updated successfully.")
            return redirect("next_of_kin_list", patient_id=patient.id)
    else:
        form = NextOfKinForm(instance=next_of_kin, patient=patient)

    return render(
        request,
        "app/next_of_kin_form.html",
        {
            "title": f"Update Next of Kin - {patient.patient_number}",
            "year": datetime.now().year,
            "patient": patient,
            "form": form,
            "submit_label": "Save Changes",
        },
    )


@login_required
def ai_encounter_list(request):
    """List encounters available for AI suggestion workflow."""
    _require_role(request, {"DOCTOR", "SPECIALIST", "ICT_ADMIN"})
    encounters = Encounter.objects.select_related("patient").all()[:50]
    return render(
        request,
        "app/ai_encounters.html",
        {
            "title": "AI Workflow",
            "year": datetime.now().year,
            "encounters": encounters,
        },
    )


@login_required
def ai_suggestions(request, encounter_id):
    """Create AI diagnosis, lab, and medication suggestions for an encounter."""
    _require_role(request, {"DOCTOR", "SPECIALIST", "ICT_ADMIN"})
    encounter = get_object_or_404(Encounter, pk=encounter_id)

    diagnosis_form = AIDiagnosisSuggestionForm(prefix="diag")
    lab_form = AILabTestSuggestionForm(prefix="lab")
    medication_form = AIMedicationSuggestionForm(prefix="med")

    if request.method == "POST":
        if "create_diagnosis" in request.POST:
            diagnosis_form = AIDiagnosisSuggestionForm(request.POST, prefix="diag")
            if diagnosis_form.is_valid():
                suggestion = diagnosis_form.save(commit=False)
                suggestion.encounter = encounter
                suggestion.save()
                messages.success(request, "Diagnosis suggestion created.")
                return redirect("ai_suggestions", encounter_id=encounter.id)

        if "create_lab" in request.POST:
            lab_form = AILabTestSuggestionForm(request.POST, prefix="lab")
            if lab_form.is_valid():
                suggestion = lab_form.save(commit=False)
                suggestion.encounter = encounter
                suggestion.save()
                messages.success(request, "Lab test suggestion created.")
                return redirect("ai_suggestions", encounter_id=encounter.id)

        if "create_medication" in request.POST:
            medication_form = AIMedicationSuggestionForm(request.POST, prefix="med")
            if medication_form.is_valid():
                suggestion = medication_form.save(commit=False)
                suggestion.encounter = encounter
                suggestion.save()
                messages.success(request, "Medication suggestion created.")
                return redirect("ai_suggestions", encounter_id=encounter.id)

    return render(
        request,
        "app/ai_suggestions.html",
        {
            "title": f"AI Suggestions - {encounter.patient.patient_number}",
            "year": datetime.now().year,
            "encounter": encounter,
            "diagnosis_form": diagnosis_form,
            "lab_form": lab_form,
            "medication_form": medication_form,
            "diagnosis_items": AIDiagnosisSuggestion.objects.filter(encounter=encounter),
            "lab_items": AILabTestSuggestion.objects.filter(encounter=encounter),
            "medication_items": AIMedicationSuggestion.objects.filter(encounter=encounter),
        },
    )


@login_required
def ai_review_suggestion(request, suggestion_type, pk):
    """Specialist review endpoint for AI recommendation items."""
    reviewer = _require_role(request, {"SPECIALIST", "ICT_ADMIN"})

    model_map = {
        "diagnosis": AIDiagnosisSuggestion,
        "lab": AILabTestSuggestion,
        "medication": AIMedicationSuggestion,
    }
    model_class = model_map.get(suggestion_type)
    if model_class is None:
        raise PermissionDenied("Unsupported suggestion type.")

    suggestion = get_object_or_404(model_class, pk=pk)

    if request.method == "POST":
        form = AIReviewForm(request.POST)
        if form.is_valid():
            suggestion.review_status = form.cleaned_data["review_status"]
            suggestion.reviewer_remarks = form.cleaned_data["reviewer_remarks"]

            if suggestion.review_status == "PENDING":
                suggestion.reviewed_by = None
                suggestion.reviewed_at = None
            else:
                suggestion.reviewed_by = reviewer
                suggestion.reviewed_at = timezone.now()

            suggestion.full_clean()
            suggestion.save()
            messages.success(request, "AI suggestion review updated.")
            return redirect("ai_suggestions", encounter_id=suggestion.encounter_id)
    else:
        form = AIReviewForm(
            initial={
                "review_status": suggestion.review_status,
                "reviewer_remarks": suggestion.reviewer_remarks,
            }
        )

    return render(
        request,
        "app/ai_review.html",
        {
            "title": "Review AI Suggestion",
            "year": datetime.now().year,
            "suggestion": suggestion,
            "suggestion_type": suggestion_type,
            "form": form,
        },
    )


def _patient_test_summary(patient):
    """Return a test-status summary for a patient.

    States:
      - "none":     no tests have been requested.
      - "awaiting": at least one requested test is still pending/in progress.
      - "ready":    tests were requested and all are now completed.
    """
    orders = LabTestOrder.objects.filter(patient=patient)
    total = orders.count()
    completed = orders.filter(status=LabTestOrder.OrderStatus.COMPLETED).count()
    pending = total - completed

    if total == 0:
        return {"state": "none", "label": "No Tests", "total": 0, "pending": 0, "completed": 0}

    if pending > 0:
        return {
            "state": "awaiting",
            "label": "Awaiting Tests",
            "total": total,
            "pending": pending,
            "completed": completed,
        }

    return {
        "state": "ready",
        "label": "Tests Ready",
        "total": total,
        "pending": 0,
        "completed": completed,
    }


def _patient_medication_summary(patient):
    """Summarize the patient's medication status and where medication is received.

    Returns a dict with:
      - on_medication: True when the patient has any active prescription.
      - setting: "hospital" (inpatient), "home" (outpatient/repeat), or "none".
      - setting_label: human-readable setting text.
      - active_count: number of currently active prescriptions.
      - expected_stay: expected stay text for inpatients (from duration/end date).
    """
    today = timezone.now().date()
    medications = patient.medications.all()

    active = [
        med for med in medications
        if med.end_date is None or med.end_date >= today
    ]
    inpatient_meds = [
        med for med in active
        if med.prescription_type == "INPATIENT"
    ]
    outpatient_meds = [
        med for med in active
        if med.prescription_type in {"OUTPATIENT", "REPEAT"}
    ]

    if inpatient_meds:
        setting = "hospital"
        setting_label = "Hospital Bed (Inpatient)"
    elif outpatient_meds:
        setting = "home"
        setting_label = "Home (Outpatient)"
    elif active:
        setting = "other"
        setting_label = "On Medication"
    else:
        setting = "none"
        setting_label = "Not on Medication"

    expected_stay = None
    if inpatient_meds:
        durations = [med.duration for med in inpatient_meds if med.duration]
        end_dates = [med.end_date for med in inpatient_meds if med.end_date]
        if durations:
            expected_stay = ", ".join(durations)
        elif end_dates:
            expected_stay = f"until {max(end_dates)}"

    return {
        "on_medication": bool(active),
        "setting": setting,
        "setting_label": setting_label,
        "active_count": len(active),
        "expected_stay": expected_stay,
    }


@login_required
def role_dashboard(request):
    """Redirect an authenticated user to the dashboard for their staff role."""
    profile = getattr(request.user, "staff_profile", None)
    if profile is None:
        return redirect("home")

    role_dashboard_map = {
        StaffRole.NURSE: "nurse_dashboard",
        StaffRole.DOCTOR: "doctor_dashboard",
        StaffRole.SPECIALIST: "doctor_dashboard",
        StaffRole.ICT_ADMIN: "doctor_dashboard",
        StaffRole.PATHOLOGIST: "pathologist_dashboard",
        StaffRole.LAB_TECH: "lab_tech_dashboard",
        StaffRole.RADIOGRAPHER: "radiography_dashboard",
    }
    return redirect(role_dashboard_map.get(profile.role, "home"))


@login_required
def doctor_dashboard(request):
    """Doctor dashboard: queue of patients awaiting encounter (first booked first)."""
    _require_role(request, {StaffRole.DOCTOR, StaffRole.SPECIALIST, StaffRole.ICT_ADMIN})

    # Patients awaiting encounter: encounters not yet completed/cancelled/done,
    # ordered by start time (earliest booking first). One row per encounter.
    terminal_statuses = [
        Encounter.EncounterStatus.COMPLETED,
        Encounter.EncounterStatus.CANCELLED,
        Encounter.EncounterStatus.DONE,
    ]
    awaiting_encounters = (
        Encounter.objects.exclude(status__in=terminal_statuses)
        .select_related("patient", "attending_doctor")
        .order_by("started_at")
    )

    # Build a lightweight list with a test-status summary per encounter patient.
    queue = []
    for enc in awaiting_encounters:
        queue.append({
            "encounter": enc,
            "test_status": _patient_test_summary(enc.patient),
        })

    # Summary counts for the dashboard header.
    total_awaiting = len(queue)
    awaiting_tests_count = sum(1 for item in queue if item["test_status"]["state"] == "awaiting")
    tests_ready_count = sum(1 for item in queue if item["test_status"]["state"] == "ready")

    return render(request, "app/doctor_dashboard.html", {
        "title": "Doctor Dashboard",
        "queue": queue,
        "total_awaiting": total_awaiting,
        "awaiting_tests_count": awaiting_tests_count,
        "tests_ready_count": tests_ready_count,
    })


@login_required
def doctor_patient_list(request):
    """Doctor's patient list: patients awaiting encounter, ordered by booking time."""
    _require_role(request, {StaffRole.DOCTOR, StaffRole.SPECIALIST, StaffRole.ICT_ADMIN})

    # Patients with an encounter not yet completed, ordered by earliest booking first.
    terminal_statuses = [
        Encounter.EncounterStatus.COMPLETED,
        Encounter.EncounterStatus.CANCELLED,
        Encounter.EncounterStatus.DONE,
    ]
    awaiting_encounters = (
        Encounter.objects.exclude(status__in=terminal_statuses)
        .select_related("patient")
        .order_by("started_at")
    )

    patients = []
    seen_ids = set()
    for enc in awaiting_encounters:
        patient = enc.patient
        if patient.id in seen_ids:
            continue
        seen_ids.add(patient.id)
        patients.append({
            "patient": patient,
            "encounter": enc,
            "test_status": _patient_test_summary(patient),
        })

    return render(request, "app/doctor_patient_list.html", {
        "title": "Patients Awaiting Encounter",
        "patients": patients,
    })


@login_required
def doctor_all_patients(request):
    """Doctor's full patient list: every patient, waiting or not."""
    _require_role(request, {StaffRole.DOCTOR, StaffRole.SPECIALIST, StaffRole.ICT_ADMIN})

    terminal_statuses = [
        Encounter.EncounterStatus.COMPLETED,
        Encounter.EncounterStatus.CANCELLED,
        Encounter.EncounterStatus.DONE,
    ]

    # Optional free-text search by patient number or name.
    query = (request.GET.get("q") or "").strip()
    patients = Patient.objects.all().order_by("patient_number")
    if query:
        patients = patients.filter(
            Q(patient_number__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone_number__icontains=query)
        )

    patient_rows = []
    for patient in patients:
        is_waiting = patient.encounters.exclude(status__in=terminal_statuses).exists()
        patient_rows.append({
            "patient": patient,
            "is_waiting": is_waiting,
            "test_status": _patient_test_summary(patient),
        })

    return render(request, "app/doctor_all_patients.html", {
        "title": "All Patients",
        "patients": patient_rows,
        "query": query,
        "total_count": len(patient_rows),
        "waiting_count": sum(1 for row in patient_rows if row["is_waiting"]),
    })


def _doctor_patient_detail_context(patient, staff_profile, request_form=None, encounter_form=None, prescription_form=None):
    """Build the shared context for the doctor's patient detail page."""
    if request_form is None:
        request_form = LabTestOrderForm(patient=patient)

    if encounter_form is None:
        encounter_initial = {}
        if staff_profile.role in {StaffRole.DOCTOR, StaffRole.SPECIALIST}:
            encounter_initial["attending_doctor"] = staff_profile
        encounter_form = DoctorEncounterForm(initial=encounter_initial)

    if prescription_form is None:
        prescription_form = PrescribedMedicationForm()

    return {
        "title": f"Patient - {patient.patient_number}",
        "patient": patient,
        "test_orders": (
            LabTestOrder.objects.filter(patient=patient)
            .select_related("encounter", "ordered_by")
            .prefetch_related("pathologist_finding", "radiography_study", "lab_results")
            .order_by("-ordered_at")
        ),
        "test_summary": _patient_test_summary(patient),
        "medication_summary": _patient_medication_summary(patient),
        "request_form": request_form,
        "encounter_form": encounter_form,
        "prescription_form": prescription_form,
        "prescriptions": patient.medications.select_related("prescribed_by").order_by("-start_date"),
        "encounters": patient.encounters.select_related("attending_doctor").order_by("-started_at"),
        "encounter_count": patient.encounters.count(),
        "vitals": patient.vitals.all().order_by("-recorded_at"),
    }


@login_required
def doctor_patient_detail(request, patient_id):
    """Doctor's patient profile: demographics, encounters, requested tests & results."""
    _require_role(request, {StaffRole.DOCTOR, StaffRole.SPECIALIST, StaffRole.ICT_ADMIN})
    patient = get_object_or_404(Patient, pk=patient_id)

    context = _doctor_patient_detail_context(patient, request.user.staff_profile)
    return render(request, "app/doctor_patient_detail.html", context)


@login_required
def doctor_request_test(request, patient_id):
    """Doctor requests a lab/pathology/radiography test for a specific patient."""
    staff_profile = _require_role(request, {StaffRole.DOCTOR, StaffRole.SPECIALIST, StaffRole.ICT_ADMIN})
    patient = get_object_or_404(Patient, pk=patient_id)

    if request.method == "POST":
        form = LabTestOrderForm(request.POST, patient=patient)
        if form.is_valid():
            order = form.save(commit=False)
            # The form's patient field is pre-scoped, but enforce it anyway.
            order.patient = patient
            order.ordered_by = staff_profile
            order.save()
            messages.success(request, f"Test '{order.test_name}' requested for {patient}.")
            return redirect("doctor_patient_detail", patient_id=patient.id)

        # Re-render the patient detail page with validation errors visible.
        context = _doctor_patient_detail_context(patient, staff_profile, request_form=form)
        return render(request, "app/doctor_patient_detail.html", context)

    # GET: the form lives on the patient detail page.
    return redirect("doctor_patient_detail", patient_id=patient.id)


@login_required
def doctor_encounter_create(request, patient_id):
    """Doctor creates an encounter for the patient whose profile is being viewed."""
    staff_profile = _require_role(request, {StaffRole.DOCTOR, StaffRole.SPECIALIST, StaffRole.ICT_ADMIN})
    patient = get_object_or_404(Patient, pk=patient_id)

    if request.method == "POST":
        form = DoctorEncounterForm(request.POST)
        if form.is_valid():
            encounter = form.save(commit=False)
            encounter.patient = patient
            # Auto-fill attending doctor when not chosen.
            if not encounter.attending_doctor_id and staff_profile.role in {StaffRole.DOCTOR, StaffRole.SPECIALIST}:
                encounter.attending_doctor = staff_profile
            encounter.save()
            messages.success(request, "Encounter created successfully.")
            return redirect("doctor_patient_detail", patient_id=patient.id)

        # Re-render the patient detail page with validation errors visible.
        context = _doctor_patient_detail_context(patient, staff_profile, encounter_form=form)
        return render(request, "app/doctor_patient_detail.html", context)

    # GET: the form lives on the patient detail page.
    return redirect("doctor_patient_detail", patient_id=patient.id)


@login_required
def doctor_prescription_create(request, patient_id):
    """Doctor writes a prescription for the patient whose profile is being viewed."""
    staff_profile = _require_role(request, {StaffRole.DOCTOR, StaffRole.SPECIALIST, StaffRole.ICT_ADMIN})
    patient = get_object_or_404(Patient, pk=patient_id)

    if request.method == "POST":
        form = PrescribedMedicationForm(request.POST)
        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.patient = patient
            prescription.prescribed_by = staff_profile
            prescription.save()
            messages.success(request, f"Prescription '{prescription.medication_name}' written for {patient}.")
            return redirect("doctor_patient_detail", patient_id=patient.id)

        # Re-render the patient detail page with validation errors visible.
        context = _doctor_patient_detail_context(patient, staff_profile, prescription_form=form)
        return render(request, "app/doctor_patient_detail.html", context)

    # GET: the form lives on the patient detail page.
    return redirect("doctor_patient_detail", patient_id=patient.id)


@login_required
def doctor_view_test_result(request, order_id):
    """Doctor views the results/report uploaded for a requested test."""
    _require_role(request, {StaffRole.DOCTOR, StaffRole.SPECIALIST, StaffRole.ICT_ADMIN})
    order = get_object_or_404(LabTestOrder, pk=order_id)

    # Determine the platform-specific result object for this order.
    pathology = getattr(order, "pathologist_finding", None)
    radiography = getattr(order, "radiography_study", None)
    lab_results = order.lab_results.all().order_by("-created_at")

    return render(request, "app/doctor_test_result_detail.html", {
        "title": f"Test Results - {order.test_name}",
        "order": order,
        "pathology": pathology,
        "radiography": radiography,
        "lab_results": lab_results,
    })


@login_required
def nurse_dashboard(request):
    """Nurse dashboard showing today's encounters and patients needing vitals."""
    _require_role(request, {StaffRole.NURSE})
    today = timezone.now().date()
    # Patients registered today (most recent first) with a flag indicating no vitals yet
    patients = Patient.objects.all().order_by('-created_at')
    # Today's encounters for the nurse to manage
    todays_encounters = Encounter.objects.filter(
        started_at__date=today
    ).select_related('patient', 'attending_doctor').order_by('started_at')
    # Patients who need vitals check (registered today with no vitals recorded)
    patients_needing_vitals = [
        p for p in patients
        if not p.vitals.exists()
    ]

    # Build test-status info per patient (requested tests awaiting vs ready).
    patient_test_status = {
        p.id: _patient_test_summary(p) for p in patients
    }
    encounter_test_status = {
        enc.id: _patient_test_summary(enc.patient) for enc in todays_encounters
    }

    return render(request, 'app/nurse_dashboard.html', {
        'title': 'Nurse Dashboard',
        'patients': patients,
        'todays_encounters': todays_encounters,
        'patients_needing_vitals': patients_needing_vitals,
        'patient_test_status': patient_test_status,
        'encounter_test_status': encounter_test_status,
    })

@login_required
def nurse_patient_create(request):
    _require_role(request, {StaffRole.NURSE})
    if request.method == 'POST':
        patient_form = PatientRegistrationForm(request.POST)
        nok_formset = NextOfKinFormSet(request.POST, instance=Patient())
        if patient_form.is_valid() and nok_formset.is_valid():
            patient = patient_form.save()
            nok_forms = nok_formset.save(commit=False)
            for nok_form in nok_forms:
                nok_form.patient = patient
                nok_form.save()
            messages.success(request, "Patient and next‑of‑kin records created.")
            return redirect('nurse_dashboard')
    else:
        patient_form = PatientRegistrationForm()
        nok_formset = NextOfKinFormSet(instance=Patient())
    return render(request, 'app/nurse_patient_form.html', {
        'form': patient_form,
        'nok_formset': nok_formset,
        'title': 'Register Patient',
        'submit_label': 'Create Patient',
    })

@login_required
def nurse_vital_signs_create(request, patient_id):
    _require_role(request, {StaffRole.NURSE})
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = VitalSignsForm(request.POST)
        if form.is_valid():
            vital = form.save(commit=False)
            vital.patient = patient
            vital.recorded_by = request.user.staff_profile
            
            vital.save()
            messages.success(request, "Vital signs recorded successfully.")
            return redirect('nurse_patient_detail', patient_id=patient.id)
    else:
        form = VitalSignsForm()

    return render(request, 'app/nurse_vital_signs_form.html',
                 {'form': form, 'patient': patient})

@login_required
def nurse_medication_create(request, patient_id):
    """Nurses cannot add medications — redirect to patient detail for viewing only."""
    _require_role(request, {StaffRole.NURSE})
    messages.info(
        request,
        "Medications are prescribed by the doctor. You can view recommended "
        "medications on the patient detail page."
    )
    return redirect('nurse_patient_detail', patient_id=patient_id)

@login_required
def nurse_patient_list(request):
    """List today's encounter patients for the nurse with status indicators."""
    _require_role(request, {StaffRole.NURSE})
    today = timezone.now().date()
    # Get encounters for today, ordered by start time (earliest first)
    todays_encounters = Encounter.objects.filter(
        started_at__date=today
    ).select_related('patient', 'attending_doctor').order_by('started_at')
    # All patients ordered by most recently created first
    patients = Patient.objects.all().order_by('-created_at')
    # Build a set of patient IDs that have vitals recorded
    patients_with_vitals = set(
        VitalSigns.objects.values_list('patient_id', flat=True).distinct()
    )

    # Test status summaries for patients and today's encounters.
    patient_test_status = {
        p.id: _patient_test_summary(p) for p in patients
    }
    encounter_test_status = {
        enc.id: _patient_test_summary(enc.patient) for enc in todays_encounters
    }

    return render(request, 'app/nurse_patient_list.html', {
        'patients': patients,
        'todays_encounters': todays_encounters,
        'patients_with_vitals': patients_with_vitals,
        'patient_test_status': patient_test_status,
        'encounter_test_status': encounter_test_status,
    })

@login_required
def nurse_patient_detail(request, patient_id):
    """View patient details, vitals, and doctor-recommended medications (read-only)."""
    _require_role(request, {StaffRole.NURSE})
    patient = get_object_or_404(Patient, pk=patient_id)
    vitals = patient.vitals.all().order_by('-recorded_at')
    # Show prescribed medications for this patient (read-only for nurse)
    medications = patient.medications.all().order_by('-created_at')
    # Get AI medication suggestions from the patient's encounters (doctor-recommended)
    ai_medications = AIMedicationSuggestion.objects.filter(
        encounter__patient=patient
    ).select_related('encounter').order_by('-created_at')
    # Get the patient's encounters with their status
    encounters = patient.encounters.all().order_by('-started_at')
    # Requested lab/pathology/radiography tests with status (read-only for nurse)
    test_orders = (
        LabTestOrder.objects.filter(patient=patient)
        .select_related("ordered_by")
        .order_by("-ordered_at")
    )
    return render(request, 'app/nurse_patient_detail.html', {
        'patient': patient,
        'vitals': vitals,
        'medications': medications,
        'ai_medications': ai_medications,
        'encounters': encounters,
        'test_orders': test_orders,
    })


@login_required
def nurse_change_encounter_status(request, encounter_id):
    """Allow nurse to change an encounter status (e.g. to PENDING_REVIEW for follow-ups)."""
    _require_role(request, {StaffRole.NURSE})
    encounter = get_object_or_404(Encounter, pk=encounter_id)

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        # Allowed status transitions for nurse
        allowed_statuses = {
            Encounter.EncounterStatus.PENDING_REVIEW,
            Encounter.EncounterStatus.IN_CONSULTATION,
            Encounter.EncounterStatus.DONE,
        }
        if new_status in {s.value for s in allowed_statuses}:
            encounter.status = new_status
            encounter.save()
            messages.success(
                request,
                f"Encounter status changed to {encounter.get_status_display()}."
            )
        else:
            messages.error(request, "Invalid status selected.")
        return redirect('nurse_patient_list')


# ===========================================================================
# PATHOLOGIST PLATFORM VIEWS
# ===========================================================================

@login_required
def pathologist_dashboard(request):
    """Pathologist dashboard: view pending orders, write reports, review lab tech results."""
    _require_role(request, {StaffRole.PATHOLOGIST})
    staff = request.user.staff_profile

    # Pending pathology orders (Histopathology, Cytopathology, Hematopathology, etc.)
    pathology_categories = [
        LabTestCategory.HISTOPATHOLOGY,
        LabTestCategory.CYTOPATHOLOGY,
        LabTestCategory.HEMATOPATHOLOGY,
        LabTestCategory.AUTOPSY,
        LabTestCategory.MOLECULAR_GENETIC,
        LabTestCategory.IHC,
        LabTestCategory.TRANSFUSION_PATH,
    ]
    pending_orders = LabTestOrder.objects.filter(
        test_category__in=pathology_categories,
    ).exclude(
        status=LabTestOrder.OrderStatus.COMPLETED
    ).select_related("patient", "encounter", "ordered_by").order_by("-priority", "-ordered_at")

    # Pathologist's own draft/final reports
    my_reports = PathologistFinding.objects.filter(
        pathologist=staff,
    ).select_related("lab_test_order__patient").order_by("-created_at")

    # Lab tech results waiting for pathologist verification
    pending_verifications = LabTestResult.objects.filter(
        status=LabTestResult.ResultStatus.COMPLETED,
    ).select_related("lab_test_order__patient", "lab_technician").order_by("-created_at")

    return render(request, "app/pathologist_dashboard.html", {
        "title": "Pathologist Dashboard",
        "pending_orders": pending_orders,
        "my_reports": my_reports,
        "pending_verifications": pending_verifications,
    })


@login_required
def pathologist_report_create(request, order_id):
    """Create a pathology report/finding for a lab test order."""
    _require_role(request, {StaffRole.PATHOLOGIST})
    order = get_object_or_404(LabTestOrder, pk=order_id)

    # If a finding already exists, redirect to edit
    if hasattr(order, "pathologist_finding"):
        return redirect("pathologist_report_edit", order_id=order.id)

    if request.method == "POST":
        form = PathologistFindingForm(request.POST, request.FILES)
        if form.is_valid():
            finding = form.save(commit=False)
            finding.lab_test_order = order
            finding.pathologist = request.user.staff_profile
            finding.save()
            # Mark order as in progress
            order.status = LabTestOrder.OrderStatus.IN_PROGRESS
            order.save()
            messages.success(request, "Pathology report created successfully.")
            return redirect("pathologist_dashboard")
    else:
        form = PathologistFindingForm()

    return render(request, "app/pathologist_report_form.html", {
        "title": f"Pathology Report - {order.test_name}",
        "form": form,
        "order": order,
        "submit_label": "Save Report",
    })


@login_required
def pathologist_report_edit(request, order_id):
    """Edit an existing pathology report."""
    _require_role(request, {StaffRole.PATHOLOGIST})
    order = get_object_or_404(LabTestOrder, pk=order_id)
    finding = get_object_or_404(PathologistFinding, lab_test_order=order)

    if request.method == "POST":
        form = PathologistFindingForm(request.POST, request.FILES, instance=finding)
        if form.is_valid():
            form.save()
            # If marked final, complete the order
            if finding.status == PathologistFinding.FindingStatus.FINAL:
                order.status = LabTestOrder.OrderStatus.COMPLETED
                order.completed_at = timezone.now()
                order.save()
            messages.success(request, "Pathology report updated successfully.")
            return redirect("pathologist_dashboard")
    else:
        form = PathologistFindingForm(instance=finding)

    return render(request, "app/pathologist_report_form.html", {
        "title": f"Edit Pathology Report - {order.test_name}",
        "form": form,
        "order": order,
        "submit_label": "Update Report",
    })


@login_required
def pathologist_verify_lab_result(request, result_id):
    """Pathologist verifies a lab technician's test result."""
    _require_role(request, {StaffRole.PATHOLOGIST})
    result = get_object_or_404(LabTestResult, pk=result_id)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "verify":
            result.status = LabTestResult.ResultStatus.VERIFIED
            result.verified_by = request.user.staff_profile
            result.verified_at = timezone.now()
            # Complete the order
            order = result.lab_test_order
            order.status = LabTestOrder.OrderStatus.COMPLETED
            order.completed_at = timezone.now()
            order.save()
            result.save()
            messages.success(request, "Lab result verified and order completed.")
        elif action == "reject":
            result.status = LabTestResult.ResultStatus.IN_PROGRESS
            result.save()
            messages.warning(request, "Lab result sent back for revision.")
        return redirect("pathologist_dashboard")

    return render(request, "app/pathologist_verify_result.html", {
        "title": "Verify Lab Result",
        "result": result,
    })


# ===========================================================================
# LAB TECHNICIAN PLATFORM VIEWS
# ===========================================================================

@login_required
def lab_tech_dashboard(request):
    """Lab Technician dashboard: view assigned orders, enter results."""
    _require_role(request, {StaffRole.LAB_TECH})
    staff = request.user.staff_profile

    # Lab technician categories (not pathology, not radiography)
    lab_categories = [
        LabTestCategory.HEMATOLOGY,
        LabTestCategory.CLINICAL_CHEMISTRY,
        LabTestCategory.MICROBIOLOGY,
        LabTestCategory.IMMUNOLOGY_SEROLOGY,
        LabTestCategory.URINALYSIS,
        LabTestCategory.HISTOLOGY_CYTOLOGY,
        LabTestCategory.TRANSFUSION_LAB,
    ]
    pending_orders = LabTestOrder.objects.filter(
        test_category__in=lab_categories,
    ).exclude(
        status=LabTestOrder.OrderStatus.COMPLETED
    ).select_related("patient", "encounter", "ordered_by").order_by("-priority", "-ordered_at")

    # Lab tech's own results
    my_results = LabTestResult.objects.filter(
        lab_technician=staff,
    ).select_related("lab_test_order__patient").order_by("-created_at")

    # Limited patient info — only through orders, not direct access
    return render(request, "app/lab_tech_dashboard.html", {
        "title": "Lab Technician Dashboard",
        "pending_orders": pending_orders,
        "my_results": my_results,
    })


@login_required
def lab_tech_result_create(request, order_id):
    """Lab technician enters test results for an order."""
    _require_role(request, {StaffRole.LAB_TECH})
    order = get_object_or_404(LabTestOrder, pk=order_id)

    if request.method == "POST":
        form = LabTestResultForm(request.POST, request.FILES)
        if form.is_valid():
            result = form.save(commit=False)
            result.lab_test_order = order
            result.lab_technician = request.user.staff_profile
            result.save()
            order.status = LabTestOrder.OrderStatus.IN_PROGRESS
            order.save()
            messages.success(request, "Lab result recorded successfully.")
            return redirect("lab_tech_dashboard")
    else:
        form = LabTestResultForm()

    return render(request, "app/lab_tech_result_form.html", {
        "title": f"Enter Result - {order.test_name}",
        "form": form,
        "order": order,
        "submit_label": "Save Result",
    })


@login_required
def lab_tech_result_edit(request, result_id):
    """Edit an existing lab result."""
    _require_role(request, {StaffRole.LAB_TECH})
    result = get_object_or_404(LabTestResult, pk=result_id)

    if request.method == "POST":
        form = LabTestResultForm(request.POST, request.FILES, instance=result)
        if form.is_valid():
            form.save()
            messages.success(request, "Lab result updated successfully.")
            return redirect("lab_tech_dashboard")
    else:
        form = LabTestResultForm(instance=result)

    return render(request, "app/lab_tech_result_form.html", {
        "title": f"Edit Result - {result.lab_test_order.test_name}",
        "form": form,
        "order": result.lab_test_order,
        "submit_label": "Update Result",
    })


@login_required
def lab_tech_submit_for_review(request, result_id):
    """Lab tech marks a result as complete, sending it for pathologist verification."""
    _require_role(request, {StaffRole.LAB_TECH})
    result = get_object_or_404(LabTestResult, pk=result_id)

    if request.method == "POST":
        result.status = LabTestResult.ResultStatus.COMPLETED
        result.save()
        messages.success(request, "Result submitted for pathologist review.")
        return redirect("lab_tech_dashboard")

    return redirect("lab_tech_dashboard")


# ===========================================================================
# RADIOGRAPHY PLATFORM VIEWS
# ===========================================================================

@login_required
def radiography_dashboard(request):
    """Radiography dashboard: view imaging orders, upload images, write reports."""
    _require_role(request, {StaffRole.RADIOGRAPHER})
    staff = request.user.staff_profile

    # Radiography categories
    radio_categories = [
        LabTestCategory.XRAY,
        LabTestCategory.CT,
        LabTestCategory.MRI,
        LabTestCategory.ULTRASOUND,
        LabTestCategory.FLUOROSCOPY,
        LabTestCategory.INTERVENTIONAL_RAD,
    ]
    pending_orders = LabTestOrder.objects.filter(
        test_category__in=radio_categories,
    ).exclude(
        status=LabTestOrder.OrderStatus.COMPLETED
    ).select_related("patient", "encounter", "ordered_by").order_by("-priority", "-ordered_at")

    # Radiographer's own studies
    my_studies = RadiographyStudy.objects.filter(
        radiographer=staff,
    ).select_related("lab_test_order__patient").order_by("-created_at")

    return render(request, "app/radiography_dashboard.html", {
        "title": "Radiography Dashboard",
        "pending_orders": pending_orders,
        "my_studies": my_studies,
    })


@login_required
def radiography_study_create(request, order_id):
    """Radiographer creates an imaging study with findings and image upload."""
    _require_role(request, {StaffRole.RADIOGRAPHER})
    order = get_object_or_404(LabTestOrder, pk=order_id)

    # If study already exists, redirect to edit
    if hasattr(order, "radiography_study"):
        return redirect("radiography_study_edit", order_id=order.id)

    if request.method == "POST":
        form = RadiographyStudyForm(request.POST, request.FILES)
        if form.is_valid():
            study = form.save(commit=False)
            study.lab_test_order = order
            study.radiographer = request.user.staff_profile
            study.save()
            order.status = LabTestOrder.OrderStatus.IN_PROGRESS
            order.save()
            messages.success(request, "Radiography study created successfully.")
            return redirect("radiography_dashboard")
    else:
        form = RadiographyStudyForm()

    return render(request, "app/radiography_study_form.html", {
        "title": f"Imaging Study - {order.test_name}",
        "form": form,
        "order": order,
        "submit_label": "Save Study",
        "is_image_upload": True,
    })


@login_required
def radiography_study_edit(request, order_id):
    """Edit an existing radiography study."""
    _require_role(request, {StaffRole.RADIOGRAPHER})
    order = get_object_or_404(LabTestOrder, pk=order_id)
    study = get_object_or_404(RadiographyStudy, lab_test_order=order)

    if request.method == "POST":
        form = RadiographyStudyForm(request.POST, request.FILES, instance=study)
        if form.is_valid():
            form.save()
            if study.status == RadiographyStudy.StudyStatus.COMPLETED:
                order.status = LabTestOrder.OrderStatus.COMPLETED
                order.completed_at = timezone.now()
                order.save()
            messages.success(request, "Radiography study updated successfully.")
            return redirect("radiography_dashboard")
    else:
        form = RadiographyStudyForm(instance=study)

    return render(request, "app/radiography_study_form.html", {
        "title": f"Edit Imaging Study - {order.test_name}",
        "form": form,
        "order": order,
        "study": study,
        "submit_label": "Update Study",
        "is_image_upload": True,
    })


# ===========================================================================
# SHARED: Lab Test Order Management (Doctor ordering tests)
# ===========================================================================

@login_required
def lab_test_order_create(request, encounter_id):
    """Doctor orders a lab/pathology/radiography test for a patient encounter."""
    _require_role(request, {StaffRole.DOCTOR, StaffRole.SPECIALIST, StaffRole.ICT_ADMIN})
    encounter = get_object_or_404(Encounter, pk=encounter_id)

    if request.method == "POST":
        form = LabTestOrderForm(request.POST, patient=encounter.patient)
        if form.is_valid():
            order = form.save(commit=False)
            order.encounter = encounter
            order.patient = encounter.patient
            order.ordered_by = request.user.staff_profile
            order.save()
            messages.success(request, f"Test '{order.test_name}' ordered successfully.")
            return redirect("encounter_list")
    else:
        form = LabTestOrderForm(
            patient=encounter.patient,
            initial={
                "encounter": encounter,
                "patient": encounter.patient,
            },
        )

    return render(request, "app/lab_test_order_form.html", {
        "title": f"Order Test - {encounter.patient}",
        "form": form,
        "encounter": encounter,
        "submit_label": "Order Test",
    })