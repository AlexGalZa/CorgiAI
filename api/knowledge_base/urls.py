from django.urls import path
from knowledge_base import views

urlpatterns = [
    path("", views.knowledge_base_index, name="knowledge_base_index"),
    path("<slug:slug>/", views.knowledge_base_article, name="knowledge_base_article"),
]
