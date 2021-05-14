from django.urls import path

from integrations.metagov import views


urlpatterns = [
    path("internal/outcome/<int:id>", views.post_outcome),
    path("internal/action", views.action),
    path("save_config", views.save_config),
]
