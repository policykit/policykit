.. _start:

Proposal
===============

| **Attributes**

+---------------+---------------------------------------------+
| author        | The user who created the proposal.          |
+---------------+---------------------------------------------+
| proposal_time | The datetime that the proposal was created. |
+---------------+---------------------------------------------+
| status        | PROPOSED, PASSED or FAILED.                 |
+---------------+---------------------------------------------+

| **Functions**

+-----------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_time_elapsed()                      | Returns a datetime object representing the time elapsed since the proposal's creation.                                                                                                                |
+-----------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_all_boolean_votes(users=None)       | For Boolean voting. Returns all boolean votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.                   |
+-----------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_yes_votes(users=None)               | For Boolean voting. Returns the yes votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.                       |
+-----------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_no_votes(users=None)                | For Boolean voting. Returns the no votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.                        |
+-----------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_all_number_votes(users=None)        | For Number voting. Returns all number votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.                     |
+-----------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_one_number_votes(value, users=None) | For Number voting. Returns number votes for the specified value as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted. |
+-----------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| save(\*args, \*\*kwargs)                | Saves the proposal. Note: Only meant for internal use.                                                                                                                                                |
+-----------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
