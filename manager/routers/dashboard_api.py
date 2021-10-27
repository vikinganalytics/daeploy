import logging
from datetime import datetime

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import manager.license
from manager.routers.service_api import read_services, inspect_service
from manager.routers.notification_api import get_notifications, delete_notifications
from manager.constants import get_external_proxy_url, get_manager_version

LOGGER = logging.getLogger(__name__)
DEFAULT_NUMBER_OF_LOGS = 100

app = dash.Dash(
    __name__,
    requests_pathname_prefix="/dashboard/",
    update_title=None,
    assets_folder="../assets",
)
app.title = "Daeploy"


def build_user_section():
    return html.Div(
        id="user-actions",
        className="user-actions",
        children=[
            html.P(f"v:{get_manager_version()}", className="version-identifier"),
            html.P(
                f"Expiry date: {manager.license.EXPIRATION_TIME.date()}",
                id="expiry-date",
                className="version-identifier",
            ),
            html.P(),
            html.A(
                "LOGS",
                id="manager-logs-buttom",
                href=f"{get_external_proxy_url()}/logs",
                className="logout",
            ),
            html.A(
                "API DOCS",
                id="documenation-button",
                href=f"{get_external_proxy_url()}/docs",
                className="logout",
            ),
            html.P(),
            html.Button(
                "CLEAR NOTIFICATIONS",
                id="clear-notifications-button",
                n_clicks=0,
                className="logout",
            ),
            html.A(
                "LOGOUT",
                id="logout-button",
                href=f"{get_external_proxy_url()}/auth/logout",
                className="logout",
            ),
        ],
    )


def build_banner():
    return html.Div(
        id="banner",
        className="banner",
        children=[
            html.Div(
                id="banner-text",
                children=[
                    html.Img(src=app.get_asset_url("daeploy_white_icon.png")),
                    dcc.Markdown(
                        """
                    ### Daeploy Dashboard
                    by Viking Analytics AB
                    """
                    ),
                ],
            ),
        ],
    )


def build_tabs():
    return html.Div(
        id="daeploy_tabs",
        children=[
            dcc.Tabs(
                id="app-tabs",
                className="daeploy_custom-tabs",
                # Set tab-1 to active from start.
                value="tab1",
                children=[
                    dcc.Tab(
                        id="services",
                        label="Services",
                        value="tab1",
                        className="daeploy_custom-tabs",
                        selected_className="daeploy_custom-tab--selected",
                    ),
                    dcc.Tab(
                        id="notification",
                        label="Notifications",
                        value="tab2",
                        className="daeploy_custom-tabs",
                        selected_className="daeploy_custom-tab--selected",
                    ),
                ],
            )
        ],
    )


@app.callback(
    Output("expiry-date", "children"),
    Input("interval1", "n_intervals"),
)
# pylint: disable=unused-argument
def update_expiry_date(interval):
    return f"Expiry date: {manager.license.EXPIRATION_TIME.date()}"


@app.callback(
    Output("app-content", "children"),
    Input("app-tabs", "value"),
    Input("interval1", "n_intervals"),
    Input("clear-notifications-button", "n_clicks"),
)
# pylint: disable=unused-argument
def update_content(tab_switch, interval, n_clicks):

    # Clearing notifications
    changed_id = [p["prop_id"] for p in dash.callback_context.triggered][0]
    if "clear-notifications-button" in changed_id:
        LOGGER.debug("Clearing notifications!")
        delete_notifications()

    LOGGER.debug(f"tab_switch: {tab_switch} - interval: {interval}")
    if tab_switch == "tab2":
        return (
            html.Div(
                children=[
                    html.Div(children=[generate_table_notifications()]),
                ],
            ),
        )
    return (
        html.Div(
            children=[
                html.Div(children=[generate_table_services()]),
            ],
        ),
    )


