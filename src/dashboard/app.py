from callbacks import register_callbacks
from dash import Dash, html  # type: ignore
from gt_1000.gt1000 import GT1000

# Initialize the GT1000 class
gt1000 = GT1000()
ret = gt1000.open_ports()
print(f"Open ports: {ret}")

# Initialize the Dash app
app = Dash(__name__)

# Define the layout
app.layout = html.Div(
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
        "height": "100vh",
        "gap": "0",
    },
)

# Import and register callbacks
register_callbacks(app, gt1000)

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")
