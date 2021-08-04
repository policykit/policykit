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

#### PLUGIN MANAGEMENT ####
plugin_base = f"{settings.METAGOV_URL}/api/internal/plugin"

def enable_plugin(community_slug, name, config):
    headers = {"X-Metagov-Community": community_slug}
    response = requests.post(f"{plugin_base}/{name}", json=config, headers=headers)
    if not response.ok:
        raise Exception(response.text or "Unknown error")
    return response.json()

def delete_plugin(name: str, id):
    response = requests.delete(f"{plugin_base}/{name}/{id}")
    if not response.ok and response.status_code != 404:
        raise Exception(response.text or "Unknown error")

#### SCHEMAS ####

def get_plugin_config_schemas():
    url = f"{settings.METAGOV_URL}/api/internal/plugin-schemas"
    response = requests.get(url)
    if not response.ok:
        raise Exception(response.text or "Unknown error")
    return response.json()

def get_plugin_metadata(plugin):
    url = f"{settings.METAGOV_URL}/api/internal/plugin/{plugin}/metadata"
    response = requests.get(url)
    if not response.ok:
        raise Exception(response.text or "Unknown error")
    return response.json()
