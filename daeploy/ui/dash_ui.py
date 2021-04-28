import dash
import dash_html_components as html 
from starlette.middleware.wsgi import WSGIMiddleware

import daeploy
from daeploy.utilities import get_service_root_path, get_service_name, get_service_version
import daeploy.ui.components as components


def render_ui(app: dash.Dash):
    layout = [
        html.H1(children=f"{get_service_name()} {get_service_version()}")
    ]


    # Add layout to app
    app.layout = html.Div(
        children=layout
    )


def start_ui(service):
    app = dash.Dash(
        __name__,
        requests_pathname_prefix=get_service_root_path() + "/",
        title="Daeploy"
    )

    render_ui(app)

    service.app.mount("/", WSGIMiddleware(app.server))
