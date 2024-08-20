from dash import Input  # type: ignore


def register_callbacks(app, gt1000):
    for n in range(1, 5):
        app.callback(
            Input(f"fx{n}_on", "n_clicks"),
            prevent_initial_call=True,
        )(lambda n_clicks, fx_num=n: send_fx_command(gt1000, fx_num, "on", n_clicks))

        app.callback(
            Input(f"fx{n}_off", "n_clicks"),
            prevent_initial_call=True,
        )(lambda n_clicks, fx_num=n: send_fx_command(gt1000, fx_num, "off", n_clicks))


def send_fx_command(gt1000, fx_num, action, n_clicks):
    if not n_clicks:
        return
    if action == "on":
        gt1000.send_message(gt1000.enable_fx(fx_num))
    else:
        gt1000.send_message(gt1000.disable_fx(fx_num))
