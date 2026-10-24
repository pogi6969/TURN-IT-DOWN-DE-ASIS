"""Runs without a Pi:  python3 test_sorter.py"""
import time

import config
import sorter

config.TRAVEL_S = {b: 0.05 for b in config.TRAVEL_S}
config.SETTLE_S = 0.0


class FakeHW:
    def __init__(self):
        self.log, self.present = [], False

    def conveyor(self, which, speed):
        self.log.append(("belt", which, round(speed, 2)))

    def flap(self, b, open_):
        self.log.append(("flap", b, open_))
        if not open_:
            self.present = False          # item has gone into the bin

    def item_present(self):
        return self.present


class FakeClf:
    def __init__(self, votes):
        self.votes = list(votes)

    def predict(self, frame):
        return self.votes.pop(0)


class FakeCam:
    def frame(self):
        return None


def test_choose_bin():
    v = lambda *labels: [(l, 0.9) for l in labels]
    assert sorter.choose_bin(v("Can", "Can", "Can", "Paper", "Can")) == (2, "Can")
    assert sorter.choose_bin(v("Empty", "Empty", "Empty", "Empty", "Empty")) == (None, None)
    assert sorter.choose_bin(v("Can", "Paper", "Plastic bottle", "Can", "Paper"))[0] == config.FALLBACK_BIN
    assert sorter.choose_bin([("Paper", 0.4)] * 5) == (config.FALLBACK_BIN, None)
    assert sorter.choose_bin(v("Mystery", "Mystery", "Mystery", "Mystery", "Mystery"))[0] == config.FALLBACK_BIN


def test_sort_cycle():
    hw = FakeHW()
    s = sorter.Sorter(hw, FakeCam(), FakeClf([("Plastic bottle", 0.95)] * config.VOTES), autostart=False)
    hw.present = True
    assert s.sort_one() == 1
    flaps = [e for e in hw.log if e[0] == "flap"]
    assert flaps == [("flap", 1, True), ("flap", 1, False)]
    assert s.counts[1] == 1 and s.state == "running"
    assert ("belt", 1, 0) in hw.log and hw.log[-1][0] == "belt"


def test_jam_stops_belts():
    hw = FakeHW()
    s = sorter.Sorter(hw, FakeCam(), FakeClf([("Can", 0.95)] * config.VOTES), autostart=False)
    hw.flap = lambda b, o: hw.log.append(("flap", b, o))      # item never leaves
    hw.present = True
    s.enabled = True
    assert s.sort_one() is None
    assert not s.enabled and s.state.startswith("jam")


if __name__ == "__main__":
    test_choose_bin()
    test_sort_cycle()
    test_jam_stops_belts()
    print("all sorter tests passed")
