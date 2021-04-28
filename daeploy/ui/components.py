import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component


def text_input(entrypoint, argname, default_value=None):
    component_id = f"{entrypoint}-{argname.lower()}"

    default_value = default_value or Component.UNDEFINED

    input_div = html.Div(
        [
            f"{argname}: ",
            dcc.Input(id=component_id, value=default_value, type="text")
        ]
    )

    return input_div, component_id


def text_output(entrypoint):
    component_id = f"{entrypoint}-output"

    output_div = html.Div(
        [
            "Output: ",
            dcc.Textarea(id=component_id, value="", readOnly=True)
        ]
    )

    return output_div, component_id
