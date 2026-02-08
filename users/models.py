from django.db import models
from django.contrib.auth.models import User

# We use Django's built-in User model for authentication
# For RBAC, we'll use Django's Group and Permission models
# and extend with Neo4j nodes for graph relationships

# No custom models needed - using Django's built-in auth system
