import logging
from datetime import datetime

import dash
from dash import dcc, html, Input, Output

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
    return html.Nav(
        className="actions",
        children=[
            html.A(
                "Logs",
                href=f"{get_external_proxy_url()}/logs",
                className="act",
            ),
            html.A(
                "API Docs",
                href=f"{get_external_proxy_url()}/docs",
                className="act",
            ),
            html.Button(
                "Clear notifications",
                id="clear-notifications-button",
                n_clicks=0,
                className="act",
            ),
            html.A(
                "Log out",
                href=f"{get_external_proxy_url()}/auth/logout",
                className="act danger",
            ),
        ],
    )


def build_banner():
    return html.Header(
        className="top",
        children=[
            html.Div(
                className="left",
                children=[
                    html.Div(
                        className="mark",
                        children=[
                            html.Img(
                                src=app.get_asset_url("daeploy_mark.svg"),
                                width=26,
                                height=26,
                            ),
                            html.Span(
                                children=[
                                    "dae",
                                    html.B("ploy"),
                                ],
                                className="wordmark",
                            ),
                        ],
                    ),
                    html.Span(
                        children=[
                            "manager ",
                            html.B(f"v: {get_manager_version()}"),
                        ],
                        className="vchip",
                    ),
                ],
            ),
            build_user_section(),
        ],
    )


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


@app.callback(
    Output("notifications-content", "children"),
    Input("interval1", "n_intervals"),
    Input("clear-notifications-button", "n_clicks"),
)
# pylint: disable=unused-argument
def update_notifications(interval, n_clicks):
    return generate_table_notifications()


def generate_table_services():
    """Generates service rows with the service information.

    Returns:
        html.Div: A Div containing styled service rows.
    """
    services = read_services()
    if not services:
        return html.Div("No services deployed.", className="empty")

    rows = []
    for service in services:
        is_main = service["main"]
        inspection = inspect_service(service["name"], service["version"])
        running = inspection["State"]["Running"]

        # Determine dot class and state label
        if running and is_main:
            dot_class = "sdot run live"
            state_label = "Running"
        elif running:
            dot_class = "sdot shadow"
            state_label = "Mirroring traffic"
        else:
            dot_class = "sdot stop"
            state_label = "Stopped"

        # Timestamp
        if running:
            timestamp_raw = inspection["State"]["StartedAt"]
        else:
            timestamp_raw = inspection["State"]["FinishedAt"]
        timestamp = datetime.strptime(timestamp_raw.split(".")[0], "%Y-%m-%dT%H:%M:%S")
        since_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Pin icon
        if is_main:
            pin = html.Span("★", className="pin main", title="Main version")
        elif not running:
            pin = html.Span("○", className="pin", title="Stopped")
        else:
            pin = html.Span("↗", className="pin", title="Shadow version")

        # Name with optional shadow badge
        name_children = [html.Div(service["name"], className="name")]
        if not is_main and running:
            name_children[0] = html.Div(
                [service["name"], html.Span("shadow", className="badge shadow")],
                className="name",
            )
        name_children.append(html.Div(service["version"], className="ver"))

        id_div = html.Div(
            [pin, html.Div(name_children)],
            className="id",
        )

        state_lbl_class = "lbl stopped" if not running else "lbl"
        state_div = html.Div(
            [
                html.Span(className=dot_class),
                html.Div(
                    [
                        html.Div(state_label, className=state_lbl_class),
                        html.Div(f"since {since_str}", className="since"),
                    ]
                ),
            ],
            className="state",
        )

        actions_div = html.Div(
            [
                get_service_log_link(service),
                get_service_docs_link(service),
            ],
            className="svc-actions",
        )

        rows.append(html.Div([id_div, state_div, actions_div], className="svc"))

    return html.Div(rows)


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
        className="lnk",
    )


def get_service_log_link(service):
    """Get the link to the logs from a service

    Args:
        service (dict): The service to get the link for.

    Returns:
        html.A: Html.A object with a href to the logs for 'service'
    """
    proxy_url = get_external_proxy_url()
    return html.A(
        "Logs",
        href=f"{proxy_url}/services/~logs/view"
        f"?name={service['name']}&version={service['version']}",
        className="lnk",
    )


def get_service_link(service):
    service_endpoint = (
        f"{get_external_proxy_url()}/services/{service['name']}_{service['version']}/"
    )
    return html.A(service["name"], href=service_endpoint, style=get_link_style())


def generate_table_notifications():
    """Generates notification rows.

    Returns:
        html.Div: A Div containing styled notification rows.
    """
    notifications = get_notifications()
    if not notifications:
        return html.Div("No notifications.", className="empty")

    severity_map = get_severity_colors(notifications)
    rows = []
    for index, _ in reversed(
        sorted(notifications.items(), key=lambda item: item[1]["timestamp"])
    ):
        notification = notifications[index]
        sev_class, sev_label = severity_map[index]
        timestamp = notification["timestamp"]
        msg = notification["msg"]

        row = html.Div(
            [
                html.Span(className=f"sev {sev_class}"),
                html.Div(
                    [
                        html.Div(msg, className="msg"),
                        html.Div(
                            [
                                html.Span(sev_label, className=f"sev-tag {sev_class}"),
                                html.Span(timestamp),
                            ],
                            className="meta",
                        ),
                    ]
                ),
            ],
            className="note",
        )
        rows.append(row)

    return html.Div(rows)


def get_severity_colors(notifications):
    """Get the CSS class and label for each notification's severity.

    Args:
        notifications (dict): The notifications.

    Returns:
        dict: Dict with the notification hash as the key and
        a (css_class, label) tuple as the value.
        Severity mapping: 0=Info, 1=Warning, 2=Critical.
    """
    result = {}
    for index, notification in notifications.items():
        sev = notification["severity"]
        if sev == 1:
            result[index] = ("warn", "Warning")
        elif sev == 2:
            result[index] = ("crit", "Critical")
        else:
            result[index] = ("info", "Info")
    return result


app.layout = html.Div(
    children=[
        dcc.Interval(id="interval1", interval=5 * 1000, n_intervals=0),
        # Hidden tabs component kept so update_content callback still resolves
        dcc.Tabs(id="app-tabs", value="tab1", style={"display": "none"}),
        build_banner(),
        html.Div(
            className="page",
            children=[
                html.Div(
                    className="grid",
                    children=[
                        # Services panel (hero)
                        html.Section(
                            className="panel",
                            children=[
                                html.Div(
                                    className="panel-head",
                                    children=[html.H2("Services")],
                                ),
                                html.Div(id="app-content"),
                            ],
                        ),
                        # Notifications panel
                        html.Section(
                            className="panel",
                            children=[
                                html.Div(
                                    className="panel-head",
                                    children=[html.H2("Notifications")],
                                ),
                                html.Div(
                                    id="notifications-content",
                                    children=[generate_table_notifications()],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)
