import dash
from dash import html, dcc, ctx, Input, Output, callback, get_app
from datetime import datetime
from time import sleep

from shared import gt1000, off_color, on_color, logger

dash.register_page(__name__, path="/eq")

# This holds the current layout, we only want to refresh this if there
# was an actual change in state to avoid constant refreshes
current_buttons = None
last_action_ts = None

state_key = "eq"
icon = "/assets/stompbox-eq.png"
callbacks_registered = False


def register_callbacks(app):
    for n in range(1, len(gt1000.dash_effects[state_key]) + 1):
        app.callback(
            Output(f"{state_key}_toggle_fx{n}", "style"),
            Input(f"{state_key}_toggle_fx{n}", "n_clicks"),
            prevent_initial_call=True,
        )(lambda n_clicks, fx_num=n: send_fx_state_command(fx_num, n_clicks))


def refresh_all_effects():
    global callbacks_registered
    gt1000_ready = True
    if state_key not in gt1000.get_state():
        current_state = {state_key: []}
        gt1000_ready = False
    current_state = gt1000.get_state()
    # If we clicked on a button but the current_state from the pedal wasn't
    # sync'ed yet, we want to keep our old state otherwise the pedal color will
    # go back to its previous state.
    if (
        last_action_ts is None
        or current_state["last_sync_ts"][state_key] > last_action_ts
    ):
        gt1000.dash_effects[state_key] = current_state[state_key]
    for i in range(len(gt1000.dash_effects[state_key])):
        if gt1000.dash_effects[state_key][i]["state"] == "OFF":
            gt1000.dash_effects[state_key][i]["color"] = off_color
        else:
            gt1000.dash_effects[state_key][i]["color"] = on_color
        # EQs don't have names
        gt1000.dash_effects[state_key][i]["name"] = f"{state_key}{i+1}"

    if gt1000_ready and not callbacks_registered:
        register_callbacks(get_app())
        callbacks_registered = True


def generate_buttons():
    global current_buttons
    current_buttons = html.Div(
        children=[
            html.Button(
                id=f"{state_key}_toggle_fx{n}",
                children=[
                    dcc.Loading(
                        html.Div(
                            children=[
                                html.Img(
                                    src=icon,
                                    width="80%",
                                    height="80%",
                                ),
                                html.H2(
                                    id=f"fx{n}_name",
                                    children=gt1000.dash_effects[state_key][n - 1][
                                        "name"
                                    ],
                                ),
                            ],
                            style={"color": "black"},
                        )
                    )
                ],
                n_clicks=0,
                style={
                    "backgroundColor": gt1000.dash_effects[state_key][n - 1]["color"]
                },
            )
            for n in range(1, len(gt1000.dash_effects[state_key]) + 1)
        ],
        style={
            "display": "grid",
            "grid-template-columns": f"repeat({len(gt1000.dash_effects[state_key])}, 1fr)",
            "width": "100vw",
            "height": "80vh",
            "gap": "0",
        },
    )
    return current_buttons


def serve_layout():
    refresh_all_effects()
    return html.Div(
        id="button-grid",
        children=[
            dcc.Interval(
                id="interval-component",
                interval=2 * 1000,  # in milliseconds
                n_intervals=0,
            ),
            html.Div(id=f"{state_key}_buttons", children=generate_buttons()),
        ],
    )


@callback(
    Output(f"{state_key}_buttons", "children"),
    Input("interval-component", "n_intervals"),
)
def update_metrics(n):
    refresh_all_effects()
    return generate_buttons()


def send_fx_state_command(fx_num, n_clicks):
    if not n_clicks:
        return
    global last_action_ts
    last_action_ts = datetime.now()
    if gt1000.dash_effects[state_key][fx_num - 1]["state"] == "ON":
        gt1000.toggle_fx_state(state_key, fx_num, "OFF")
        # optimistically update here
        gt1000.dash_effects[state_key][fx_num - 1]["state"] = "OFF"
        return {"backgroundColor": off_color}
    else:
        gt1000.toggle_fx_state(state_key, fx_num, "ON")
        # optimistically update here
        gt1000.dash_effects[state_key][fx_num - 1]["state"] = "ON"
        return {"backgroundColor": on_color}


layout = serve_layout
# register_callbacks(get_app())
