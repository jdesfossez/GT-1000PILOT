import dash
from dash import html, dcc, ctx, Input, Output, callback, get_app

from shared import gt1000, off_color, on_color

dash.register_page(__name__, path="/")

if gt1000.model == "GT-1000CORE":
    nr_fx = 3
else:
    nr_fx = 4

def refresh_all_effects():
    gt1000.dash_effects = gt1000.get_all_fx_names_state()
    for i in range(len(gt1000.dash_effects)):
        if gt1000.dash_effects[i]["state"] == "OFF":
            gt1000.dash_effects[i]["color"] = off_color
        else:
            gt1000.dash_effects[i]["color"] = on_color

def serve_layout():
    refresh_all_effects()
    return html.Div(
        id="button-grid",
        children=[
            dcc.Interval(
                id='interval-component',
                interval=1*1000, # in milliseconds
                n_intervals=0
                ),
            html.Div(
                children=[
                    html.Button(
                        id=f"toggle_fx{n}",
                        children=[
                            dcc.Loading(
                                html.Div(
                                    children=[
                                        html.Img(
                                            src="/assets/stompbox.png",
                                            width="80%",
                                            height="80%",
                                            ),
                                        html.H2(id=f"fx{n}_name", children=gt1000.dash_effects[n-1]["name"]),
                                        ],
                                    style={"color": "black"},
                                    )
                                )
                            ],
                        n_clicks=0,
                        style={"backgroundColor": gt1000.dash_effects[n-1]["color"]},
                        )
                    for n in range(1, nr_fx + 1)
                    ],
                style={
                    "display": "grid",
                    "grid-template-columns": f"repeat({nr_fx}, 1fr)",
                    "width": "100vw",
                    "height": "80vh",
                    "gap": "0",
                    },
                ),

            ],
        )


def register_callbacks(app):
    for n in range(1, nr_fx + 1):
        app.callback(
            Output(f"toggle_fx{n}", "style"),
            Input(f"toggle_fx{n}", "n_clicks"),
            prevent_initial_call=True,
        )(lambda n_clicks, fx_num=n: send_fx_state_command(fx_num, n_clicks))


def send_fx_state_command(fx_num, n_clicks):
    if not n_clicks:
        return
    if gt1000.dash_effects[fx_num - 1]["state"] == "ON":
        gt1000.send_message(gt1000.disable_fx(fx_num))
        # optimistically update here
        gt1000.dash_effects[fx_num - 1]["state"] = "OFF"
        return {"backgroundColor": off_color}
    else:
        gt1000.send_message(gt1000.enable_fx(fx_num))
        # optimistically update here
        gt1000.dash_effects[fx_num - 1]["state"] = "ON"
        return {"backgroundColor": on_color}

layout = serve_layout
register_callbacks(get_app())
