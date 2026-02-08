# core/urls.py

from django.contrib import admin
from django.urls import path, include
from graphene_django.views import GraphQLView
from cmdb.schema import schema

urlpatterns = [
    path('admin/', admin.site.urls),
    path('graphql/', GraphQLView.as_view(graphiql=True, schema=schema)),
    path('api/', include('cmdb.api_urls')),
    path('cmdb/', include('cmdb.urls')),         
]