import dash
from dash import html, dcc, ctx, Input, Output, callback, get_app
import dash_bootstrap_components as dbc
from datetime import datetime
from time import sleep

from shared import gt1000, off_color, on_color, logger, buttons_pc_height

last_action_ts = None

callbacks_registered = {}


def get_icon(fx_type):
    prefix = "/assets/"
    icons = {
        "dist": "stompbox-dist.png",
        "eq": "stompbox-eq.png",
        "fx": "stompbox-fx.png",
        "comp": "stompbox-comp.png",
    }
    if fx_type in icons:
        return f"{prefix}{icons[fx_type]}"
    return f"{prefix}stompbox-fx.png"


def register_callbacks(app, fx_type):
    for n in range(1, len(gt1000.dash_effects[fx_type]) + 1):
        app.callback(
            Output(f"{fx_type}_toggle_fx{n}", "style"),
            Input(f"{fx_type}_toggle_fx{n}", "n_clicks"),
            prevent_initial_call=True,
        )(lambda n_clicks, fx_num=n: send_fx_state_command(fx_type, fx_num, n_clicks))


def refresh_all_effects(fx_type):
    global callbacks_registered
    gt1000_ready = True
    if fx_type not in gt1000.get_state():
        current_state = {fx_type: []}
        gt1000_ready = False
    current_state = gt1000.get_state()
    # If we clicked on a button but the current_state from the pedal wasn't
    # sync'ed yet, we want to keep our old state otherwise the pedal color will
    # go back to its previous state.
    if (
        last_action_ts is None
        or current_state["last_sync_ts"][fx_type] > last_action_ts
    ):
        gt1000.dash_effects[fx_type] = current_state[fx_type]
    for i in range(len(gt1000.dash_effects[fx_type])):
        if gt1000.dash_effects[fx_type][i]["state"] == "OFF":
            gt1000.dash_effects[fx_type][i]["color"] = off_color
        else:
            gt1000.dash_effects[fx_type][i]["color"] = on_color

    if gt1000_ready and not callbacks_registered[fx_type]:
        register_callbacks(get_app(), fx_type)
        callbacks_registered[fx_type] = True


def build_grid(fx_type):
    grid = []
    num_effects = len(gt1000.dash_effects[fx_type])
    col_width = int(12 / num_effects)  # Column width based on number of effects

    for n in range(1, num_effects + 1):
        grid.append(dbc.Col(
            width=col_width,
            children=[
                html.Button(
                    id=f"{fx_type}_toggle_fx{n}",
                    children=[
                        html.Div(
                            children=[
                                html.Img(
                                    src=get_icon(fx_type),
                                    style={
                                        "max-width": "90%",   # Ensures the image width is capped at 100% of its container
                                        "max-height": "90%",  # Ensures the image height is capped at 100% of its container
                                        "width": "auto",       # Adjust the width to maintain aspect ratio
                                        "height": "auto",      # Adjust the height to maintain aspect ratio
                                        "object-fit": "contain",  # Ensures the entire image is visible, scaling as needed
                                    },
                                ),
                                html.H2(
                                    id=f"fx{n}_name",
                                    children=gt1000.dash_effects[fx_type][n - 1]["name"],
                                    style={"text-align": "center", "margin": "0"},  # Center text and remove margins
                                ),
                            ],
                            style={"color": "black", "text-align": "center", "height": "100%", "display": "flex", "flex-direction": "column", "justify-content": "center"},
                        )
                    ],
                    n_clicks=0,
                    style={
                        "backgroundColor": gt1000.dash_effects[fx_type][n - 1]["color"],
                        "display": "flex",
                        "flex-direction": "column",
                        "align-items": "center",
                        "justify-content": "center",
                        "width": "100%",  # Ensure button takes full width of column
                        "height": "100%",  # Ensure button takes full height of column
                        "box-sizing": "border-box",  # Include padding/border in size calculations
                        "overflow": "hidden",  # Prevent any content overflow
                        "textDecoration": "none",
                    },
                )
            ]
        ))

    return grid

def generate_buttons(fx_type):
    grid = build_grid(fx_type)
    return html.Div(
            children=dbc.Row(
                id="button_grid",
                children=grid,
                style={
                    "display": "flex",
                    "flex-wrap": "nowrap",  # Ensure items do not wrap to a new row
                    "justify-content": "space-evenly",  # Evenly space out the columns
                    "align-items": "stretch",  # Make sure all columns stretch to the same height
                    "overflow": "hidden",  # Prevent scrollbars
                    "width": "100%",
                    "height": "100%",  # Ensure the grid takes full height of its container
                    }

                ),
            style={
                "display": "flex",
                "flex-direction": "column",
                "height": f"{buttons_pc_height}vh",  # This should match the max-height defined earlier
                "overflow": "hidden",  # Prevent scrollbars on the outer container
                }
            )

def serve_layout(fx_type):
    refresh_all_effects(fx_type)
    return html.Div(
        id="button-grid",
        children=[
            dcc.Interval(
                id="interval-component",
                interval=2 * 1000,  # in milliseconds
                n_intervals=0,
            ),
            html.Div(id=f"{fx_type}_buttons", children=generate_buttons(fx_type)),
        ],
    )


def send_fx_state_command(fx_type, fx_num, n_clicks):
    if not n_clicks:
        return
    global last_action_ts
    last_action_ts = datetime.now()
    if gt1000.dash_effects[fx_type][fx_num - 1]["state"] == "ON":
        gt1000.toggle_fx_state(fx_type, fx_num, "OFF")
        # optimistically update here
        gt1000.dash_effects[fx_type][fx_num - 1]["state"] = "OFF"
        return {"backgroundColor": off_color}
    else:
        gt1000.toggle_fx_state(fx_type, fx_num, "ON")
        # optimistically update here
        gt1000.dash_effects[fx_type][fx_num - 1]["state"] = "ON"
        return {"backgroundColor": on_color}
