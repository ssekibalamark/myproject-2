"""
Definition of forms.
"""

from datetime import date
from django.urls import reverse_lazy

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from .models import (
    AIDiagnosisSuggestion,
    AILabTestSuggestion,
    AIMedicationSuggestion,
    Encounter,
    NextOfKin,
    Patient,
    PrescribedMedication,
    StaffRole,
    StaffProfile,
    VitalSigns,
    
)
from django.forms import inlineformset_factory




class AutoBootstrapFormMixin:
    """Apply Bootstrap classes and required-field markup automatically."""

    base_input_class = "form-control"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget

            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                css_class = "form-check-input"
            else:
                css_class = self.base_input_class

            current = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{current} {css_class}".strip()

            if field.required:
                required_class = widget.attrs.get("class", "")
                widget.attrs["class"] = f"{required_class} is-required".strip()
                widget.attrs["required"] = "required"

                if field.label and not field.label.endswith(" *"):
                    field.label = f"{field.label} *"


class BaseStyledModelForm(AutoBootstrapFormMixin, forms.ModelForm):
    """Shared model form with Bootstrap styling and confidence validation."""

    def clean_confidence_score(self):
        """Validate confidence score range when the field is present."""
        confidence = self.cleaned_data.get("confidence_score")
        if confidence is None:
            return confidence
        if confidence < 0 or confidence > 1:
            raise forms.ValidationError("Confidence score must be between 0 and 1.")
        return confidence


