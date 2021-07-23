"""
Helper script for downloading all policies for all communities.

Run with:

python manage.py shell
exec(open('scripts/download_all_policies.py').read())
"""

from policyengine.models import BasePolicy
import json
import os
import datetime


dirname = f"downloaded_policies_{datetime.datetime.now().isoformat()}"
os.mkdir(dirname)
print(f"Downloading policies to directory: {dirname}")

def download(policy):
    prefix = f"{policy.community.platform}_{policy.community.team_id}_"
    filename = prefix + policy.name.replace(" ", "_")
    print(f"Saving: {filename}")
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

for policy in BasePolicy.objects.all():
    download(policy)
