"""Data models for hospital staff, patients, and encounters."""

import uuid

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models, transaction


class TimeStampedModel(models.Model):
    """Abstract base model that adds created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class StaffRole(models.TextChoices):
    """Supported hospital staff role values."""

    ICT_ADMIN = "ICT_ADMIN", "ICT Admin"
    DOCTOR = "DOCTOR", "Doctor"
    SPECIALIST = "SPECIALIST", "Specialist"
    NURSE = "NURSE", "Nurse"
    PHARMACIST = "PHARMACIST", "Pharmacist"
    PATHOLOGIST = "PATHOLOGIST", "Pathologist"
    LAB_TECH = "LAB_TECH", "Lab Technician"
    RADIOGRAPHER = "RADIOGRAPHER", "Radiographer"
    


class Sex(models.TextChoices):
    """Patient sex options used during registration."""

    MALE = "M", "Male"
    FEMALE = "F", "Female"
    


class StaffProfile(TimeStampedModel):
    """Profile and work metadata for a medical or administrative staff user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    staff_id = models.CharField(max_length=30, unique=True)
    role = models.CharField(max_length=20, choices=StaffRole.choices)
    department = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=20, blank=True)
    license_number = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True)
    registered_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registered_medical_staff",
        help_text="ICT user who registered this medical staff.",
    )
    registered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["staff_id"]

    def __str__(self):
        """Readable admin/list display name for staff objects."""
        return f"{self.staff_id} - {self.user.get_full_name() or self.user.username}"

    def clean(self):
        """Ensure staff users can authenticate with their registration number.

        Enforces that the associated Django User has a usable password so the
        staff member can login using their registration number (staff_id) and
        password. The staff user's username is synchronized to staff_id on save
        so the default Django authentication (username/password) works with the
        registration number.
        """
        # Ensure a user is linked
        if not self.user_id:
            raise ValidationError("StaffProfile must be linked to a Django User.")

        # Require a usable password so the staff can login with registration number
        if not self.user.has_usable_password():
            raise ValidationError({
                "user": (
                    "Associated user must have a usable password so staff can login "
                    "using the registration number and password."
                )
            })

        # Ensure the staff member's full name is registered on the linked User
        if not (self.user.first_name and self.user.last_name):
            raise ValidationError({
                "user": (
                    "Associated user must have first_name and last_name set so the "
                    "medical staff full name is registered."
                )
            })

        # Ensure no other User already uses the staff_id as a username.
        # This prevents a DB integrity error when we synchronize User.username
        # to staff_id during save.
        conflict_qs = User.objects.filter(username__iexact=self.staff_id)
        if self.user_id:
            conflict_qs = conflict_qs.exclude(pk=self.user_id)

        if conflict_qs.exists():
            raise ValidationError({
                "staff_id": (
                    "This staff ID would conflict with an existing user account username. "
                    "Choose a different staff ID or update the other user account."
                )
            })

    def save(self, *args, **kwargs):
        """Keep the related User.username synchronized to staff_id and validate
        the profile before saving.
        """
        # Run model validation to ensure password usability, names, and that
        # the staff_id will not conflict with existing usernames.
        self.full_clean()

        # If the linked User exists but username differs, update it so staff can
        # authenticate using their registration number as the username. Save the
        # User after validation to avoid DB integrity errors.
        if self.user_id and self.user.username != self.staff_id:
            self.user.username = self.staff_id
            self.user.save()

        return super().save(*args, **kwargs)

class PatientNumberSequence(models.Model):
    last_number = models.PositiveIntegerField(default=0)

    @classmethod
    def get_next_patient_number(cls):
        with transaction.atomic():
            seq = cls.objects.select_for_update().first()
            if not seq:
                seq = cls.objects.create(last_number=0)
            seq.last_number += 1
            seq.save()
            return f"PAT-{seq.last_number:06d}"  # Format as PAT-000001, PAT-000002, etc."


