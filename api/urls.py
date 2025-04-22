from django.urls import path
from api import views

urlpatterns = [
    path("list_databases", views.list_databases),
    path("list_tables", views.list_tables),
    path("run_sql", views.run_sql),
]
