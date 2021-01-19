from django.shortcuts import render, redirect
from django.http import HttpResponse
from policykit.settings import SERVER_URL, DISCOURSE_CLIENT_SECRET
from integrations.discourse.models import DiscourseCommunity, DiscourseUser, DiscoursePostMessage, DiscourseStarterKit
from policyengine.models import *
from django.contrib.auth import login, authenticate
from django.views.decorators.csrf import csrf_exempt
from urllib import parse
import urllib.request
import json
import base64
import logging

logger = logging.getLogger(__name__)

# Create your views here.

@csrf_exempt
def init_community_discourse(request):
    url = request.POST['url']

    s = DiscourseCommunity.objects.filter(team_id=url)

    community = None

    req = urllib.request.Request(url + '/about.json')
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))

    title = res['about']['title']

    if not s.exists():
        user_group,_ = CommunityRole.objects.get_or_create(role_name="Base User", name="Discourse: " + title + ": Base User")

        community = DiscourseCommunity.objects.create(
            community_name=title,
            team_id=url,
            base_role=user_group
        )
        user_group.community = community
        user_group.save()
    else:
        community = s[0]
        community.community_name = title
        community.team_id = url
        community.save()

        response = redirect('/login?success=true')
        return response

    context = {
        "starterkits": [kit.name for kit in DiscourseStarterKit.objects.all()],
        "community_name": community.community_name,
        "platform": "discourse"
    }
    return render(request, "policyadmin/init_starterkit.html", context)

@csrf_exempt
def action(request):
    json_data = json.loads(request.body)
    logger.info('RECEIVED ACTION')
    logger.info(json_data)

def post_policy(policy, action, users=None, template=None, channel=None):
    from policyengine.models import LogAPICall

    policy_message_default = "This action is governed by the following policy: " + policy.description

    if not template:
        policy_message = policy_message_default
    else:
        policy_message = template

    data = {
        'content': policy_message
    }

    call = 'posts.json'

    res = policy.community.make_call(call, values=data)
    data['id'] = res['id']
    _ = LogAPICall.objects.create(community=community,
                                  call_type=call,
                                  extra_info=json.dumps(data))

    action.community_post = res['id']
    action.save()
