from callbacks import register_callbacks
from dash import Dash, Input, Output, html, dcc, ctx  # type: ignore
import dash
from gt_1000.gt1000 import GT1000

gt1000 = GT1000()
#gt1000.open_ports()

app = Dash(__name__, use_pages=True, pages_folder="pages")

#app.layout = html.Div([
#    html.H1('Multi-page app with Dash Pages'),
#    html.Div([
#        html.Div(
#            dcc.Link(f"{page['name']} - {page['path']}", href=page["relative_path"])
#        ) for page in dash.page_registry.values()
#    ]),
#    dash.page_container
#])


app.layout = html.Div([
    html.Div(
        id="button-grid",
        children=[
            dcc.Link(
                id=f"page_{page['name']}",
                children=page['name'],
                href=page["relative_path"],
                style={
                    "backgroundColor": "green",
                    "display": "flex",
                    "justify-content": "center",
                    "align-items": "center",
                    "height": "100%",
                    "textDecoration": "none",
                    "color": "white",
                }
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
        children=[
            dash.page_container
        ],
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
})


#@app.callback([Input(f"page_{page['name']}", "n_clicks") for page in dash.page_registry.values()], prevent_initial_call=True)
#def func(*args):
#    trigger = ctx.triggered[0]
#    print(trigger)
#    page_name = trigger["prop_id"].split(".")[0].split("page_")[1]
#    this_page = None
#    for page in dash.page_registry.values():
#        if page['name'] == page_name:
#            this_page = page
#    print("You clicked button {}".format(trigger["prop_id"].split(".")[0]))
#    return this_page["relative_path"]


if __name__ == '__main__':
    app.run_server(debug=True, host="0.0.0.0")
