from django.urls import path

from integrations.metagov import views


urlpatterns = [
    path("internal/outcome/<int:id>", views.internal_receive_outcome),
    path("internal/action", views.internal_receive_action)
]
