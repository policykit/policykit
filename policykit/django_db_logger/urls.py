from django.urls import path
from django.contrib.auth.decorators import login_required
from django_db_logger.views import LogListView

urlpatterns = [path("", login_required(login_url="/login")(LogListView.as_view()))]
