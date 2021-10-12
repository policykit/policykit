import logging

import requests
from django.conf import settings
import json
import integrations.metagov.api as MetagovAPI

logger = logging.getLogger(__name__)


class MetagovProcessData(object):
    def __init__(self, obj):
        self.status = obj.get("status")
        self.errors = obj.get("errors")
        self.outcome = obj.get("outcome")


class Metagov:
    """
    Metagov client library to be exposed to policy author
    """

    def __init__(self, proposal):
        self.proposal = proposal
        self.headers = {"X-Metagov-Community": proposal.policy.community.metagov_slug}

    def start_process(self, process_name, payload) -> MetagovProcessData:
        """
        Kick off a governance process in Metagov. Store the process URL and data on the `proposal`
        """
        logger.debug(f"Starting Metagov process '{process_name}' for {self.proposal}\n{payload}")

        url = f"{settings.METAGOV_URL}/api/internal/process/{process_name}"
        payload["callback_url"] = f"{settings.SERVER_URL}/metagov/internal/outcome/{self.proposal.pk}"

        # Kick off process in Metagov
        response = requests.post(url, json=payload, headers=self.headers)
        if not response.ok:
            raise Exception(f"Error starting process: {response.status_code} {response.reason} {response.text}")
        location = response.headers.get("location")
        if not location:
            raise Exception("Response missing location header")

        self.proposal.governance_process_url = f"{settings.METAGOV_URL}{location}"

        response = requests.get(self.proposal.governance_process_url)
        if not response.ok:
            raise Exception(f"Error getting process: {response.status_code} {response.reason} {response.text}")
        logger.debug(response.text)

        # store the outcome data on the proposal
        self.proposal.governance_process_json = response.text
        self.proposal.save()
        return self.get_process()

    def close_process(self) -> MetagovProcessData:
        """
        Close a GovernanceProcess in Metagov, and store the latest outcome data
        """
        location = self.proposal.governance_process_url
        if not location:
            return

        logger.debug(f"{self.proposal} making request to close process at '{location}'")
        response = requests.delete(location)
        if not response.ok:
            logger.error(f"Error closing process: {response.status_code} {response.reason} {response.text}")
            return
        logger.debug(f"Closed governance process: {response.text}")
        self.proposal.governance_process_json = response.text
        self.proposal.save()

        return self.get_process()

    def get_process(self) -> MetagovProcessData:
        json_data = self.proposal.governance_process_json
        if json_data:
            data = json.loads(json_data)
            return MetagovProcessData(data)

    def perform_action(self, name, parameters):
        """
        Perform an action through Metagov. If the requested action belongs to a plugin that is
        not active for the current community, this will throw an exception.
        """
        return MetagovAPI.perform_action(
            community_slug=self.proposal.policy.community.metagov_slug,
            name=name,
            parameters=parameters
        )
