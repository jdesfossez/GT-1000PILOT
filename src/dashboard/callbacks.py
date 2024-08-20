from dash import Input  # type: ignore


def register_callbacks(app, gt1000, midi_out):
    for n in range(1, 5):
        app.callback(
            Input(f"fx{n}_on", "n_clicks"),
            prevent_initial_call=True,
        )(lambda n_clicks, fx_num=n: send_fx_command(gt1000, midi_out, fx_num, "on", n_clicks))

        app.callback(
            Input(f"fx{n}_off", "n_clicks"),
            prevent_initial_call=True,
        )(lambda n_clicks, fx_num=n: send_fx_command(gt1000, midi_out, fx_num, "off", n_clicks))


def send_fx_command(gt1000, midi_out, fx_num, action, n_clicks):
    if not n_clicks:
        return
    if action == "on":
        out = gt1000.enable_fx(fx_num)
        print("OUT", out)
        midi_out.send_message(gt1000.enable_fx(fx_num))
    else:
        midi_out.send_message(gt1000.disable_fx(fx_num))
