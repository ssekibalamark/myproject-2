from django.contrib import admin
from django.utils import timezone

from .models import (
    AIDiagnosisSuggestion,
    AILabTestSuggestion,
    AIMedicationSuggestion,
    Encounter,
    LabTestOrder,
    LabTestResult,
    NextOfKin,
    PathologistFinding,
    Patient,
    RadiographyStudy,
    StaffProfile,
)


class NextOfKinInline(admin.TabularInline):
    """Inline editor for patient next-of-kin records in Patient admin."""

    model = NextOfKin
    extra = 2
    min_num = 2
    max_num = 2


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    """Admin configuration for hospital staff profiles.

    Only ICT Admin users (or superusers) are allowed to register and manage
    staff records from Django admin.
    """

    list_display = ("staff_id", "user", "role", "department", "is_active", "registered_by", "registered_at")
    list_filter = ("role", "department", "is_active")
    search_fields = ("staff_id", "user__username", "user__first_name", "user__last_name", "department")
    autocomplete_fields = ("user", "registered_by")

    @staticmethod
    def _is_ict_admin(user):
        """Return True when the current user is allowed to manage staff records."""
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return hasattr(user, "staff_profile") and user.staff_profile.role == "ICT_ADMIN"

    def has_add_permission(self, request):
        """Allow creation of staff profiles for ICT Admin only."""
        return self._is_ict_admin(request.user)

    def has_change_permission(self, request, obj=None):
        """Allow editing of staff profiles for ICT Admin only."""
        return self._is_ict_admin(request.user)

    def has_delete_permission(self, request, obj=None):
        """Allow deleting staff profiles for ICT Admin only."""
        return self._is_ict_admin(request.user)

    def get_queryset(self, request):
        """Hide staff records from non-ICT users in admin list view."""
        queryset = super().get_queryset(request)
        if self._is_ict_admin(request.user):
            return queryset
        return queryset.none()

    def save_model(self, request, obj, form, change):
        """Capture who registered a staff profile and when it was created."""
        if not change:
            obj.registered_by = request.user
            obj.registered_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Admin configuration for patient demographic and profile records."""

    list_display = ("patient_number", 
                    "first_name", 
                    "last_name", 
                    "date_of_birth", 
                    "sex", 
                    "passport_number",
                    "national_id",
                    "insurance_type",
                    "nationality",
                    "marital_status",)
    list_filter = ("sex",
                  "insurance_type", 
                  "nationality",
                  "marital_status",)
    search_fields = ("patient_number", 
                     "first_name", 
                     "middle_name", 
                     "last_name", 
                     "phone_number",
                     "passport_number",
                     "national_id",
                     "tribe",
                     "nationality",)
    inlines = [NextOfKinInline]


@admin.register(NextOfKin)
class NextOfKinAdmin(admin.ModelAdmin):
    """Admin configuration for next-of-kin records."""

    list_display = ("patient", "slot", "full_name", "relationship", "phone_number")
    list_filter = ("slot", "relationship")
    search_fields = ("patient__patient_number", "full_name", "relationship", "phone_number")
    autocomplete_fields = ("patient",)


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    """Admin configuration for clinical encounters and specialist review state."""

    list_display = (
        "encounter_number",
        "patient",
        "encounter_type",
        "status",
        "attending_doctor",
        "specialist_reviewer",
        "started_at",
        "ended_at",
        "specialist_decision",
    )
    list_filter = ("encounter_type", "status", "specialist_decision", "started_at")
    search_fields = (
        "encounter_number",
        "patient__patient_number",
        "patient__first_name",
        "patient__last_name",
        "chief_complaint",
        "symptoms",
    )
    autocomplete_fields = ("patient", "attending_doctor", "specialist_reviewer")
    readonly_fields = ("encounter_number", "created_at", "updated_at")


@admin.register(AIDiagnosisSuggestion)
class AIDiagnosisSuggestionAdmin(admin.ModelAdmin):
    """Admin configuration for AI diagnosis recommendations."""

    list_display = (
        "encounter",
        "diagnosis_name",
        "icd10_code",
        "differential_rank",
        "confidence_score",
        "review_status",
        "reviewed_by",
    )
    list_filter = ("review_status", "differential_rank", "created_at")
    search_fields = ("encounter__encounter_number", "diagnosis_name", "icd10_code")
    autocomplete_fields = ("encounter", "reviewed_by")


@admin.register(AILabTestSuggestion)
class AILabTestSuggestionAdmin(admin.ModelAdmin):
    """Admin configuration for AI laboratory test recommendations."""

    list_display = (
        "encounter",
        "test_name",
        "priority",
        "confidence_score",
        "review_status",
        "reviewed_by",
    )
    list_filter = ("priority", "review_status", "created_at")
    search_fields = ("encounter__encounter_number", "test_name", "loinc_code")
    autocomplete_fields = ("encounter", "reviewed_by")


@admin.register(AIMedicationSuggestion)
class AIMedicationSuggestionAdmin(admin.ModelAdmin):
    """Admin configuration for AI medication recommendations."""

    list_display = (
        "encounter",
        "medication_name",
        "dose",
        "frequency",
        "confidence_score",
        "review_status",
        "reviewed_by",
    )
    list_filter = ("review_status", "created_at")
    search_fields = ("encounter__encounter_number", "medication_name")
    autocomplete_fields = ("encounter", "reviewed_by")


# ---------------------------------------------------------------------------
# Lab / Pathology / Radiography Admin Registrations
# ---------------------------------------------------------------------------

@admin.register(LabTestOrder)
class LabTestOrderAdmin(admin.ModelAdmin):
    """Admin configuration for lab/pathology/radiography test orders."""
    list_display = ("test_name", "patient", "test_category", "priority", "status", "ordered_by", "ordered_at")
    list_filter = ("test_category", "priority", "status", "ordered_at")
    search_fields = ("test_name", "patient__patient_number", "patient__first_name", "patient__last_name")
    autocomplete_fields = ("patient", "encounter", "ordered_by")


@admin.register(PathologistFinding)
class PathologistFindingAdmin(admin.ModelAdmin):
    """Admin configuration for pathologist findings and reports."""
    list_display = ("lab_test_order", "pathologist", "status", "specimen_type", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("lab_test_order__test_name", "lab_test_order__patient__patient_number", "diagnosis")
    autocomplete_fields = ("lab_test_order", "pathologist", "reviewed_by")


@admin.register(LabTestResult)
class LabTestResultAdmin(admin.ModelAdmin):
    """Admin configuration for lab technician test results."""
    list_display = ("lab_test_order", "lab_technician", "status", "result_value", "is_abnormal", "created_at")
    list_filter = ("status", "is_abnormal", "created_at")
    search_fields = ("lab_test_order__test_name", "lab_test_order__patient__patient_number", "result_value")
    autocomplete_fields = ("lab_test_order", "lab_technician", "verified_by")


@admin.register(RadiographyStudy)
class RadiographyStudyAdmin(admin.ModelAdmin):
    """Admin configuration for radiography imaging studies."""
    list_display = ("lab_test_order", "radiographer", "status", "body_part", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("lab_test_order__test_name", "lab_test_order__patient__patient_number", "body_part", "findings")
    autocomplete_fields = ("lab_test_order", "radiographer", "reviewed_by")
