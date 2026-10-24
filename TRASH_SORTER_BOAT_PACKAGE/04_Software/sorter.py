"""Sorting loop: wait for an item at the camera, stop the belts, classify,
open the matching flap, run the belt until the item is in its bin, close."""
import collections
import logging
import threading
import time

import config

log = logging.getLogger("sorter")


def choose_bin(votes):
    """votes: list of (label, confidence). Majority label among confident,
    non-empty votes; low confidence or no majority -> fallback bin."""
    good = [l for (l, c) in votes if c >= config.MIN_CONFIDENCE and l != config.EMPTY_LABEL]
    if not good:
        if all(l == config.EMPTY_LABEL for (l, c) in votes):
            return None, None                      # empty belt: false trigger
        return config.FALLBACK_BIN, None
    label, n = collections.Counter(good).most_common(1)[0]
    if n * 2 <= len(votes):
        return config.FALLBACK_BIN, label
    return config.LABEL_TO_BIN.get(label, config.FALLBACK_BIN), label


class Sorter:
    def __init__(self, hw, camera, classifier, autostart=True):
        self.hw, self.camera, self.clf = hw, camera, classifier
        self.enabled = False
        self.state = "stopped"
        self.counts = {b: 0 for b in config.SERVO_CHANNELS}
        self.last = None
        self._stop = threading.Event()
        if autostart:
            threading.Thread(target=self._run, daemon=True).start()

    def set_enabled(self, on):
        self.enabled = on
        self.state = "stopped"
        if not on:
            self.hw.conveyor(1, 0)
            self.hw.conveyor(2, 0)

    def _belts(self, on):
        self.hw.conveyor(1, config.C1_SPEED if on else 0)
        self.hw.conveyor(2, config.C2_SPEED if on else 0)

    def sort_one(self):
        """One item is at the IR sensor. Returns the bin it went to (or None)."""
        self.state = "settling"
        time.sleep(config.SETTLE_S)
        self._belts(False)
        self.state = "classifying"
        votes = []
        for _ in range(config.VOTES):
            votes.append(self.clf.predict(self.camera.frame()) if self.clf else ("Other", 1.0))
        bin_no, label = choose_bin(votes)
        self.last = dict(label=label, bin=bin_no, votes=votes, t=time.time())
        if bin_no is None:                         # false trigger on an empty belt
            self.state = "running"
            self._belts(True)
            return None
        self.state = f"to bin {bin_no}"
        self.hw.flap(bin_no, True)
        time.sleep(0.4)                            # let the flap swing before the item arrives
        self.hw.conveyor(2, config.C2_SPEED)       # C1 stays paused so no second item lands
        time.sleep(config.TRAVEL_S[bin_no])
        self.hw.conveyor(2, 0)
        self.hw.flap(bin_no, False)
        if self.hw.item_present():                 # the item never left the camera zone
            self.set_enabled(False)
            self.state = "jam at camera - clear it and press Sorting ON"
            return None
        self.counts[bin_no] += 1
        log.info("item %s -> bin %s", label, bin_no)
        self.state = "running"
        self._belts(True)
        return bin_no

    def _run(self):
        while not self._stop.is_set():
            if not self.enabled:
                time.sleep(0.1)
                continue
            if self.state == "stopped":
                self.state = "running"
                self._belts(True)
            if self.hw.item_present():
                try:
                    self.sort_one()
                except Exception:
                    log.exception("sorting failed")
                    self.set_enabled(False)
            time.sleep(0.02)
