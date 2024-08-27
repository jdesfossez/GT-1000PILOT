from pygt1000 import GT1000
import logging


menu_color1 = "#ABBACC"
menu_color2 = "#C1C9CB"
# off_color = "#F2E9D8"
off_color = "white"
on_color = "#2D8C2A"

buttons_pc_height = 70

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

gt1000 = GT1000()
gt1000.dash_effects = {}

# Mac and Linux default portname prefixes
known_default_portname_prefixes = ["GT-1000", "GT-1000:GT-1000 MIDI 1"]


def open_gt1000(portname=None):
    opened = False
    if portname is None:
        portnames = known_default_portname_prefixes
    else:
        portnames = [portname]
    for portname in portnames:
        logger.info(f"Opening MIDI port {portname}")
        if not gt1000.open_ports(portname=portname):
            continue
        opened = True
    if not opened:
        return False
    gt1000.refresh_state()
    gt1000.start_refresh_thread()
    return True