class Patient(TimeStampedModel):
    """Patient demographic, social determinant, and contact information."""

    patient_number = models.CharField(max_length=30, unique=True, editable=False)
    passport_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        help_text="Passport number (if applicable)."
    )
    national_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True,
        help_text="National ID / Social Security Number."
    )
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)
    date_of_birth = models.DateField()
    sex = models.CharField(max_length=1, choices=Sex.choices)

    nationality = models.CharField(max_length=80, blank=True)
    insurance_type = models.CharField(max_length=120, blank=True)
    tribe = models.CharField(max_length=80, blank=True)
    religion = models.CharField(max_length=80, blank=True)

    marital_status = models.CharField(max_length=200, blank=True)
    
    location = models.CharField(max_length=200, blank=True)
    occupation = models.CharField(max_length=120, blank=True)

    phone_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        """Generate a unique patient number if not already set."""
        if not self.patient_number:
            self.patient_number = PatientNumberSequence.get_next_patient_number()
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ["patient_number"]

    def validate_next_of_kin_count(self, allow_empty=True):
        """Validate that the patient has exactly two next-of-kin records.

        When ``allow_empty`` is True, zero records are allowed during early
        registration before contacts are added.
        """
        if not self.pk:
            return

        kin_count = self.next_of_kins.count()
        if allow_empty and kin_count == 0:
            return

        if kin_count != 2:
            raise ValidationError(
                "Each patient profile must have exactly 2 next-of-kin records."
            )

    def clean(self):
        """ validate that at least one unique identifier is provided"""
        if not (self.patient_number or self.passport_number or self.national_id):
            raise ValidationError(
                "At least one unique identifier (patient number, passport number, or national ID) must be provided."
            )
        """Keep patient-level next-of-kin validation in model logic."""
        self.validate_next_of_kin_count(allow_empty=True)

    def __str__(self):
        """Readable admin/list display name for patient objects."""
        return f"{self.patient_number} - {self.first_name} {self.last_name}"


class NextOfKin(TimeStampedModel):
    """Emergency contact details for a patient (two slots per patient)."""

    class KinSlot(models.IntegerChoices):
        """Fixed next-of-kin slot positions required by the system."""

        FIRST = 1, "Next of kin 1"
        SECOND = 2, "Next of kin 2"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="next_of_kins")
    slot = models.PositiveSmallIntegerField(choices=KinSlot.choices)
    full_name = models.CharField(max_length=160)
    relationship = models.CharField(max_length=80)
    phone_number = models.CharField(max_length=20)
    alternative_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["patient", "slot"]
        constraints = [
            models.UniqueConstraint(fields=["patient", "slot"], name="unique_patient_kin_slot")
        ]

    def clean(self):
        """Ensure a patient cannot have more than two next-of-kin records."""
        if not self.patient_id:
            return

        existing = NextOfKin.objects.filter(patient_id=self.patient_id)
        if self.pk:
            existing = existing.exclude(pk=self.pk)

        if existing.count() >= 2:
            raise ValidationError(
                "A patient cannot have more than 2 next-of-kin records."
            )

    def save(self, *args, **kwargs):
        """Run model validation before saving next-of-kin records."""
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        """Readable admin/list display name for next-of-kin objects."""
        return f"{self.patient.patient_number} - {self.full_name}"


