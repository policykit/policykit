import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


#### COMMUNITY MANAGEMENT ####
community_base = f"{settings.METAGOV_URL}/api/internal/community"


def delete_community(name: str):
    response = requests.delete(f"{community_base}/{name}")
    if not response.ok and response.status_code != 404:
        raise Exception(response.text or "Unknown error")


def create_empty_metagov_community(readable_name=""):
    payload = {"readable_name": readable_name, "plugins": []}
    response = requests.post(f"{community_base}", json=payload)
    if not response.ok:
        raise Exception(response.text or "Unknown error")
    return response.json()



def update_metagov_community(community, plugins=[]):
    if not community.metagov_slug:
        raise Exception(f"no metagov slug for {community}")

    payload = {"slug": community.metagov_slug, "readable_name": community.community_name, "plugins": plugins}
    response = requests.put(f"{community_base}/{community.metagov_slug}", json=payload)
    if not response.ok:
        raise Exception(response.text or "Unknown error")
    return response.json()


def get_metagov_community(slug):
    response = requests.get(f"{community_base}/{slug}")
    if not response.ok:
        raise Exception(response.text or "Unknown error")
    return response.json()


#### SCHEMAS ####


def get_webhooks(community):
    url = f"{settings.METAGOV_URL}/api/internal/community/{community.metagov_slug}/hooks"
    response = requests.get(url)
    if not response.ok:
        raise Exception(response.text or "Unknown error")
    data = response.json()
    return [f"{settings.METAGOV_URL}{hook}" for hook in data["hooks"]]


def get_plugin_config_schemas():
    url = f"{settings.METAGOV_URL}/api/internal/plugin-schemas"
    response = requests.get(url)
    if not response.ok:
        raise Exception(response.text or "Unknown error")
    return response.json()
