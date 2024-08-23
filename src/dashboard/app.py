from callbacks import register_callbacks
from dash import Dash, Input, Output, html, dcc, ctx  # type: ignore
import dash_bootstrap_components as dbc
import dash
from gt_1000.gt1000 import GT1000
from shared import gt1000, open_gt1000, logger, menu_color1, menu_color2
from time import sleep

while not open_gt1000():
    logger.error("Failed to open GT1000 communication")
    sleep(1)

app = Dash(__name__, use_pages=True, pages_folder="pages")

app.layout = dbc.Container(
    fluid=True,  # Ensure the container takes up the full width of the viewport
    children=[
        # Top navigation bar (20% height)
        dbc.Row(
            dbc.Col(
                id="button-grid",
                children=[
                    dcc.Link(
                        id=f"page_{page['name']}",
                        children=page["name"].upper(),
                        href=page["relative_path"],
                        style={
                            "backgroundColor": menu_color1 if i % 2 == 0 else menu_color2,
                            "display": "flex",
                            "justify-content": "center",
                            "align-items": "center",
                            "textDecoration": "none",
                            "color": "black",
                            "padding": "0.5rem",
                            "height": "100%",
                            "width": "100%",
                        },
                    )
                    for i, page in enumerate(dash.page_registry.values())
                ],
                style={
                    "display": "grid",
                    "grid-template-columns": f"repeat({len(dash.page_registry)}, 1fr)",
                    "width": "100%",
                    "height": "100%",  # Ensure full height of this section is used
                    "gap": "0",
                    "box-sizing": "border-box",
                },
            ),
            className="h-20",
        ),

        # Middle section for buttons (70% height)
        dbc.Row(
            dbc.Col(
                children=dash.page_container,
                style={
                    "display": "flex",
                    "flex-direction": "column",
                    "justify-content": "center",  # Center content vertically
                    "align-items": "center",  # Center content horizontally
                    "height": "100%",  # Ensure the section takes up 70% height
                    "width": "100%",
                    "overflow-y": "auto",  # Allow scrolling if content overflows
                    "padding": "1rem",  # Optional padding
                    "box-sizing": "border-box",
                },
            ),
            className="h-70",
        ),

        # Bottom section for text (10% height)
        dbc.Row(
            dbc.Col(
                html.P(
                    "Some footer text here",
                    style={
                        "text-align": "center",
                        "margin": "0",
                        "padding": "1rem",
                        "font-size": "1rem",
                        "color": "gray",
                    }
                ),
                style={
                    "display": "flex",
                    "align-items": "center",
                    "justify-content": "center",
                    "background-color": "#f8f8f8",  # Light background for the footer
                    "height": "100%",  # Ensure full height of the allocated 10%
                },
            ),
            className="h-10",
        ),
    ],
    className="h-100",
)

if __name__ == "__main__":
    app.run_server(debug=False, host="0.0.0.0")
    gt1000.stop_refresh_thread()
