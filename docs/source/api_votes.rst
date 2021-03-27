.. _start:

Votes
====================================

UserVote
~~~~~~~~~~~~~~~~~

| **Attributes**

+-----------+---------------------------------------+
| user      | The user who cast the vote.           |
+-----------+---------------------------------------+
| proposal  | The proposal which is being voted on. |
+-----------+---------------------------------------+
| vote_time | The time at which the vote was cast.  |
+-----------+---------------------------------------+

| **Functions**

+--------------------+----------------------------------------------------------------------------------+
| get_time_elapsed() | Returns a datetime object representing the time elapsed since the vote was cast. |
+--------------------+----------------------------------------------------------------------------------+

BooleanVote
~~~~~~~~~~~~~~~~~~~~

| Extends ``UserVote``.

| **Attributes**

+---------------+-------------------------------------------------------------+
| boolean_value | The value of the vote. Either True ('Yes') or False ('No'). |
+---------------+-------------------------------------------------------------+

NumberVote
~~~~~~~~~~~~~~~~~~~~

| Extends ``UserVote``.

| **Attributes**

+--------------+--------------------------------------------+
| number_value | The value of the vote. Must be an integer. |
+--------------+--------------------------------------------+
