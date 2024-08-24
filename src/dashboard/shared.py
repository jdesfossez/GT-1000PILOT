from gt_1000.gt1000 import GT1000
import logging


menu_color1 = "#ABBACC"
menu_color2 = "#C1C9CB"
off_color = "#F2E9D8"
on_color = "#2D8C2A"

buttons_pc_height = 60

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

gt1000 = GT1000()
gt1000.dash_effects = {}


def open_gt1000():
    if not gt1000.open_ports():
        return False
    gt1000.refresh_state()
    gt1000.start_refresh_thread()
    return True
