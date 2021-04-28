import daeploy
import dash
import dash_html_components as html

# We need a WSGIMiddleware to be the middleman between the asynchronous SDK app
# (based on FastAPI) and the synchronous Dash app (based on Flask). `starlette`
# is a dependency of FastAPI so it doesnt need to be added to the
# `requirements.txt`
from starlette.middleware.wsgi import WSGIMiddleware

# Creating Dash app object that can be used as usual to build you Dash application.
# We make sure to give it the correct path where it will be mounted
app = dash.Dash(
    __name__,
    requests_pathname_prefix=daeploy.utilities.get_service_root_path() + "/dashboard/",
)

app.layout = html.Div(
    children=[
        html.H1(children="Hello World"),
    ]
)

# We mount the Dash app server under daeploy.service.app on the subpath `/dashboard`
daeploy.service.app.mount("/dashboard", WSGIMiddleware(app.server))

# And finally we start the service as we would with any other SDK-based service.
if __name__ == "__main__":
    daeploy.service.run()
