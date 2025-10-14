import csv
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from profile.models import UserProfile, UserProfileCustomField, CustomField

from profile.models import TrainingInfo

class Command(BaseCommand):
    help = 'Migrate user profile data from CSV to new UserProfile fields and custom fields.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file to import')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            expected_fields = [
                'id', 'about', 'can_upload', 'organisation', 'phone_number', 'user_id', 'created', 'modified', 'exclude_from_reporting',
                'age', 'education_level', 'email', 'gender', 'grand_father', 'health_post', 'healthpost_uid', 'participant_id', 'phcu', 'phcu_uid',
                'region', 'region_uid', 'woreda', 'woreda_uid', 'year_of_birth', 'year_of_employment', 'zone', 'zone_uid', 'profession', 'health_post_type', 'hew_setting'
            ]
            for row in reader:
                username = row.get('user_name')
                if not username:
                    self.stdout.write(self.style.WARNING('No user_name found in row, skipping'))
                    continue
                try:
                    user = User.objects.get(username=username)
                    
                except User.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'user_name "{username}" not found in auth_user, skipping row'))
                    continue
                # User exists, proceed with migration
                try:
                    profile = UserProfile.objects.get(user=user)
                    # Update existing profile
                    for field in expected_fields:
                        if field == 'user_id':
                            continue  # Do not set user_id from CSV
                        if field in row:
                            setattr(profile, field, row[field])
                    profile.save()
                    
                except UserProfile.DoesNotExist:
                    # Create new profile
                    profile = UserProfile(user=user)
                    for field in expected_fields:
                        if field == 'user_id':
                            continue  # Do not set user_id from CSV
                        if field in row:
                            setattr(profile, field, row[field])
                    profile.save()
                    self.stdout.write(self.style.SUCCESS(f"Saved UserProfile for user_name '{username}' with user_id {user.id}"))
                # Create TrainingInfo if training fields are present (no prefix)
                training_fields = ['training_date', 'created_date', 'id', 'module_type']
                training_data = {}
                for f in training_fields:
                    val = row.get(f)
                    if val and val != 'NULL':
                        if f == 'training_date':
                            date_val = val.split(',')[0].strip() if ',' in val else val.strip()
                            import re
                            import datetime
                            iso_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
                            if not iso_pattern.match(date_val):
                                converted = None
                                for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%m-%d-%Y", "%d-%m-%Y"):
                                    try:
                                        converted = datetime.datetime.strptime(date_val, fmt).strftime("%Y-%m-%d")
                                        # Only log when new TrainingInfo is created below
                                        break
                                    except Exception:
                                        continue
                                if converted:
                                    training_data[f] = converted
                                else:
                                    training_data[f] = date_val
                            else:
                                training_data[f] = date_val
                        else:
                            training_data[f] = val
                training_info = None
                training_date = training_data.get('training_date')
                module_type = training_data.get('module_type')
                if training_date and module_type:
                    training_info = TrainingInfo.objects.filter(training_date=training_date, module_type=module_type).first()
                    if not training_info:
                        # Remove 'module_type' from training_data if present to avoid duplicate argument
                        training_data_clean = dict(training_data)
                        training_data_clean.pop('module_type', None)
                        training_info = TrainingInfo.objects.create(
                            module_type=module_type,
                            **training_data_clean
                        )
                        self.stdout.write(self.style.SUCCESS(f"Created new TrainingInfo with id {training_info.id} for user_id {user.id}, training_date {training_date}, module_type {module_type}"))
                # Only create UserProfileCustomField for key_name_id values that already exist in CustomField
                available_customfields = set(CustomField.objects.values_list('id', flat=True))
                for field in expected_fields:
                    if field in row and field in available_customfields:
                        cf = CustomField.objects.get(id=field)
                        # Use training_info as part of uniqueness
                        upcf, created = UserProfileCustomField.objects.get_or_create(
                            user=user, key_name=cf, training_info_id=training_info.id if training_info else None
                        )
                        upcf.value_str = str(row[field]) if row[field] not in [None, ''] else None
                        if upcf.value_str not in [None, '']:
                            upcf.save()
                # Migrate custom fields (no prefix logic)
                for key in row:
                    value = row[key]
                    if key in available_customfields:
                        cf, _ = CustomField.objects.get_or_create(id=key)
                        field_type = getattr(cf, 'type', 'str')
                        # Use training_info as part of uniqueness
                        upcf, _ = UserProfileCustomField.objects.get_or_create(
                            user=user, key_name=cf, training_info_id=training_info.id if training_info else None
                        )
                        if field_type == 'int':
                            try:
                                upcf.value_int = int(value)
                            except (ValueError, TypeError):
                                upcf.value_int = None
                        elif field_type == 'bool':
                            upcf.value_bool = str(value).lower() in ['true', '1', 'yes']
                        else:
                            upcf.value_str = str(value)
                        # Always save the custom field, even if all value fields are null/empty
                        upcf.save()
        self.stdout.write(self.style.SUCCESS('User profile migration from CSV completed.'))
