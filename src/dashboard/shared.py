from gt_1000.gt1000 import GT1000
import logging


off_color = "red"
on_color = "green"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

gt1000 = GT1000()


def open_gt1000():
    if not gt1000.open_ports():
        return False
    gt1000.refresh_state()
    gt1000.start_refresh_thread()
    return True