class Encounter(TimeStampedModel):
    """A patient care interaction including notes and specialist review outcome."""

    class EncounterType(models.TextChoices):
        """Clinical encounter categories."""

        OUTPATIENT = "OUTPATIENT", "Outpatient"
        INPATIENT = "INPATIENT", "Inpatient"
        EMERGENCY = "EMERGENCY", "Emergency"
        FOLLOW_UP = "FOLLOW_UP", "Follow-up"

    class EncounterStatus(models.TextChoices):
        """Workflow status of an encounter."""
        SCHEDULED = "SCHEDULED", "Scheduled"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        IN_CONSULTATION = "IN_CONSULTATION", "In Consultation"
        OPEN = "OPEN", "Open"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        DONE = "DONE", "Done"

    class SpecialistDecision(models.TextChoices):
        """Specialist review decision for AI/clinical recommendations."""

        PENDING = "PENDING", "Pending"
        AGREED = "AGREED", "Agreed"
        UPDATED = "UPDATED", "Updated with remarks"
        REJECTED = "REJECTED", "Rejected"

    encounter_number = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="encounters")
    encounter_type = models.CharField(max_length=20, choices=EncounterType.choices)
    status = models.CharField(max_length=20, choices=EncounterStatus.choices, default=EncounterStatus.OPEN)

    attending_doctor = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attending_encounters",
    )
    specialist_reviewer = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="specialist_reviews",
    )

    chief_complaint = models.TextField(blank=True)
    symptoms = models.TextField(blank=True)
    doctor_notes = models.TextField(blank=True)
    assessment = models.TextField(blank=True)
    plan = models.TextField(blank=True)

    specialist_decision = models.CharField(
        max_length=20,
        choices=SpecialistDecision.choices,
        default=SpecialistDecision.PENDING,
    )
    specialist_remarks = models.TextField(blank=True)
    specialist_reviewed_at = models.DateTimeField(null=True, blank=True)

    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def clean(self):
        """Validate temporal consistency for encounter start/end timestamps."""
        if self.ended_at and self.ended_at < self.started_at:
            raise ValidationError({"ended_at": "Encounter end time cannot be earlier than start time."})

        if self.patient_id:
            self.patient.validate_next_of_kin_count(allow_empty=False)

    def __str__(self):
        """Readable admin/list display name for encounter objects."""
        return f"{self.encounter_number} - {self.patient.patient_number}"


class AIReviewStatus(models.TextChoices):
    """Workflow state for clinician review of AI recommendations."""

    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class AIRecommendationBase(TimeStampedModel):
    """Shared fields for AI-generated clinical recommendations."""

    encounter = models.ForeignKey(
        Encounter,
        on_delete=models.CASCADE,
        related_name="%(class)s_items",
    )
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    rationale = models.TextField(blank=True)
    source_model = models.CharField(max_length=120, blank=True)

    review_status = models.CharField(
        max_length=20,
        choices=AIReviewStatus.choices,
        default=AIReviewStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_reviewed_items",
    )
    reviewer_remarks = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def clean(self):
        """Validate confidence range and reviewer metadata consistency."""
        if self.confidence_score is not None and not (0 <= self.confidence_score <= 1):
            raise ValidationError({"confidence_score": "Confidence score must be between 0 and 1."})

        if self.review_status != AIReviewStatus.PENDING and not self.reviewed_by_id:
            raise ValidationError({"reviewed_by": "Reviewed-by is required when status is approved/rejected."})


class AIDiagnosisSuggestion(AIRecommendationBase):
    """AI diagnosis suggestions generated from encounter data."""

    diagnosis_name = models.CharField(max_length=200)
    icd10_code = models.CharField(max_length=20, blank=True)
    differential_rank = models.PositiveSmallIntegerField(default=1)

    class Meta(AIRecommendationBase.Meta):
        ordering = ["encounter", "differential_rank", "-created_at"]

    def __str__(self):
        """Readable admin/list display value for diagnosis suggestion."""
        return f"{self.encounter.encounter_number} - {self.diagnosis_name}"


class AILabTestSuggestion(AIRecommendationBase):
    """AI-recommended laboratory tests for an encounter."""

    class Priority(models.TextChoices):
        """Urgency level for suggested test requests."""

        ROUTINE = "ROUTINE", "Routine"
        URGENT = "URGENT", "Urgent"
        STAT = "STAT", "Stat"

    test_name = models.CharField(max_length=200)
    loinc_code = models.CharField(max_length=30, blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.ROUTINE)
    clinical_question = models.TextField(blank=True)

    def __str__(self):
        """Readable admin/list display value for lab suggestion."""
        return f"{self.encounter.encounter_number} - {self.test_name}"


