.. _start:

Tutorial 1: Hello World
--------------------------

In this tutorial, we will write a policy in PolicyKit that performs the most traditional first action of any programmer: printing Hello World.

::

 Note: In this tutorial, and the following tutorials, we will make use of the DiscordIntegration.
 If you are new to PolicyKit, we recommend following along in the DiscordIntegration so as not to
 become lost. However, it shouldn't pose too much of a challenge to emulate the steps in this
 tutorial in another integration, if you are up to the task.

To begin, we must log into the PolicyKit dashboard. You can use either our test server at `https://policykit.org/main/ <https://policykit.org/main/>`_ or your own custom PolicyKit server. To set up PolicyKit with your local Discord guild, please see our tutorial on setting up PolicyKit with Discord. Once you have finished setting up PolicyKit with Discord, you should install PolicyKit to your Discord server. For practice purposes, you should use the Testing starter kit, as it will allow you to instantly pass any policy you propose. When you have installed PolicyKit to your Discord server, you can sign in with Discord to view the PolicyKit dashboard.

|

From there, you should click the Propose Action button on the top right of the dashboard. On the following Actions screen, you should click the Platform Policies menu to drop down the list of platform policy actions. Select the Add Platform Policy option to view the Policy Editor.

|

On the Policy Editor page, fill in the following information for your policy:

**Name**
 ``Hello World`` (or whatever you would like to name your policy)
**Description**
 ``A simple program that sends a Hello World message.`` (can leave this blank if you wish)
**Filter**
 ``return True``
**Initialize**
 ``pass``
**Notify**
 ``pass``
**Check**
 ``return PASSED``
**Pass**
 ``ac