def generate_table_services():
    """Generates a HTML table with the service information

    Returns:
        html.Table: The html table with service information
    """
    services = read_services()
    headers = ["Main", "Service name", "Version", "State", "Logs", "Documentation"]

    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in headers])]
        +
        # Body
        [
            html.Tr(
                # Main/Shadow
                [
                    html.Td("*", className="green-text")
                    if service["main"]
                    else html.Td("")
                ]
                +
                # Name
                [html.Td(get_service_link(service))]
                # Version
                + [html.Td(service["version"])]
                # Service state
                + [html.Td(get_service_state(service))]
                # Log link
                + [html.Td(get_service_log_link(service))]
                # Docs link
                + [html.Td(get_service_docs_link(service))]
            )
            for service in services
        ]
    )


def get_service_state(service):
    """Getter for the state of the service.
       The statue of the service is collected from the inspect information.

    Args:
        service (dict): The service to get the state from.

    Returns:
        str: The state of the 'service'
    """
    inspection = inspect_service(service["name"], service["version"])

    running = inspection["State"]["Running"]
    if running:
        timestamp = inspection["State"]["StartedAt"]
        running_msg = "Running"
    else:
        timestamp = inspection["State"]["FinishedAt"]
        running_msg = "Stopped"

    timestamp = datetime.strptime(timestamp.split(".")[0], "%Y-%m-%dT%H:%M:%S")
    timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return f" {running_msg} (since {timestamp})"


def get_link_style():
    return {"color": "white"}


def get_service_docs_link(service):
    """Create the link to the docs from a service

    Args:
        service (dict): The service to get the link for.

    Returns:
        html.A: Html.A object with a href to the docs for 'service'
    """
    proxy_url = get_external_proxy_url()
    return html.A(
        "Docs",
        href=(f"{proxy_url}/services/{service['name']}_{service['version']}/docs"),
        style=get_link_style(),
    )


def get_service_log_link(service):
    """Get the link to the logs from a service

    Args:
        service (dict): The service to get the link for.

    Returns:
        html.A: Html.A object with a href to the logs for 'service'
    """
    logs_end_point = f"{get_external_proxy_url()}/services/~logs"
    return html.A(
        "Logs",
        href=f"{logs_end_point}?name={service['name']}&version={service['version']}"
        f"&follow=true&tail={DEFAULT_NUMBER_OF_LOGS}",
        style=get_link_style(),
    )


def get_service_link(service):
    service_endpoint = (
        f"{get_external_proxy_url()}/services/{service['name']}_{service['version']}/"
    )
    return html.A(service["name"], href=service_endpoint, style=get_link_style())


def generate_table_notifications():
    """Generates a HTML table with the notifications

    Returns:
        html.Table: The html table with notification information
    """
    notifications = get_notifications()
    headers = [
        "Latest Timestamp",
        "Service name",
        "Version",
        "Message",
        "Count",
        "Severity",
    ]
    dict_keys = ["timestamp", "service_name", "service_version", "msg", "counter"]
    severity_colors = get_severity_colors(notifications)
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in headers])]
        +
        # Body
        [
            html.Tr(
                [html.Td(notifications[index[0]][key]) for key in dict_keys]
                + [severity_colors[index[0]]]
            )
            for index in reversed(
                sorted(notifications.items(), key=lambda item: item[1]["timestamp"])
            )
        ]
    )


def get_severity_colors(notifications):
    """Get the correct color for a severity.

    Args:
        notifications (dict): The notifications.

    Returns:
        dict: Dict with the notification hash as the key and
        a html.Td object with correct color class for the severity
        as value.
    """
    tds = {}
    for index, notification in notifications.items():
        color_class = "severity-info"
        text = "Info"
        if notification["severity"] == 1:
            color_class = "severity-warning"
            text = "Warning"
        elif notification["severity"] == 2:
            color_class = "severity-critical"
            text = "Critical"
        tds[index] = html.Td(text, className=color_class)
    return tds


app.layout = html.Div(
    id="big-app-container",
    children=[
        # reload intevarl
        dcc.Interval(id="interval1", interval=5 * 1000, n_intervals=0),
        build_user_section(),
        build_banner(),
        html.Div(
            id="app-container",
            children=[
                build_tabs(),
                # Main app
                html.Div(id="app-content"),
            ],
        ),
    ],
)
