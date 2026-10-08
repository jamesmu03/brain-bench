"""The brain-bench baseline as a submission: mean log band-power + logistic regression."""

from brainbench.benchmark import BandpowerLogReg


def build():
    return BandpowerLogReg()
