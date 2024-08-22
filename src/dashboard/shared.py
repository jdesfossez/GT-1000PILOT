from gt_1000.gt1000 import GT1000


off_color = "red"
on_color = "green"

gt1000 = GT1000()

def open_gt1000():
    if not gt1000.open_ports():
        return False
    gt1000.refresh_state()
    gt1000.start_refresh_thread()
    return True
