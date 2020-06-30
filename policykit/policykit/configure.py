from django.shortcuts import render
import logging


logger = logging.getLogger(__name__)

def configure(request):
    logger.info(request)

    subreddits = request.GET.get('subreddits').split(',')

    response = render(request, 'policyadmin/configure.html', { 'subreddits': subreddits })
    return response
