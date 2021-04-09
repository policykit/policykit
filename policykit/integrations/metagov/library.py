import json
import logging

import requests
from django.conf import settings
from django.utils.text import slugify
from integrations.metagov.models import ExternalProcess
from policyengine.models import Community

logger = logging.getLogger(__name__)


def metagov_slug(community: Community):
    """
    Get the unique slug used to identify this community in Metagov.
    """
    return slugify(f"{community.platform} {community.team_id}")


def update_metagov_community(community: Community, plugins=[]):
    metagov_name = metagov_slug(community)
    payload = {"name": metagov_name, "readable_name": community.community_name, "plugins": plugins}
    url = f"{settings.METAGOV_URL}/api/internal/community/{metagov_name}"
    response = requests.put(url, json=payload)
    if not response.ok:
        raise Exception(response.text or "Unknown error")
    data = response.json()
    return data

def get_metagov_community(community: Community):
    url = f"{settings.METAGOV_URL}/api/internal/community/{metagov_slug(community)}"
    response = requests.get(url)
    if not response.ok:
        logger.error(response.text)
        return None
    return response.json()

class DecisionResult(object):
    def __init__(self, obj):
        self.status = obj.get("status")
        self.errors = obj.get("errors")
        self.outcome = obj.get("outcome")


class Metagov:
    """
    Metagov client library to be exposed to policy author
    """

    def __init__(self, policy, action):
        self.policy = policy
        self.action = action
        self.headers = {"X-Metagov-Community": metagov_slug(policy.community)}

    def start_process(self, process_name, payload):
        """
        Kick off a governance process in metagov, and pass along a callback_url to
        be invoked whent the process completes.
        """
        model = ExternalProcess.objects.create(policy=self.policy, action=self.action)

        url = f"{settings.METAGOV_URL}/api/internal/process/{process_name}"
        payload["callback_url"] = f"{settings.SERVER_URL}/metagov/outcome/{model.pk}"
        logger.info(f"Making request to start '{process_name}' with payload: {payload}")
        response = requests.post(url, json=payload, headers=self.headers)
        if not response.ok:
            raise Exception(f"Error starting process: {response.status_code} {response.reason} {response.text}")
        location = response.headers.get("location")
        if not location:
            raise Exception("Response missing location header")
        model.location = location
        model.save()

        resource_url = f"{settings.METAGOV_URL}{location}"
        response = requests.get(resource_url)
        if not response.ok:
            raise Exception(f"Error getting process data: {response.status_code} {response.reason} {response.text}")
        data = response.json()
        logger.info(f"External process created: {data}")
        return data.get("data", None)

    def close_process(self) -> DecisionResult:
        try:
            model = ExternalProcess.objects.get(policy=self.policy, action=self.action)
        except ExternalProcess.DoesNotExist:
            raise Exception("ExternalProcess not found")
        if not model.location:
            raise Exception("ExternalProcess missing location")
        logger.info(f"Making request to close process at '{model.location}'")
        resource_url = f"{settings.METAGOV_URL}{model.location}"
        response = requests.delete(resource_url)
        if not response.ok:
            raise Exception(f"Error getting process data: {response.status_code} {response.reason} {response.text}")
        data = response.json()
        logger.info(f"External process closed: {data}")
        assert data.get("status") == "completed"
        return DecisionResult(data)

    def get_process_outcome(self) -> DecisionResult:
        model = ExternalProcess.objects.filter(policy=self.policy, action=self.action).first()
        if model and model.json_data:
            data = json.loads(model.json_data)
            # json_data is only present when external process is completed
            assert data.get("status") == "completed"
            return DecisionResult(data)
        return None

    def get_resource(self, resource_name, payload):
        url = f"{settings.METAGOV_URL}/api/internal/resource/{resource_name}"
        response = requests.get(url, params=payload, headers=self.headers)
        if not response.ok:
            raise Exception(f"Error getting resource: {response.status_code} {response.reason} {response.text}")
        data = response.json()
        return data

    def perform_action(self, action_type, parameters):
        """
        Perform an action through Metagov. If the requested action belongs to a plugin that is
        not active for the current community, this will throw an exception.
        """
        url = f"{settings.METAGOV_URL}/api/internal/action/{action_type}"
        response = requests.post(url, json={"parameters": parameters}, headers=self.headers)
        if not response.ok:
            raise Exception(f"Error performing action: {response.status_code} {response.reason} {response.text}")
        data = response.json()
        return data
