import csv

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from profile.models import UserProfileCustomField, CustomField, UserProfile


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
                
                # update phone no
                user_profile = UserProfile.objects.get(user=user)
                if user_profile.phone_number == "" or user_profile.phone_number is None:
                    user_profile.phone_number = row.get('phone_number')
                    user_profile.save()
                    print("%s: phone_number updated to %s" % (row.get("username"), row.get('phone_number')))
                
                for cf in custom_fields:
                    try:
                        upcf = UserProfileCustomField.objects.get(user=user, key_name=cf.id)
                    except UserProfileCustomField.DoesNotExist:
                        upcf = UserProfileCustomField(user=user, key_name=cf)
                        print("%s: adding customfield record for %s" % (row.get("username"), cf.id))

                    if cf.type == 'str' and (upcf.value_str is None or upcf.value_str == ""):
                        upcf.value_str = row.get(cf.id)
                        upcf.save()
                        print("%s: %s updated to %s" % (row.get("username"), cf.id, row.get(cf.id)))
                    if cf.type == 'int' and (upcf.value_int is None or upcf.value_int ==  ""):
                        upcf.value_int = row.get(cf.id)
                        upcf.save()
                        print("%s: %s updated to %s" % (row.get("username"), cf.id, row.get(cf.id)))
        
        # Fix participant ids
        upcfs = UserProfileCustomField.objects.filter(key_name="participant_id")
        for participant in upcfs:
            if participant.value_str is not None and len(participant.value_str) < 4:
                participant.value_str = str(participant.value_str).zfill(4)
                participant.save()
                print("%s: participant_id updated to %s" % (participant.user.username, participant.value_str))
                
                
                
        