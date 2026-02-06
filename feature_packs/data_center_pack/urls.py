# feature_packs/data_center_pack/urls.py
from django.urls import path
from .views import rack_elevation_data

urlpatterns = [
    path('<str:label>/<str:element_id>/rack-elevation/', rack_elevation_data, name='rack_elevation_data'),
]