class AIMedicationSuggestion(AIRecommendationBase):
    """AI medication recommendations for clinician review."""

    medication_name = models.CharField(max_length=200)
    dose = models.CharField(max_length=80, blank=True)
    route = models.CharField(max_length=60, blank=True)
    frequency = models.CharField(max_length=80, blank=True)
    duration = models.CharField(max_length=80, blank=True)
    safety_notes = models.TextField(blank=True)

    def __str__(self):
        """Readable admin/list display value for medication suggestion."""
        return f"{self.encounter.encounter_number} - {self.medication_name}"


class VitalSigns(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="vitals")
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight in kilograms")
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Height in centimeters")
    pulse = models.PositiveIntegerField(null=True, blank=True, help_text="Pulse rate in beats per minute")
    body_temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="Body temperature in Celsius")
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="recorded_vitals")

    def __str__(self):
        """Readable admin/list display value for vital signs."""
        return f"{self.patient} - {self.recorded_at.strftime('%Y-%m-%d %H:%M:%S')  }"

class PrescriptionType(models.TextChoices):
    """Type of prescription being written."""

    OUTPATIENT = "OUTPATIENT", "Outpatient"
    INPATIENT = "INPATIENT", "Inpatient"
    REPEAT = "REPEAT", "Repeat"
    CONTROLLED = "CONTROLLED", "Controlled Drug"


class AdministrationRoute(models.TextChoices):
    """Route of administration for a prescribed medicine."""

    ORAL = "ORAL", "Oral"
    INJECTION = "INJECTION", "Injection"
    INTRAVENOUS = "INTRAVENOUS", "Intravenous"
    TOPICAL = "TOPICAL", "Topical"
    INHALATION = "INHALATION", "Inhalation"
    SUBCUTANEOUS = "SUBCUTANEOUS", "Subcutaneous"
    RECTAL = "RECTAL", "Rectal"
    OPHTHALMIC = "OPHTHALMIC", "Ophthalmic"
    OTIC = "OTIC", "Otic"
    OTHER = "OTHER", "Other"


