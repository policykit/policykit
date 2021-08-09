from django.core.management.base import BaseCommand
from policyengine.models import Policy
import json
import datetime
from pathlib import Path

class Command(BaseCommand):
    help = 'Downloads all policies as text files, in a format that can be uploaded in the PolicyKit UI'

    def handle(self, *args, **options):
        # if Policy.objects.all().count() == 0:
        #     self.stdout.write(self.style.NOTICE(f"No policies to download."))
        #     return
        
        dirname = f"policy_backups/{datetime.datetime.now().isoformat()}"
        Path(dirname).mkdir(parents=True, exist_ok=True)

        print(f"Downloading policies to directory: {dirname}")

        def download(policy):
            prefix = f"{policy.community.platform}_{policy.community.team_id}_"
            filename = prefix + policy.name.replace(" ", "_")
            self.stdout.write(self.style.SUCCESS(f"Saving: {filename}"))
            data = {
                "name": policy.name,
                "description": policy.description,
                "filter": policy.filter,
                "initialize": policy.initialize,
                "check": policy.check,
                "notify": policy.notify,
                "success": policy.success,
                "fail": policy.fail,
            }
            jsonString = json.dumps(data, indent=4)
            jsonFile = open(f"{dirname}/{filename}.json", "w")
            jsonFile.write(jsonString)
            jsonFile.close()
        
        for policy in Policy.objects.all():
            download(policy)

            