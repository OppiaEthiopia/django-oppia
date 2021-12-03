import csv

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from profile.models import UserProfileCustomField, CustomField


class Command(BaseCommand):
    help = 'Script to re-upload and fix users with missing profile data'

    def add_arguments(self, parser):

        parser.add_argument(
            '--filepath',
            dest='filepath',
            help='user file to upload',
        )

    def handle(self, *args, **options):

        custom_fields = CustomField.objects.all()
        
        with open(options['filepath'], newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:                
                # check the user exists in db
                try:
                    user = User.objects.get(username=row.get('username'))
                except User.DoesNotExist:
                    print("user not found: ",row.get('username'))
                    continue
                
                for cf in custom_fields:
                    try:
                        upcf = UserProfileCustomField.objects.get(user=user, key_name=cf.id)
                    except UserProfileCustomField.DoesNotExist:
                        continue   
                    if cf.type == 'str' and upcf.value_str is None:
                        upcf.value_str = row.get(cf.id)
                        upcf.save()
                        print("%s: %s updated to %s" % (row.get("username"), cf.id, row.get(cf.id)))
                    if cf.type == 'int' and upcf.value_int is None:
                        upcf.value_int = row.get(cf.id)
                        upcf.save()
                        print("%s: %s updated to %s" % (row.get("username"), cf.id, row.get(cf.id)))
        