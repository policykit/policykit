.. _start:

Roles
===============

Group
~~~~~~~~~~~~~~~~~~~~~~~~

| **Attributes**

+-------------+---------------------------------------------------------------------+
| name        | The name of the role. Note: Only meant for internal use.            |
+-------------+---------------------------------------------------------------------+
| permissions | The permissions which the role has, as a Many-to-many relationship. |
+-------------+---------------------------------------------------------------------+

CommunityRole
~~~~~~~~~~~~~~~~~~~~~~~~

| Extends ``Group``.

| **Attributes**

+-------------+-----------------------------------------------------+
| community   | The community which the role belongs to.            |
+-------------+-----------------------------------------------------+
| role_name   | The readable name of the role.                      |
+-------------+-----------------------------------------------------+
| description | The readable description of the role. May be empty. |
+-------------+-----------------------------------------------------+
