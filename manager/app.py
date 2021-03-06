import atexit
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from starlette.middleware.wsgi import WSGIMiddleware

from manager.routers import (
    admin_api,
    service_api,
    dashboard_api,
    notification_api,
    auth_api,
    logging_api,
)
from manager import proxy
from manager.database.database import initialize_db
from manager.database import service_db
from manager.constants import get_manager_version, cors_enabled, cors_config


# Setup logger
logging_api.setup_logging()
LOGGER = logging.getLogger(__name__)

LOGGER.info("Creating manager FastApi application...")
app = FastAPI(
    title="Daeploy",
    description="Daeploy Manager API by Viking Analytics",
    version=get_manager_version(),
)

# CORS middleware
if cors_enabled():
    app.add_middleware(CORSMiddleware, **cors_config())

# Services subapi
app.include_router(service_api.ROUTER, prefix="/services", tags=["Service"])

# Notifications subapi
app.include_router(
    notification_api.ROUTER, prefix="/notifications", tags=["Notification"]
)

# Dashboard subapi
app.mount("/dashboard", WSGIMiddleware(dashboard_api.app.server))

# Logs subapi
app.include_router(logging_api.ROUTER, prefix="/logs", tags=["Logging"])

# Authentication subapi
app.include_router(
    auth_api.ROUTER, prefix="/auth", tags=["Auth"], include_in_schema=False
)

# Admin subapi
app.include_router(
    admin_api.ROUTER, prefix="/admin", tags=["Admin"], include_in_schema=False
)


# Root
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")


# Get the version of the manger
@app.get("/~version")
def return_manager_version() -> str:
    return get_manager_version()


@app.on_event("startup")
def startup_event():
    """Perform initial setup of dependencies"""
    killer = proxy.initial_setup()
    atexit.register(killer)
    initialize_db()
    recreate_proxy_configurations()


def recreate_proxy_configurations():
    """Use database to recreate proxy configuration files for running services"""
    services = service_db.get_all_services_db()
    service_names = []
    for service in services:
        proxy.create_new_service_configuration(
            service["name"], service["version"], service["url"]
        )
        if service["name"] not in service_names:
            service_names.append(service["name"])

    for name in service_names:
        main_version, shadow_version = service_db.get_main_and_shadow_versions(name)
        proxy.create_mirror_configuration(name, main_version, shadow_version)


if __name__ == "__main__":
    # For debugging only
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
