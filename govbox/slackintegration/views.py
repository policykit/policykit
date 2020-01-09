from django.shortcuts import render
from urllib import parse
import urllib.request
from govbox.settings import CLIENT_SECRET

# Create your views here.

def oauth(request):
    
#     code = request.GET.code
    code = 'test'

    data = parse.urlencode({
        'client_id': '455205644210.869594358164',
        'client_secret': CLIENT_SECRET,
        'code': code,                    
        }).encode()
        
    print(data)
    
    req = urllib.request.Request('https://slack.com/api/oauth.access', data=data)
    resp = urllib.request.urlopen(req)
    print(resp)