.. _start:

Community
====================================

| **Attributes**

+----------------+----------------------------------------------------+
| community_name | The name of the community.                         |
+----------------+----------------------------------------------------+
| platform       | The name of the platform ("Slack", "Reddit", etc.) |
+----------------+----------------------------------------------------+
| base_role      | The default role which users have.                 |
+----------------+----------------------------------------------------+

| **Functions**

+--------------------------------------+-------------------------------------------------------------------+
| notify_action(action, policy, users) | Sends a notification to users of a pending action.                |
+--------------------------------------+-------------------------------------------------------------------+
| get_roles()                          | Returns a QuerySet of all roles in the community.                 |
+--------------------------------------+-------------------------------------------------------------------+
| get_platform_policies()              | Returns a QuerySet of all platform policies in the community.     |
+--------------------------------------+-------------------------------------------------------------------+
| get_constitution_policies()          | Returns a QuerySet of all constitution policies in the community. |
+--------------------------------------+-------------------------------------------------------------------+
| get_documents()                      | Returns a QuerySet of all documents in the community.             |
+--------------------------------------+-------------------------------------------------------------------+
