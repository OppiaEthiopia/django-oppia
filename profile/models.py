from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from datarecovery.models import DataRecovery
from oppia.models import Participant, CoursePermissions
import logging
logger = logging.getLogger(__name__)

class UserProfile(models.Model):
    hew_setting = models.CharField(max_length=100, blank=True, null=True, default=None, verbose_name="HEW Setting")
    Profession = models.CharField(max_length=100, blank=True, null=True, default=None, verbose_name="Profession")
    health_post_type = models.CharField(max_length=100, blank=True, null=True, default=None, verbose_name="Health Post Type")
    hew_type = models.CharField(max_length=100, blank=True, null=True, default=None, verbose_name="HEW Type")
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(blank=True, null=True, default=None)
    job_title = models.TextField(blank=True, null=True, default=None)
    grand_father = models.TextField(blank=True, null=True, default=None, verbose_name="Grand Father's Name")
    participant_id = models.TextField(blank=True, null=True, default=None, verbose_name="Participant ID")
    gender = models.TextField(blank=True, null=True, default=None, verbose_name="Gender")
    education_level = models.TextField(blank=True, null=True, default=None, verbose_name="Education Qualification Level")
    region = models.TextField(blank=True, null=True, default=None, verbose_name="Region")
    region_uid = models.TextField(blank=True, null=True, default=None, verbose_name="Region UID")
    zone = models.TextField(blank=True, null=True, default=None, verbose_name="Zone")
    zone_uid = models.TextField(blank=True, null=True, default=None, verbose_name="Zone UID")
    woreda = models.TextField(blank=True, null=True, default=None, verbose_name="Woreda")
    woreda_uid = models.TextField(blank=True, null=True, default=None, verbose_name="Woreda UID")
    phcu = models.TextField(blank=True, null=True, default=None, verbose_name="PHCU Name")
    phcu_uid = models.TextField(blank=True, null=True, default=None, verbose_name="PHCU UID")
    health_post = models.TextField(blank=True, null=True, default=None, verbose_name="Health Post")
    healthpost_uid = models.TextField(blank=True, null=True, default=None, verbose_name="Health Post UID")
    year_of_birth = models.TextField(blank=True, null=True, default=None, verbose_name="Year of Birth")
    year_of_employment = models.TextField(blank=True, null=True, default=None, verbose_name="Year of Employment")
    about = models.TextField(blank=True, null=True, default=None)
    can_upload = models.BooleanField(default=False)
    organisation = models.TextField(blank=True, null=True, default=None)
    phone_number = models.TextField(blank=True, null=True, default=None)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    exclude_from_reporting = models.BooleanField(
        default=False,
        verbose_name=_('Exclude from reporting'),
        help_text=_('If checked, the activity from this user will not be taken into account for summary calculations '
                    'and reports'))

    def get_can_upload(self):
        if self.user.is_staff:
            return True
        manager = CoursePermissions.objects.filter(user=self.user, role=CoursePermissions.MANAGER)
        if manager.exists():
            return True
        return self.can_upload

    def get_can_upload_activitylog(self):
        return self.user.is_staff

    def is_student_only(self):
        if self.user.is_staff:
            return False
        teacher = Participant.objects.filter(user=self.user, role=Participant.TEACHER)
        manager = CoursePermissions.objects.filter(user=self.user, role=CoursePermissions.MANAGER)
        return not teacher.exists() and not manager.exists()

    def is_teacher_only(self):
        if self.user.is_staff:
            return False
        teacher = Participant.objects.filter(user=self.user, role=Participant.TEACHER)
        manager = CoursePermissions.objects.filter(user=self.user, role=CoursePermissions.MANAGER)
        return teacher.exists() and not manager.exists()

    def update_customfields(self, fields_dict):
        print('hi')
        errors = []
        custom_fields = CustomField.objects.all()

        # Extract training_date, training_location, and module_type from fields_dict
        training_date = fields_dict.get('training_date')
        training_location = fields_dict.get('training_location') or fields_dict.get('training_center')
        module_type = fields_dict.get('module_type')

        training_info = None
        print(f"training_date: {training_date}, training_location: {training_location}, module_type: {module_type}")
        
        if training_date and (module_type or training_location):
            # Convert to date if it's a datetime or string
            import datetime
            if isinstance(training_date, datetime.datetime):
                training_date = training_date.date()
            elif isinstance(training_date, str):
                parsed = False
                # Try ISO format first
                try:
                    training_date = datetime.datetime.fromisoformat(training_date).date()
                    parsed = True
                except Exception:
                    pass
                # Try common US and EU date formats if not parsed
                if not parsed:
                    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y"):
                        try:
                            training_date = datetime.datetime.strptime(training_date, fmt).date()
                            parsed = True
                            break
                        except Exception:
                            continue
                if not parsed:
                    print(f"Could not parse training_date: {training_date}")
            training_info, _ = TrainingInfo.objects.get_or_create(
                training_date=training_date,
                module_type=module_type,
                defaults={"training_location": training_location}
            )

        for custom_field in custom_fields:
            if custom_field.id in fields_dict and (
                (fields_dict[custom_field.id] != '' and fields_dict[custom_field.id] is not None)
                    or custom_field.required is True
            ):
                profile_field, created = UserProfileCustomField.objects.get_or_create(
                    key_name=custom_field,
                    user=self.user,
                    training_info=training_info
                )

                if custom_field.type == 'int':
                    profile_field.value_int = fields_dict.get(custom_field.id, None)
                elif custom_field.type == 'bool':
                    profile_field.value_bool = fields_dict.get(custom_field.id, None)
                else:
                    profile_field.value_str = fields_dict.get(custom_field.id, None)

                profile_field.save()

        missing_fields = [field for field in fields_dict if field not in custom_fields.values_list('id', flat=True).all()]
        if missing_fields:
            errors.append(DataRecovery.Reason.CUSTOM_PROFILE_FIELDS_NOT_DEFINED_IN_THE_SERVER + str(missing_fields))

        return errors

    def get_customfields_dict(self):
        profile_fields = {}
        custom_fields = CustomField.objects.all()
        for custom_field in custom_fields:
            value = UserProfileCustomField.get_user_value(self.user, custom_field)
            if value is not None:
                profile_fields[custom_field.id] = value

        return profile_fields


