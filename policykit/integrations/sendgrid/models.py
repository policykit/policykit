import logging
from django.db import models
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from policyengine.models import CommunityPlatform

sendgrid_settings = settings.METAGOV_SETTINGS["SENDGRID"]
SENDGRID_API_KEY = sendgrid_settings["API_KEY"]

logger = logging.getLogger(__name__)


class OpencollectiveCommunity(CommunityPlatform):
    platform = "sendgrid"

    @staticmethod
    def validate_input_schema(input: dict):
        input_schema = {
            "type": "object",
            "properties": {
                "from_email": {
                    "description": "Address email being sent from",
                    "type": "string"
                },
                "to_email": {
                    "description": "Address email being sent to",
                    "type": "string"
                },
                "subject": {
                    "description": "Subject of the email",
                    "type": "string"
                },
                "html_content": {
                    "description": "Text of the email body in HTML format",
                    "type": "string"
                }
            },
            "required": ["from", "to", "subject", "html_content"]
        }

        if sorted(list(input_schema["properties"].keys())) != sorted(list(input.keys())):
            logger.error("Input validation failed!")
            return False

        for key, key_type in input.items():
            if type(key_type) != str:
                logger.error("Input validation failed!")
                return False
        logger.info("Input validation successful!")
        return True

    def send_message(self, **kwargs):
        """
            kwargs_struct = {
                "to_emails": "to@example.com",
                "from_email": "from_email@example.com",
                "subject": "Sending with Twilio SendGrid is Fun",
                "html_content": "<strong>and easy to do anywhere, even with Python</strong>"
                }
        """
        if not validate_input_schema(input_schema):
            return False

        message = Mail(**kwargs)
        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)
            logger.info(response.status_code, response.body)
            if response.status_code != 202:
                logger.error("There was error sending email")
                return False
            return True
        except Exception as e:
            logger.error(e.message)
            return False
