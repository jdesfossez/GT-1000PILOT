import dash
from dash import html, dcc, ctx, Input, Output, callback, get_app
from datetime import datetime
from time import sleep

from shared import gt1000, off_color, on_color, logger
from pages.pages_common import send_fx_state_command, register_callbacks, refresh_all_effects, generate_buttons, serve_layout, callbacks_registered

dash.register_page(__name__, path="/dist")

state_key = "dist"
icon = "/assets/stompbox-dist.png"
callbacks_registered[state_key] = False


@callback(
    Output(f"{state_key}_buttons", "children"),
    Input("interval-component", "n_intervals"),
)
def update_metrics(n):
    refresh_all_effects(state_key)
    return generate_buttons(state_key, icon)

layout = serve_layout(state_key, icon)
