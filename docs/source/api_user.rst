.. _start:

Users
===============

User
~~~~~~~~~~~~~~~~~~~~~~~~

| **Attributes**

+------------------+-----------------------------------------------------------------------+
| username         | The username of the user.                                             |
+------------------+-----------------------------------------------------------------------+
| first_name       | The first name of the user. May or may not exist.                     |
+------------------+-----------------------------------------------------------------------+
| last_name        | The last name of the user. May or may not exist.                      |
+------------------+-----------------------------------------------------------------------+
| email            | The email of the user. May or may not exist.                          |
+------------------+-----------------------------------------------------------------------+
| password         | The password of the user.                                             |
+------------------+-----------------------------------------------------------------------+
| groups           | The groups to which the user belongs, as a many-to-many relationship. |
+------------------+-----------------------------------------------------------------------+
| user_permissions | The permissions which the user has, as a many-to-many relationship.   |
+------------------+-----------------------------------------------------------------------+

| **Functions**

+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_username()                  | Returns the user's username.                                                                                                                                              |
+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_full_name()                 | Returns the user's first_name plus last_name, with a space in between.                                                                                                    |
+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_user_permissions(obj=None)  | Returns the set of permission strings which the user has directly, as a QuerySet. If obj is passed in, only returns the permissions for this specific object.             |
+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_group_permissions(obj=None) | Returns the set of permission strings which the user has through their groups, as a QuerySet. If obj is passed in, only returns the permissions for this specific object. |
+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| get_all_permissions(obj=None)   | Returns the set of all permission strings which the user has, as a QuerySet. If obj is passed in, only returns the permissions for this specific object.                  |
+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| has_perm(perm, obj=None)        | Returns True if the user has the specified permission. If obj is passed in, only returns the permissions for this specific object.                                        |
+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

CommunityUser
~~~~~~~~~~~~~~~~~~~~~~~~

| Extends ``User``.

| **Attributes**

+--------------------+----------------------------------------------------------------+
| readable_name      | The readable name of the user. May or may not exist.           |
+--------------------+----------------------------------------------------------------+
| avatar             | The URL of the avatar image of the user. May or may not exist. |
+--------------------+----------------------------------------------------------------+
| community          | The community which the user belongs to.                       |
+--------------------+----------------------------------------------------------------+
| access_token       | The access token which the user has. May or may not exist.     |
+--------------------+----------------------------------------------------------------+
| is_community_admin | True if the user is an admin.                                  |
+--------------------+----------------------------------------------------------------+

| **Functions**

+--------------------------+-------------------------------------------------------------------+
| has_role(role_name)      | Returns True if the user has a role with the specified role_name. |
+--------------------------+-------------------------------------------------------------------+
| get_roles()              | Returns a list containing all of the user's roles.                |
+--------------------------+-------------------------------------------------------------------+
| save(\*args, \*\*kwargs) | Saves the user. Note: Only meant for internal use.                |
+--------------------------+-------------------------------------------------------------------+
