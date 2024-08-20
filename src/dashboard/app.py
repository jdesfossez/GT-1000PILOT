from callbacks import register_callbacks
from dash import Dash, html  # type: ignore
from gt_1000.gt1000 import GT1000
import rtmidi

PORTNAME = "UM-ONE"
midi_out = rtmidi.MidiOut()
port_count = midi_out.get_port_count()

for i in range(port_count):
    if midi_out.get_port_name(i).startswith(PORTNAME):
        midi_out.open_port(i)
        print(f"Opening port {i} {midi_out.get_port_name(1)}")
if not midi_out.is_port_open():
    print("Failed to open MIDI out port")

# Initialize the GT1000 class
gt1000 = GT1000()

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
register_callbacks(app, gt1000, midi_out)

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0")