class PrescribedMedication(TimeStampedModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="medications")
    medication_name = models.CharField(max_length=200, help_text="Generic or brand name of the medicine")
    dose = models.CharField(max_length=80, blank=True, help_text="Exact amount (e.g. 500 mg)")
    route = models.CharField(
        max_length=30,
        choices=AdministrationRoute.choices,
        default=AdministrationRoute.ORAL,
        blank=True,
    )
    frequency = models.CharField(max_length=80, blank=True, help_text="How often (e.g. twice daily, every 8 hours)")
    duration = models.CharField(max_length=80, blank=True, help_text="How long to continue (e.g. 7 days, until finished)")
    prescription_type = models.CharField(
        max_length=20,
        choices=PrescriptionType.choices,
        default=PrescriptionType.OUTPATIENT,
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    prescribed_by = models.ForeignKey(StaffProfile, 
                                      on_delete=models.SET_NULL, 
                                      null=True, 
                                      blank=True, 
                                      related_name="prescribed_medications")
    special_instructions = models.TextField(
        blank=True,
        help_text="Take with food, avoid alcohol, store in fridge, etc.",
    )
    notes = models.TextField(blank=True)
    def __str__(self):
        """Readable admin/list display value for prescribed medication."""
        return f"{self.patient} - {self.medication_name} ({self.start_date} to {self.end_date or 'ongoing'})"


# ---------------------------------------------------------------------------
# Lab / Pathology / Radiography Platform Models
# ---------------------------------------------------------------------------

class LabTestCategory(models.TextChoices):
    """Top-level categories for lab, pathology, and radiography tests."""

    # -- Pathologist categories --
    HISTOPATHOLOGY = "HISTOPATHOLOGY", "Histopathology (Tissue Analysis)"
    CYTOPATHOLOGY = "CYTOPATHOLOGY", "Cytopathology (Cell Analysis)"
    HEMATOPATHOLOGY = "HEMATOPATHOLOGY", "Hematopathology (Blood Disorders)"
    AUTOPSY = "AUTOPSY", "Autopsy Examination"
    MOLECULAR_GENETIC = "MOLECULAR_GENETIC", "Molecular & Genetic Testing"
    IHC = "IHC", "Immunohistochemistry (IHC)"
    TRANSFUSION_PATH = "TRANSFUSION_PATH", "Transfusion Medicine Oversight"

    # -- Lab Technician categories --
    HEMATOLOGY = "HEMATOLOGY", "Hematology"
    CLINICAL_CHEMISTRY = "CLINICAL_CHEMISTRY", "Clinical Chemistry"
    MICROBIOLOGY = "MICROBIOLOGY", "Microbiology"
    IMMUNOLOGY_SEROLOGY = "IMMUNOLOGY_SEROLOGY", "Immunology & Serology"
    URINALYSIS = "URINALYSIS", "Urinalysis & Fluid Tests"
    HISTOLOGY_CYTOLOGY = "HISTOLOGY_CYTOLOGY", "Histology & Cytology Prep"
    TRANSFUSION_LAB = "TRANSFUSION_LAB", "Transfusion Medicine"

    # -- Radiography categories --
    XRAY = "XRAY", "X-ray"
    CT = "CT", "CT (Computed Tomography)"
    MRI = "MRI", "MRI (Magnetic Resonance Imaging)"
    ULTRASOUND = "ULTRASOUND", "Ultrasound"
    FLUOROSCOPY = "FLUOROSCOPY", "Fluoroscopy"
    INTERVENTIONAL_RAD = "INTERVENTIONAL_RAD", "Interventional Radiography"


class LabTestOrder(TimeStampedModel):
    """A test ordered by a doctor during an encounter for lab/pathology/radiography."""

    class OrderStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    class Priority(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        URGENT = "URGENT", "Urgent"
        STAT = "STAT", "Stat"

    encounter = models.ForeignKey(
        Encounter, on_delete=models.CASCADE, related_name="lab_test_orders"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="lab_test_orders"
    )
    test_name = models.CharField(max_length=200)
    test_category = models.CharField(max_length=30, choices=LabTestCategory.choices)
    ordered_by = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ordered_lab_tests",
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.ROUTINE
    )
    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    clinical_notes = models.TextField(blank=True, help_text="Doctor's notes for the lab/radio.")
    ordered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-ordered_at"]

    def __str__(self):
        return f"{self.test_name} ({self.get_test_category_display()}) - {self.patient}"


# ---------------------------------------------------------------------------
# 1. PATHOLOGIST PLATFORM
# ---------------------------------------------------------------------------

class PathologistFinding(TimeStampedModel):
    """Pathologist's detailed findings, diagnosis, and report for a test order."""

    class FindingStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINAL = "FINAL", "Final"
        AMENDED = "AMENDED", "Amended"

    lab_test_order = models.OneToOneField(
        LabTestOrder,
        on_delete=models.CASCADE,
        related_name="pathologist_finding",
    )
    pathologist = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pathologist_findings",
    )
    status = models.CharField(
        max_length=20, choices=FindingStatus.choices, default=FindingStatus.DRAFT
    )

    # -- Specimen details --
    specimen_type = models.CharField(max_length=200, blank=True)
    specimen_received_at = models.DateTimeField(null=True, blank=True)
    specimen_quality = models.CharField(max_length=100, blank=True)

    # -- Microscopic / Gross findings --
    gross_description = models.TextField(blank=True, help_text="Macroscopic description of specimen.")
    microscopic_findings = models.TextField(blank=True, help_text="Microscopic examination findings.")

    # -- Diagnosis & grading --
    diagnosis = models.TextField(blank=True, help_text="Final pathological diagnosis.")
    tumor_grade = models.CharField(max_length=60, blank=True, help_text="Tumor grading (e.g., Grade I-IV, Gleason score).")
    margins_status = models.CharField(max_length=60, blank=True, help_text="Surgical margins status.")
    lymph_node_status = models.CharField(max_length=100, blank=True)

    # -- Special studies --
    ihc_results = models.TextField(blank=True, help_text="Immunohistochemistry staining results.")
    molecular_findings = models.TextField(blank=True, help_text="DNA/RNA, PCR, sequencing results.")
    flow_cytometry_results = models.TextField(blank=True)

    # -- Autopsy-specific --
    cause_of_death = models.CharField(max_length=200, blank=True)
    organ_damage_summary = models.TextField(blank=True)

    # -- Conclusion & report --
    conclusion = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    report_file = models.FileField(upload_to="pathology_reports/%Y/%m/", null=True, blank=True)

    # -- Review tracking --
    reviewed_by = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_pathology_reports",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pathology Report - {self.lab_test_order}"