class CustomField(models.Model):

    DATA_TYPES = (
        ('str', 'String'),
        ('int', 'Integer'),
        ('bool', 'Boolean')
    )

    id = models.CharField(max_length=100, primary_key=True, editable=True)
    label = models.CharField(max_length=200, null=False, blank=False)
    required = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    helper_text = models.TextField(blank=True, null=True, default=None)
    type = models.CharField(max_length=10, choices=DATA_TYPES, null=False, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.id


class TrainingInfo(models.Model):
    id = models.AutoField(primary_key=True)
    training_date = models.DateField()
    created_date = models.DateTimeField(auto_now_add=True)
    module_type = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        unique_together = ['training_date', 'module_type']

    def __str__(self):
        return f"{self.module_type or self.training_location} on {self.training_date}"


class UserProfileCustomField(models.Model):
    key_name = models.ForeignKey(CustomField, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value_str = models.TextField(blank=True, null=True, default=None)
    value_int = models.IntegerField(blank=True, null=True, default=None)
    value_bool = models.BooleanField(null=True, default=None)
    training_info = models.ForeignKey(TrainingInfo, on_delete=models.CASCADE, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['key_name', 'user', 'training_info']

    def __str__(self):
        return self.key_name.id + ": " + self.user.username

    @staticmethod
    def get_user_value(user, key_name):
        try:
            return UserProfileCustomField.objects.get(key_name=key_name, user=user).get_value()
        except UserProfileCustomField.DoesNotExist:
            return None

    def get_value(self):
        if self.value_bool is not None:
            return self.value_bool
        elif self.value_int is not None:
            return self.value_int
        else:
            return self.value_str
