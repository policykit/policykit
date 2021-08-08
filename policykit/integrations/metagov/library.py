import logging

import requests
from django.conf import settings
import json

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

    def __init__(self, evaluation):
        self.evaluation = evaluation
        self.headers = {"X-Metagov-Community": evaluation.policy.community.metagov_slug}

    def start_process(self, process_name, payload) -> MetagovProcessData:
        """
        Kick off a governance process in Metagov. Store the process URL and data on the `evaluation`
        """
        logger.debug(f"Starting Metagov process '{process_name}' for {self.evaluation}\n{payload}")

        url = f"{settings.METAGOV_URL}/api/internal/process/{process_name}"
        payload["callback_url"] = f"{settings.SERVER_URL}/metagov/internal/outcome/{self.evaluation.pk}"

        # Kick off process in Metagov
        response = requests.post(url, json=payload, headers=self.headers)
        if not response.ok:
            raise Exception(f"Error starting process: {response.status_code} {response.reason} {response.text}")
        location = response.headers.get("location")
        if not location:
            raise Exception("Response missing location header")

        self.evaluation.governance_process_url = f"{settings.METAGOV_URL}{location}"

        response = requests.get(self.evaluation.governance_process_url)
        if not response.ok:
            raise Exception(f"Error getting process: {response.status_code} {response.reason} {response.text}")
        logger.debug(response.text)

        # store the outcome data on the evaluation
        self.evaluation.governance_process_json = response.text
        self.evaluation.save()
        return self.get_process()

    def close_process(self) -> MetagovProcessData:
        """
        Close a GovernanceProcess in Metagov, and store the latest outcome data
        """
        location = self.evaluation.governance_process_url
        if not location:
            return

        logger.debug(f"{self.evaluation} making request to close process at '{location}'")
        response = requests.delete(location)
        if not response.ok:
            logger.error(f"Error closing process: {response.status_code} {response.reason} {response.text}")
            return
        logger.debug(f"Closed governance process: {response.text}")
        self.evaluation.governance_process_json = response.text
        self.evaluation.save()

        return self.get_process()

    def get_process(self) -> MetagovProcessData:
        json_data = self.evaluation.governance_process_json
        if json_data:
            data = json.loads(json_data)
            return MetagovProcessData(data)

    def perform_action(self, name, parameters):
        """
        Perform an action through Metagov. If the requested action belongs to a plugin that is
        not active for the current community, this will throw an exception.
        """
        url = f"{settings.METAGOV_URL}/api/internal/action/{name}"
        response = requests.post(url, json={"parameters": parameters}, headers=self.headers)
        if not response.ok:
            raise Exception(
                f"Error performing action {name}: {response.status_code} {response.reason} {response.text}"
            )
        data = response.json()
        return data
