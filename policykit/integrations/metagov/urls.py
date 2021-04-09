from django.urls import path

from integrations.metagov import views


urlpatterns = [
    path("outcome/<int:id>", views.post_outcome),
    path("save_config", views.save_config),
    path("action", views.action),
]
