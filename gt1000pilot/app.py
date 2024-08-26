from dash import Dash, Input, Output, dcc  # type: ignore
import dash_bootstrap_components as dbc
import argparse
import flask
import signal
import dash
import requests
import threading
import os
from pathlib import Path
from gt1000pilot.shared import (
    gt1000,
    open_gt1000,
    logger,
    buttons_pc_height,
)
from time import sleep

try:
    import tkinter as tk

    cli_only = False
except Exception:
    print("tkinter not installed, running in CLI mode")
    cli_only = True


def launch(app):
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
                                "backgroundColor": "white",
                                "display": "flex",
                                "font-weight": "bold",
                                "justify-content": "center",
                                "align-items": "center",
                                "textDecoration": "none",
                                "color": "black",
                                "padding": "0.5rem",
                                "height": "100%",
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
                style={
                    "height": "20vh",
                    "width": "100vw",
                },
            ),
            # Middle section for buttons (70% height)
            dbc.Row(
                dbc.Col(
                    children=dash.page_container,
                    style={
                        "display": "flex",
                        "flex-direction": "column",
                        "flex-grow": "1",
                        "justify-content": "center",  # Center content vertically
                        "align-items": "center",  # Center content horizontally
                        "width": "100%",
                        "overflow-y": "auto",  # Allow scrolling if content overflows
                        "padding": "1rem",  # Optional padding
                        "box-sizing": "border-box",
                        "height": f"{buttons_pc_height}vh",
                        "flex": "1",
                    },
                ),
                style={
                    "height": f"{buttons_pc_height}vh",
                    "flex": "1",
                    "width": "100vw",
                    "flex-grow": "1",
                },
            ),
            # Bottom section for text (10% height)
            #        dbc.Row(
            #            dbc.Col(
            #                html.P(
            #                    "Some footer text here",
            #                    style={
            #                        "text-align": "center",
            #                        "margin": "0",
            #                        "padding": "1rem",
            #                        "font-size": "1rem",
            #                        "color": "gray",
            #                    }
            #                ),
            #                style={
            #                    "display": "flex",
            #                    "align-items": "center",
            #                    "justify-content": "center",
            #                    "background-color": "#f8f8f8",  # Light background for the footer
            #                    "height": "100%",  # Ensure full height of the allocated 10%
            #                },
            #            ),
            #            style={"height": "10vh"},
            #        ),
        ],
        style={"height": "100vh", "width": "100vw"},
    )

    app.run_server(debug=False, host="0.0.0.0")
    gt1000.stop_refresh_thread()

    # Consolidated callback to handle all link styles
    @app.callback(
        [
            Output(f'page_{page["name"]}', "style")
            for page in dash.page_registry.values()
        ],
        Input("_pages_location", "pathname"),
    )
    def update_all_link_styles(pathname):
        styles = []
        for page in dash.page_registry.values():
            if pathname == page["relative_path"]:
                styles.append(
                    {
                        "backgroundColor": "black",
                        "display": "flex",
                        "justify-content": "center",
                        "align-items": "center",
                        "textDecoration": "none",
                        "font-weight": "bold",
                        "color": "white",
                        "padding": "0.5rem",
                        "height": "100%",
                    }
                )
            else:
                styles.append(
                    {
                        "backgroundColor": "white",
                        "display": "flex",
                        "justify-content": "center",
                        "align-items": "center",
                        "textDecoration": "none",
                        "color": "black",
                        "font-weight": "bold",
                        "padding": "0.5rem",
                        "height": "100%",
                    }
                )
        return styles


class AppLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GT-1000PILOT Launcher")
        self.geometry("300x380")
        self.app_thread = None
        self.polling_thread = None
        self.stop_polling = threading.Event()

        # Load and resize the logo image
        logo_path = Path(__file__).parent / "logo.png"
        self.original_logo = tk.PhotoImage(file=logo_path)
        self.logo = self.original_logo.subsample(
            3, 3
        )  # Adjust the subsample values as needed

        # Display the image in a Label
        self.logo_label = tk.Label(self, image=self.logo)
        self.logo_label.pack(pady=10)

        # Status Label
        self.status_label = tk.Label(self, text="Application not started.", fg="red")
        self.status_label.pack(pady=10)

        # Start Button
        self.start_button = tk.Button(
            self, text="Start Application", command=self.start_app
        )
        self.start_button.pack(pady=10)

        # Quit
        self.stop_button = tk.Button(
            self, text="Quit", command=self.stop_app, state=tk.NORMAL
        )
        self.stop_button.pack(pady=10)

    def start_app(self):
        if self.app_thread is None:
            # self.stop_button.config(state=tk.NORMAL)
            self.start_button.config(state=tk.DISABLED)
            self.status_label.config(text="Loading application...", fg="orange")
            self.stop_polling.clear()
            self.polling_thread = threading.Thread(target=self.poll_server)
            self.polling_thread.start()

            # This needs to start before the Dash app
            if not open_gt1000():
                logger.error("Failed to open GT1000 communication")
                self.status_label.config(text="Failed to open GT-1000", fg="red")
                return

            # Apparently the only way to kill the GUI and dash app
            # looking for a better solution !
            server = flask.Flask(__name__)

            @server.route("/shutdown", methods=["POST"])
            def shutdown():
                pid = os.getpid()
                os.kill(pid, signal.SIGINT)

            # This cannot live in a thread
            app = Dash(
                __name__,
                use_pages=True,
                pages_folder="pages",
                server=server,
                external_stylesheets=[dbc.themes.BOOTSTRAP],
            )
            self.app_thread = threading.Thread(target=launch, args=(app,))
            self.app_thread.start()

    def stop_app(self):
        if self.app_thread:
            requests.post("http://localhost:8050/shutdown")
            self.app_thread.join()
        pid = os.getpid()
        os.kill(pid, signal.SIGINT)

    def poll_server(self):
        while not self.stop_polling.is_set():
            try:
                response = requests.get("http://localhost:8050")
                if response.status_code == 200:
                    self.status_label.config(text="Application is running. Connect to http://<your-ip>:8050", fg="green")
                    return
            except requests.ConnectionError:
                pass
            sleep(1)  # Poll every second
        self.status_label.config(text="Failed to start application.", fg="red")

    def on_closing(self):
        self.stop_app()
        self.destroy()

def cli_launch():
    while not open_gt1000():
        logger.error("Failed to open GT1000 communication")
        sleep(1)
    app = Dash(
            __name__,
            use_pages=True,
            pages_folder="pages",
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            )
    launch(app)

def gui_launch():
    launcher = AppLauncher()
    launcher.protocol("WM_DELETE_WINDOW", launcher.on_closing)
    launcher.mainloop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args()

    if cli_only or args.gui is False:
        cli_launch()
    else:
        gui_launch()
