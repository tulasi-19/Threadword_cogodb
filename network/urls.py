from django.urls import path
from . import views

app_name = "network"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("person/<str:person_id>/", views.profile, name="profile"),
    path("path/", views.path_finder, name="path_finder"),
]
