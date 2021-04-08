import dash
import dash_html_components as html
import daeploy

app = dash.Dash(
    __name__,
    requests_pathname_prefix=daeploy.utilities.get_service_root_path(),
)

app.layout = html.Div(
    children=[
        html.H1(children="Hello World"),
    ]
)

if __name__ == "__main__":
    app.run_server("0.0.0.0")
