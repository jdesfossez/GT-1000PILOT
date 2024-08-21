import dash
from dash import html

dash.register_page(__name__, path='/')

# Define the layout
layout = html.Div(
    id="button-grid",
    children=[
        html.Button(
            id=f"fx{n}_on",
            className="fx-button on-button",
            children=f"fx{n}_on",
            n_clicks=0,
            style={"backgroundColor": "green"},
        )
        for n in range(1, 5)
    ]
    + [
        html.Button(
            id=f"fx{n}_off",
            children=f"fx{n}_off",
            className="fx-button off-button",
            n_clicks=0,
            style={"backgroundColor": "red"},
        )
        for n in range(1, 5)
    ],
    style={
        "display": "grid",
        "grid-template-columns": "repeat(4, 1fr)",
        "width": "100vw",
        "height": "80vh",
        "gap": "0",
    },
)
