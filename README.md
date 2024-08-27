# GT-1000PILOT - Remotely control a Boss GT-1000/GT-1000CORE

<p align="center">
<img width="200" alt="gt1000pilot-logo" src="https://github.com/user-attachments/assets/ef71fe17-919b-4a39-b296-84493101e417">
</p>

GT-1000PILOT is a web dashboard that lets you remotely control your Boss
GT-1000/GT-1000CORE effects in real-time over MIDI. Whether you’re jamming at
home or experimenting in the studio, GT-1000PILOT makes it easy to toggle
effects blocks, adjust levels, from your tablet or phone without interrupting
your playing.

This tool doesn’t replace Boss Tone Studio; instead, it complements it by
allowing you to see and modify the current state of each effects block quickly.
It’s designed to make your unit feel more like a traditional pedalboard,
offering a more dynamic and interactive way to shape your tone.

It doesn't interfere with any of the unit normal functions, it keeps refreshing
in the background to show the current state, so toggling effects, changing
patches with a different method works normally and after a few seconds the
current state is visible on the dashboard. It is really a companion app for the
unit !

For live/gig usage this is probably not ideal, but for home/studio it has
proven to be very fun and convenient to use !


<img width="500" alt="gt1000pilot-fx" src="https://github.com/user-attachments/assets/48bd7944-8d1a-449e-b419-6db9105991d7">
<img width="500" alt="gt1000pilot-comp" src="https://github.com/user-attachments/assets/518028ca-1603-41e0-96b0-0c3583e063e4">
<img width="500" alt="gt1000pilot-pedalfx" src="https://github.com/user-attachments/assets/429e2278-d8d9-4a81-9cae-3acde65d9d16">
<img width="500" alt="gt1000pilot-delays" src="https://github.com/user-attachments/assets/5cfd74b8-127e-461c-ba53-0c5445197190">

![usage](https://github.com/user-attachments/assets/9fb24edc-6d52-46ae-885a-a974bfc6e001)

## Usage

This has been tested on Mac, Linux, Windows 11 and even embedded in a Raspberry Pi hidden
on a pedalboard (so it always come up when the pedals are powered on).

This currently requires the host to be connected to the USB port of the unit,
but it could work just with MIDI connections, just need to add a convenient way
to configure the application.

Pre-built binary packages for Linux/Mac/Windows are available in the
[Releases](https://github.com/jdesfossez/pygt1000/releases) section. For a
more manual installation, you can follow the instructions from the Development
section below.

When the application starts (GUI or CLI), it connects to the unit, enables the
editor mode, and start the refresh loop to get the current state of the pedal.
When the initial sync is complete, it starts a small webserver so we can access
the dashboard remotely over Wifi.

The dashboard listens for HTTP on the port 8050, so you need to connect to the
machine running the program with an address like: `http://<your-ip>:8050`.
Finding the IP address of the host running the program depends on the operating
system running there. To access the dashboard from the same machine:
`http://localhost:8050` will work.

## Feedback

I would love to collect feedback and see what users of the GT-1000 think and
how we could improve the experience. This was started because I always feel
like I don't have enough buttons to trigger blocks and mapping all of that for
each patch gets annoying. Now I just create my patches with a lot of optional
blocks ready to fire and decide on the fly if I want them of not while playing.
This to me feels a bit more like a traditional pedalboard and makes it more fun
to use. Hopefully it is useful and fun for others as well ! Feel free to open
an issue, share your experiences, or suggest features that would make this tool
even better.

## Development

This tool is written in Python, the web dashboard is built using Dash and the
dependencies are managed with Poetry so after
[installing Poetry](https://python-poetry.org/docs/#installation) for your
platform

```
git clone https://github.com/jdesfossez/GT-1000PILOT
cd GT-1000PILOT
poetry install
poetry run python gt1000pilot/app.py [--gui]
```

It is also possible to install using `pip`:
```
pip install GT-1000PILOT
```

It depends mainly on the [pygt1000](https://github.com/jdesfossez/pygt1000)
library to interact with the pedal.

## Contributing

This is open source to make it possible to make the tool evolve to users needs.
I am not a web developer, so any help around CSS would be appreciated :-) !

Of course, contributions in all forms (feedback, improving the UI, adding new
features, or enhancing the documentation) is appreciated !
