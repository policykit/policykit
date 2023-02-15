.. _start:

Design Overview
====================================


Data Model
~~~~~~~~~~~~~~~~~~~~

* The top-level Community represents a group of users that may exist on 1 or more platforms.

* Each Community has at least 2 CommunityPlatforms: the initial platform (eg SlackCommunity) and the policykit platform (ConstitutionCommunity). All actions proposed on the PolicyKit platform that are "constitutional" (eg changing a policy, creating a role, etc) are linked to the community's ConstitutionCommunity.

* Each Policy in a community is tied to 1 or more Action Types. For Platform Policies and Constitution Policies, the action type indicates which action type the policy **governs**. For Trigger Policies, the action type indicates which action types trigger the policy to evaluate. When a Policy is evaluated against an Action, a ``Proposal`` record is created to store any data relevant to the policy evaluation.

* ``CommunityRole`` is tied to ``Community`` (not ``CommunityPlatform``) because it may determine the ability to propose/execute governable actions, which may occur on any platform. A given ``CommunityRole`` may be assigned to CommunityUsers on multiple platforms (which in some cases may be the same person, eg "alice123" on Discourse and "alice" on Slack).


.. raw:: html

    <div style="width: 640px; height: 480px; margin: 10px; position: relative;">
        <iframe allowfullscreen frameborder="0" style="width:640px; height:480px" src="https://lucid.app/documents/embeddedchart/4d388a65-b276-4ef1-8cd1-6e15f70b385f" id="vTqymK2v-ck~">
        </iframe>
    </div>



Policy Engine Evaluation Loop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This diagram shows what happens when a new Action is created, and how the Policy engine decides whether to perform a policy evaluation for it.
This diagram does not include the policy evaluation checker task, which periodically re-evaluates all Proposals that are in "PROPOSED" state.


.. raw:: html

    <div style="width: 640px; height: 480px; margin: 10px; position: relative;">
        <iframe allowfullscreen frameborder="0" style="width:640px; height:480px" src="https://lucid.app/documents/embeddedchart/81b83e2d-890b-4e63-be47-638f9b98d582" id="y.tyq_4oL77u">
        </iframe>
    </div>


