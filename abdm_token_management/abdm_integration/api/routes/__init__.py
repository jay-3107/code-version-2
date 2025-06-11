# api/routes/__init__.py
# Import routers directly
from api.routes.token_routes import router as token_routes
from api.routes.health_routes import router as health_routes
from api.routes.encryption_routes import router as encryption_routes

# No need for any other code here