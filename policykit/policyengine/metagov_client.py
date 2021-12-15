import logging

logger = logging.getLogger(__name__)

from policyengine.metagov_app import metagov


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
        self.metagov_slug = proposal.policy.community.metagov_slug

    def start_process(self, process_name, **kwargs) -> MetagovProcessData:
        """
        Kick off a governance process in Metagov. Store the process URL and data on the `proposal`
        """

        community = metagov.get_community(self.metagov_slug)
        plugin_name, process_name = process_name.split(".")
        plugin = community.get_plugin(plugin_name)
        process = plugin.start_process(process_name, **kwargs)

        # TODO set community_post to URL!

        # store reference to process on the proposal
        self.proposal.governance_process = process
        self.proposal.save()
        return process

    def close_process(self) -> MetagovProcessData:
        """
        Close a GovernanceProcess in Metagov, and store the latest outcome data
        """
        process = self.proposal.governance_process
        if process is None:
            return
        process = process.proxy
        try:
            process.close()
        except NotImplementedError:
            pass
        else:
            logger.debug(f"Closed governance process: {process.outcome}")
        return process

    def get_process(self) -> MetagovProcessData:
        if self.proposal.governance_process is None:
            return None
        process = self.proposal.governance_process
        data = {"status": process.status, "outcome": process.outcome, "errors": process.errors}
        return MetagovProcessData(data)

    def perform_action(self, name, **kwargs):
        """
        Perform an action through Metagov. If the requested action belongs to a plugin that is
        not active for the current community, this will throw an exception.
        """
        community = metagov.get_community(self.metagov_slug)
        plugin_name, action_id = name.split(".")

        return community.perform_action(
            plugin_name, action_id, parameters=kwargs, community_platform_id=None  # FIXME pass team_id?
        )
