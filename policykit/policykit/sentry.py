from django.conf import settings
from django.utils.safestring import mark_safe
from django import template

import sentry_sdk

register = template.Library()

# https://docs.sentry.io/platforms/javascript/install/loader/#default-bundle
SENTRY_SCRIPT = '<script id="sentry-script" src="https://browser.sentry-cdn.com/8.30.0/bundle.tracing.min.js" integrity="sha384-whi3vRW+DIBqY2lQQ6oghGXbbA0sL5NJxUL6CMC+LRJ0b4A64Qn7/6YhpeR0+3Nq" crossorigin="anonymous"></script>'

@register.simple_tag
def sentry():
    DSN = settings.SENTRY_DSN
    if not DSN:
        return ''

    meta = trace_propagation_meta(sentry_sdk.Hub.current)
    html = f"""{SENTRY_SCRIPT}
  {meta}
  <script>Sentry.init({{dsn: {DSN!r}, integrations: [Sentry.browserTracingIntegration()]}});</script>
"""

    return mark_safe(html)

# Copied from newer version of Sentry SDK in https://github.com/getsentry/sentry-python/blob/ff60906fcb9af3db9cda245288f2e49f70ee432f/sentry_sdk/hub.py#L737-L748
# Can remove once we upgrade sentry by upgrading Python
def trace_propagation_meta(self, span=None):
    """
    Return meta tags which should be injected into the HTML template
    to allow propagation of trace data.
    """
    meta = ""

    for name, content in self.iter_trace_propagation_headers(span):
        meta += '<meta name="%s" content="%s">' % (name, content)

    return meta
