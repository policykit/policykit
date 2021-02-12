import logging
import requests
import json
from django.conf import settings

logger = logging.getLogger('django')


def start_process(policy, action, process_name, payload):
    from policyengine.models import ExternalProcess
    model = ExternalProcess.objects.create(
        name=process_name,
        policy=policy,
        action=action
    )

    url = f"{settings.METAGOV_URL}/api/internal/process"
    payload['process_name'] = process_name
    payload['callback_url'] = f"{settings.SERVER_URL}/outcome/{model.pk}"
    logger.info(payload)
    response = requests.post(url, json=payload)
    location = response.headers.get('location')

    if not response.ok:
        logger.error(f"Error starting process: {response.status_code} {response.text}")
        return None  # FIXME handle

    if not location:
        logger.error(f"Response missing location header")
        return None

    logger.info(f"Metagov process started at location {location}")
    resource_url = f"{settings.METAGOV_URL}{location}"
    response = requests.get(resource_url)
    if not response.ok:
        logger.error(f"Error getting process data: {response.status_code} {response.text}")
        return None  # FIXME handle
    data = response.json()
    logger.info(data)
    return data.get('data', None)


def get_process_outcome(policy, action):
    from policyengine.models import ExternalProcess
    model = ExternalProcess.objects.filter(
        policy=policy, action=action).first()
    if model is not None and model.outcome is not None:
        return json.loads(model.outcome)
    return dict()


def get_resource(resource_name, payload):
    url = f"{settings.METAGOV_URL}/api/internal/resource/{resource_name}"
    response = requests.get(url, params=payload)
    if not response.ok:
        logger.error(f"Error getting resource: {response.status_code} {response.text}")
        return  # FIXME handle
    data = response.json()
    return data


class MetagovClient:
    def __init__(self, policy, action):
        self.policy = policy
        self.action = action

    def start_process(self, *args, **kwargs):
        return start_process(self.policy, self.action, *args, **kwargs)

    def get_process_outcome(self):
        return get_process_outcome(self.policy, self.action)

    def get_resource(self, *args, **kwargs):
        return get_resource(*args, **kwargs)
