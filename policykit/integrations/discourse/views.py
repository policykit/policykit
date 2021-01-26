from django.shortcuts import render, redirect
from django.http import HttpResponse
from policykit.settings import SERVER_URL, DISCOURSE_PUBLIC_KEY
from integrations.discourse.models import DiscourseCommunity, DiscourseUser, DiscourseStarterKit
from policyengine.models import *
from django.contrib.auth import login, authenticate
from django.views.decorators.csrf import csrf_exempt
from urllib import parse
import urllib.request
import json
import base64
import secrets
import logging

logger = logging.getLogger(__name__)

# Create your views here.

@csrf_exempt
def configure(request):
    return render(request, "policyadmin/configure_discourse.html")

@csrf_exempt
def auth(request):
    url = request.POST['url']

    request.session['discourse_url'] = url

    client_id = secrets.token_hex(16) # 32 random nibbles (not bytes! despite what API doc says)
    nonce = secrets.token_hex(8) # 16 random nibbles (not bytes! despite what API doc says)
    scopes = 'read,write'

    from Crypto.PublicKey import RSA
    key_pair = RSA.generate(2048)
    public_key = key.publickey()

    req = urllib.request.Request('{}/user-api-key/new?auth_redirect={}%2Fdiscourse%2Finit_community&application_name=PolicyKit&client_id={}&scopes={}&public_key={}&nonce={}'.format(url, SERVER_URL, client_id, scopes, public_key, nonce))
    logger.info(req.__dict__)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    urllib.request.urlopen(req)

@csrf_exempt
def user_login(request):
    url = request.session['discourse_url']

    user = authenticate(request, platform='discourse')
    if user:
        login(request, user)
        response = redirect('/main')
        return response
    else:
        response = redirect('/login?error=invalid_login')
        return response

@csrf_exempt
def init_community(request):
    url = request.session['discourse_url']
    api_key = request.POST['payload']

    community = None
    s = DiscourseCommunity.objects.filter(team_id=url)
    if s.exists():
        community = s[0]

    req = urllib.request.Request(url + '/about.json')
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Api-Key", api_key)
    req.add_header("Api-Username", "PolicyKit")
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))

    title = res['about']['title']

    if community:
        community = s[0]
        community.community_name = title
        community.team_id = url
        community.api_key = api_key
        community.save()

        response = redirect('/login?success=true')
        return response
    else:
        user_group,_ = CommunityRole.objects.get_or_create(role_name="Base User", name="Discourse: " + title + ": Base User")

        community = DiscourseCommunity.objects.create(
            community_name=title,
            team_id=url,
            api_key=api_key,
            base_role=user_group
        )
        user_group.community = community
        user_group.save()

        # Get the list of users and create a DiscourseUser object for each user
        req = urllib.request.Request(url + 'admin/users/list.json')
        req.add_header("Content-Type", "application/json")
        req.add_header("Api-Key", api_key)
        req.add_header("Api-Username", "PolicyKit")
        resp = urllib.request.urlopen(req)
        users = json.loads(resp.read().decode('utf-8'))

        for u in users:
            du, _ = DiscourseUser.objects.get_or_create(
                username=u['username'],
                readable_name=u['username'],
                community=community
            )
            du.save()

        context = {
            "starterkits": [kit.name for kit in DiscourseStarterKit.objects.all()],
            "community_name": community.community_name,
            "platform": "discourse"
        }
        return render(request, "policyadmin/init_starterkit.html", context)

    response = redirect('/login?error=no_community_found')
    return response

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
