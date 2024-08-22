from callbacks import register_callbacks
from dash import Dash, Input, Output, html, dcc, ctx  # type: ignore
import dash
from gt_1000.gt1000 import GT1000
from shared import gt1000, open_gt1000, logger
from time import sleep

while not open_gt1000():
    logger.error("Failed to open GT1000 communication")
    sleep(1)

app = Dash(__name__, use_pages=True, pages_folder="pages")

app.layout = html.Div(
    [
        html.Div(
            id="button-grid",
            children=[
                dcc.Link(
                    id=f"page_{page['name']}",
                    children=page["name"],
                    href=page["relative_path"],
                    style={
                        "backgroundColor": "green",
                        "display": "flex",
                        "justify-content": "center",
                        "align-items": "center",
                        "height": "100%",
                        "textDecoration": "none",
                        "color": "white",
                    },
                )
                for page in dash.page_registry.values()
            ],
            style={
                "display": "grid",
                "grid-template-columns": f"repeat({len(dash.page_registry)}, 1fr)",
                "width": "100vw",
                "height": "20vh",
                "gap": "0",
            },
        ),
        html.Div(
            children=[dash.page_container],
            style={
                "flex": "1",  # Allows this div to grow and fill the remaining space
                "width": "100vw",
                "overflow": "auto",  # Adds scroll if content overflows
            },
        ),
    ],
    style={
        "display": "flex",
        "flex-direction": "column",  # Aligns children vertically
        "height": "100vh",  # Ensures full height of the viewport is used
        "margin": "0",
        "padding": "0",
    },
)

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0")
    gt1000.stop_refresh_thread()