class ICTStaffRegistrationForm(BaseStyledModelForm):
    """Form used by ICT Admin to register hospital staff profiles."""

    class Meta:
        model = StaffProfile
        fields = [
            "user",
            "staff_id",
            "role",
            "department",
            "phone_number",
            "license_number",
            "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = self.fields["user"].queryset.filter(staff_profile__isnull=True)

    def clean_staff_id(self):
        """Normalize and validate uniqueness of staff identifier."""
        staff_id = (self.cleaned_data.get("staff_id") or "").strip().upper()
        existing = StaffProfile.objects.filter(staff_id__iexact=staff_id)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError("This staff ID is already in use.")
        return staff_id

    def clean_phone_number(self):
        """Normalize phone number and enforce a basic length check."""
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if phone_number and len(phone_number) < 7:
            raise forms.ValidationError("Please enter a valid phone number.")
        return phone_number

    def clean_license_number(self):
        """Normalize optional license number and validate uniqueness when provided."""
        license_number = (self.cleaned_data.get("license_number") or "").strip().upper()
        if not license_number:
            return license_number

        existing = StaffProfile.objects.filter(license_number__iexact=license_number)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError("This license number is already in use.")
        return license_number

    def clean_user(self):
        """Ensure the selected account is not already linked to a staff profile."""
        user = self.cleaned_data["user"]
        if hasattr(user, "staff_profile"):
            raise forms.ValidationError("This user already has a staff profile.")
        # Require that the selected user can be used to login with staff_id/password
        if not user.has_usable_password():
            raise forms.ValidationError(
                "Selected user must have a password set so the staff can authenticate."
            )

        if not (user.first_name and user.last_name):
            raise forms.ValidationError(
                "Selected user must have first and last name set so the staff full name is registered."
            )

        return user

    def clean(self):
        """Apply cross-field validation rules for ICT staff registration."""
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        license_number = (cleaned_data.get("license_number") or "").strip()

        licensed_roles = {
            StaffRole.DOCTOR,
            StaffRole.SPECIALIST,
            StaffRole.PHARMACIST,
            StaffRole.LAB_TECH,
            StaffRole.RADIOGRAPHER,
        }

        if role in licensed_roles and not license_number:
            self.add_error("license_number", "License number is required for this staff role.")

        return cleaned_data


class HospitalStaffUpdateForm(BaseStyledModelForm):
    """Form for updating existing hospital staff profile details."""

    class Meta:
        model = StaffProfile
        fields = [
            "role",
            "department",
            "phone_number",
            "license_number",
            "is_active",
        ]

    def clean_phone_number(self):
        """Normalize phone number and enforce a basic length check."""
        phone_number = (self.cleaned_data.get("phone_number") or "").strip()
        if phone_number and len(phone_number) < 7:
            raise forms.ValidationError("Please enter a valid phone number.")
        return phone_number

    def clean_license_number(self):
        """Normalize optional license number and validate uniqueness when provided."""
        license_number = (self.cleaned_data.get("license_number") or "").strip().upper()
        if not license_number:
            return license_number

        existing = StaffProfile.objects.filter(license_number__iexact=license_number)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError("This license number is already in use.")
        return license_number

    def clean(self):
        """Apply cross-field validation rules for staff updates."""
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        license_number = (cleaned_data.get("license_number") or "").strip()

        licensed_roles = {
            StaffRole.DOCTOR,
            StaffRole.SPECIALIST,
            StaffRole.PHARMACIST,
            StaffRole.LAB_TECH,
            StaffRole.RADIOGRAPHER,
        }

        if role in licensed_roles and not license_number:
            self.add_error("license_number", "License number is required for this staff role.")

        return cleaned_data


class StaffSelfUpdateForm(BaseStyledModelForm):
    class Meta:
        model = StaffProfile
        fields = ['phone_number', 'department']

class PatientRegistrationForm(BaseStyledModelForm):
    """Form for registering and updating patient demographic/profile records."""

    class Meta:
        model = Patient
        fields = [
           
            "first_name",
            "middle_name",
            "last_name",
            "date_of_birth",
            "sex",
            "passport_number",
            "national_id",
            "nationality",
            "tribe",
            "marital_status",
            "insurance_type",
            "religion",
            "location",
            "occupation",
            "phone_number",
            "email",
            "address",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_patient_number(self):
        """Normalize and validate patient number uniqueness with a clear message."""
        patient_number = (self.cleaned_data.get("patient_number") or "").strip().upper()
        existing = Patient.objects.filter(patient_number__iexact=patient_number)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError("This patient number is already in use.")
        return patient_number

    def clean_date_of_birth(self):
        """Validate that date of birth is not in the future and not unrealistic."""
        date_of_birth = self.cleaned_data.get("date_of_birth")
        if not date_of_birth:
            return date_of_birth

        today = date.today()
        if date_of_birth > today:
            raise forms.ValidationError("Date of birth cannot be in the future.")

        max_supported_age_years = 130
        if date_of_birth.year < (today.year - max_supported_age_years):
            raise forms.ValidationError("Please provide a valid date of birth.")

        return date_of_birth

    def clean_email(self):
        """Normalize optional email value for consistent storage."""
        email = (self.cleaned_data.get("email") or "").strip().lower()
        return email
    
    def clean_passport_number(self):
        """Normalize optional passport number for consistent storage."""
        passport = (self.cleaned_data.get("passport_number") or "").strip().upper()
        
        if not passport:
            return None

        existing = Patient.objects.filter(passport_number__iexact=passport)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError("This passport number is already in use.")

        return passport

    def clean_national_id(self):
        """Normalize optional national ID for consistent storage."""
        national_id = (self.cleaned_data.get("national_id") or "").strip().upper()
        
        if not national_id:
            return None

        existing = Patient.objects.filter(national_id__iexact=national_id)
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError("This national ID is already in use.")

        return national_id

    def clean(self):
        """Apply cross-field patient validation rules."""
        cleaned_data = super().clean()
        first_name = (cleaned_data.get("first_name") or "").strip()
        last_name = (cleaned_data.get("last_name") or "").strip()


        if first_name and last_name and first_name.lower() == last_name.lower():
            self.add_error("last_name", "Last name should be different from first name.")

        passport = (cleaned_data.get("passport_number") or "").strip()
        national_id = (cleaned_data.get("national_id") or "").strip()

        if not (cleaned_data.get("patient_number") or passport or national_id):
            raise forms.ValidationError(
                "At least one unique identifier (patient number, passport number, or national ID) must be provided."
            )

        return cleaned_data



class NextOfKinForm(BaseStyledModelForm):
    """Form for capturing patient next-of-kin contact details."""

    class Meta:
        model = NextOfKin
        fields = [
            "slot",
            "full_name",
            "relationship",
            "phone_number",
            "alternative_phone",
            "address",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.patient = kwargs.pop("patient", None)
        super().__init__(*args, **kwargs)

    def clean_slot(self):
        """Validate slot uniqueness per patient when context patient is provided."""
        slot = self.cleaned_data.get("slot")
        patient = self.patient or getattr(self.instance, "patient", None)

        if patient and slot:
            existing = NextOfKin.objects.filter(patient=patient, slot=slot)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise forms.ValidationError("This next-of-kin slot is already used for the selected patient.")

        return slot

    def clean(self):
        """Validate two-contact maximum and basic phone consistency rules."""
        cleaned_data = super().clean()
        patient = self.patient or getattr(self.instance, "patient", None)
        phone_number = (cleaned_data.get("phone_number") or "").strip()
        alternative_phone = (cleaned_data.get("alternative_phone") or "").strip()

        if patient:
            existing = NextOfKin.objects.filter(patient=patient)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.count() >= 2:
                raise forms.ValidationError("A patient cannot have more than 2 next-of-kin records.")

        if alternative_phone and phone_number and alternative_phone == phone_number:
            self.add_error("alternative_phone", "Alternative phone must be different from primary phone number.")

        return cleaned_data


class EncounterForm(BaseStyledModelForm):
    """Form for creating and updating patient encounter records."""
    patient = forms.ModelChoiceField(
        queryset=Patient.objects.all(),
        widget=forms.TextInput(attrs={
            'class': 'form-control patient-autocomplete',
            'data-autocomplete-url': reverse_lazy('patient_autocomplete'),
            'placeholder': 'Type patient number or name',
        }),
        required=True,
        error_messages = {'invalid_choice': 'Please select a valid patient from the list.'}
    )

    class Meta:
        model = Encounter
        fields = [
            "patient",
            "encounter_type",
            "status",
            "attending_doctor",
            "specialist_reviewer",
            "chief_complaint",
            "symptoms",
            "doctor_notes",
            "assessment",
            "plan",
            "specialist_decision",
            "specialist_remarks",
            "specialist_reviewed_at",
            "started_at",
            "ended_at",
        ]
        widgets = {
            "chief_complaint": forms.Textarea(attrs={"rows": 3}),
            "symptoms": forms.Textarea(attrs={"rows": 3}),
            "doctor_notes": forms.Textarea(attrs={"rows": 4}),
            "assessment": forms.Textarea(attrs={"rows": 4}),
            "plan": forms.Textarea(attrs={"rows": 4}),
            "specialist_remarks": forms.Textarea(attrs={"rows": 3}),
            "started_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ended_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "specialist_reviewed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean(self):
        """Validate encounter timeline and specialist review consistency."""
        cleaned_data = super().clean()

        started_at = cleaned_data.get("started_at")
        ended_at = cleaned_data.get("ended_at")
        specialist_decision = cleaned_data.get("specialist_decision")
        specialist_reviewer = cleaned_data.get("specialist_reviewer")
        specialist_reviewed_at = cleaned_data.get("specialist_reviewed_at")
        specialist_remarks = (cleaned_data.get("specialist_remarks") or "").strip()

        if started_at and ended_at and ended_at < started_at:
            self.add_error("ended_at", "Encounter end time cannot be earlier than start time.")

        if specialist_decision != Encounter.SpecialistDecision.PENDING:
            if not specialist_reviewer:
                self.add_error("specialist_reviewer", "Specialist reviewer is required for reviewed decisions.")
            if not specialist_reviewed_at:
                self.add_error("specialist_reviewed_at", "Specialist review date/time is required.")

        if specialist_decision in {
            Encounter.SpecialistDecision.UPDATED,
            Encounter.SpecialistDecision.REJECTED,
        } and not specialist_remarks:
            self.add_error("specialist_remarks", "Remarks are required for updated or rejected decisions.")

        return cleaned_data


class BootstrapAuthenticationForm(AutoBootstrapFormMixin, AuthenticationForm):
    """Authentication form that uses Bootstrap CSS."""

    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(
            {
                "class": "form-control",
                "placeholder": "User name",
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            {
                "class": "form-control",
                "placeholder": "Password",
            }
        ),
    )


class AIDiagnosisSuggestionForm(BaseStyledModelForm):
    """Form used by clinicians to create AI diagnosis suggestions."""

    class Meta:
        model = AIDiagnosisSuggestion
        fields = [
            "diagnosis_name",
            "icd10_code",
            "differential_rank",
            "confidence_score",
            "rationale",
            "source_model",
        ]


class AILabTestSuggestionForm(BaseStyledModelForm):
    """Form used by clinicians to create AI lab test suggestions."""

    class Meta:
        model = AILabTestSuggestion
        fields = [
            "test_name",
            "loinc_code",
            "priority",
            "clinical_question",
            "confidence_score",
            "rationale",
            "source_model",
        ]


class AIMedicationSuggestionForm(BaseStyledModelForm):
    """Form used by clinicians to create AI medication suggestions."""

    class Meta:
        model = AIMedicationSuggestion
        fields = [
            "medication_name",
            "dose",
            "route",
            "frequency",
            "duration",
            "safety_notes",
            "confidence_score",
            "rationale",
            "source_model",
        ]


class AIReviewForm(AutoBootstrapFormMixin, forms.Form):
    """Specialist review form for approving or rejecting AI suggestions."""

    review_status = forms.ChoiceField(
        choices=[
            ("PENDING", "Pending"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
        ],
    )
    reviewer_remarks = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def clean(self):
        """Require specialist remarks when an AI recommendation is rejected."""
        cleaned_data = super().clean()
        review_status = cleaned_data.get("review_status")
        reviewer_remarks = (cleaned_data.get("reviewer_remarks") or "").strip()

        if review_status == "REJECTED" and not reviewer_remarks:
            self.add_error("reviewer_remarks", "Remarks are required when rejecting a suggestion.")

        return cleaned_data

NextOfKinFormSet = inlineformset_factory(
    Patient,
    NextOfKin,
    form=NextOfKinForm,
    extra=2,
    min_num=2,
    max_num=2,
    validate_min=True,
    validate_max=True,
    can_delete=True,
)




class NursePatientRegistrationForm(BaseStyledModelForm):
    """Form for nurses to register and update patient demographic/profile records."""
    class Meta:
        model = Patient
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "date_of_birth",
            "sex",
            "nationality",
            "tribe",
            "marital_status",
            "insurance_type",
            "religion",
            "location",
            "occupation",
            "phone_number",
            "email",
            "address",
            "passport_number",
            "national_id",
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={"type": "date"}),
            'address': forms.Textarea(attrs={"rows": 3}),
        }

class VitalSignsForm(BaseStyledModelForm):
    """Form for recording patient vital signs during an encounter."""
    class Meta:
        model = VitalSigns
        fields = [
            'weight',
            'height',
            'pulse',
            'body_temperature',
        ]

class PrescribedMedicationForm(BaseStyledModelForm):
    """Form for recording prescribed medications during an encounter."""
    class Meta:
        model = PrescribedMedication
        fields = [
            'medication_name',
            'dose',
            
            'frequency',
            'start_date',
            'end_date',
            'notes',
        ]
        widgets ={
            'start_date': forms.DateInput(attrs={"type": "date"}),
            'end_date': forms.DateInput(attrs={"type": "date"}),
        }
