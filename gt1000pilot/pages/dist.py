import dash
from dash import Input, Output, callback

from gt1000pilot.pages.pages_common import (
    refresh_all_effects,
    generate_buttons,
    serve_layout,
    callbacks_registered,
)

dash.register_page(__name__, path="/dist")

state_key = "dist"

callbacks_registered[state_key] = False


@callback(
    Output(f"{state_key}_buttons", "children"),
    Input("interval-component", "n_intervals"),
)
def update_metrics(n):
    refresh_all_effects(state_key)
    return generate_buttons(state_key)


layout = serve_layout(state_key)
