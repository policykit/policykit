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

+-------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| time_elapsed()                      | Returns a datetime object representing the time elapsed since the proposal's creation.                                                                                                                    |
+-------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_num_yes_votes(users=None)       | For Boolean voting. Returns the number of yes votes as an integer. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.                 |
+-------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_num_no_votes(users=None)        | For Boolean voting. Returns the number of no votes as an integer. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.                  |
+-------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_yes_votes(users=None)           | For Boolean voting. Returns the yes votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.                           |
+-------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_no_votes(users=None)            | For Boolean voting. Returns the no votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.                            |
+-------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_number_votes(value, users=None) | For Number voting. Returns the votes for the specified number value as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted. |
+-------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| save(\*args, \*\*kwargs)            | Saves the proposal. Note: Only meant for internal use.                                                                                                                                                    |
+-------------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