# ---------------------------------------------------------------------------
# 2. LAB TECHNICIAN PLATFORM
# ---------------------------------------------------------------------------

class LabTestResult(TimeStampedModel):
    """Lab technician's test result entry for a lab test order."""

    class ResultStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        VERIFIED = "VERIFIED", "Verified by Pathologist"

    lab_test_order = models.ForeignKey(
        LabTestOrder,
        on_delete=models.CASCADE,
        related_name="lab_results",
    )
    lab_technician = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="lab_test_results",
    )
    status = models.CharField(
        max_length=20, choices=ResultStatus.choices, default=ResultStatus.PENDING
    )

    # -- Result details --
    result_value = models.TextField(blank=True, help_text="Numerical or descriptive result.")
    reference_range = models.CharField(max_length=120, blank=True)
    is_abnormal = models.BooleanField(default=False)
    units = models.CharField(max_length=40, blank=True)

    # -- Additional fields --
    methodology = models.CharField(max_length=120, blank=True)
    instrument_used = models.CharField(max_length=120, blank=True)
    technician_notes = models.TextField(blank=True)

    # -- Report attachment --
    result_file = models.FileField(upload_to="lab_results/%Y/%m/", null=True, blank=True)

    # -- Verification by pathologist --
    verified_by = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_lab_results",
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Lab Result - {self.lab_test_order.test_name} ({self.lab_test_order.patient})"


# ---------------------------------------------------------------------------
# 3. RADIOGRAPHY PLATFORM
# ---------------------------------------------------------------------------

class RadiographyStudy(TimeStampedModel):
    """Radiography imaging study with findings, images, and report."""

    class StudyStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"

    lab_test_order = models.OneToOneField(
        LabTestOrder,
        on_delete=models.CASCADE,
        related_name="radiography_study",
    )
    radiographer = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="radiography_studies",
    )
    status = models.CharField(
        max_length=20, choices=StudyStatus.choices, default=StudyStatus.PENDING
    )

    # -- Imaging details --
    body_part = models.CharField(max_length=120, blank=True, help_text="Body part/region imaged.")
    technique = models.CharField(max_length=200, blank=True, help_text="Imaging technique and protocol.")
    contrast_used = models.CharField(max_length=100, blank=True)

    # -- Image upload --
    image_file = models.ImageField(upload_to="radiography_images/%Y/%m/", null=True, blank=True)
    additional_image_1 = models.ImageField(upload_to="radiography_images/%Y/%m/", null=True, blank=True)
    additional_image_2 = models.ImageField(upload_to="radiography_images/%Y/%m/", null=True, blank=True)

    # -- Findings & impression --
    findings = models.TextField(blank=True, help_text="Detailed imaging findings.")
    impression = models.TextField(blank=True, help_text="Radiologist's impression / summary.")
    conclusion = models.TextField(blank=True)

    # -- Report --
    report_file = models.FileField(upload_to="radiography_reports/%Y/%m/", null=True, blank=True)

    # -- Review tracking --
    reviewed_by = models.ForeignKey(
        StaffProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_radiography_studies",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Radiography Studies"

    def __str__(self):
        return f"Radiography Study - {self.lab_test_order.test_name} ({self.lab_test_order.patient})"
