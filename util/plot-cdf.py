#!/usr/bin/env python3
# usage: ./plot-cdf FeatureName

from matplotlib import pyplot
import csv
import sys

show = pyplot.show

class CDFPlotter(object):

    def __init__(self, feature, use_pyplot_hist = True):
        self.feature_max_values = []
        self.feature = feature
        self.use_pyplot_hist = use_pyplot_hist

    def plot(self, features_csv):
        with open(features_csv, "r") as f:
            data = sorted([
                float(row[feature])
                for row in csv.DictReader(f)
            ])

        self.feature_max_values.append(max(data))

        if (self.use_pyplot_hist):
            pyplot.hist(
                data, len(data),
                normed = 1, cumulative = True,
                label = features_csv,
                histtype = "step",
                linewidth = 2
            )
        else:
            pyplot.plot(
                data,
                [i/len(data) for i in range(len(data))],
                label = features_csv,
                linewidth = 2
            )

    def decorate(self):
        pyplot.grid(True)
        pyplot.ylabel("cdf")
        pyplot.xlabel(self.feature)
        pyplot.legend(loc = "upper left")

if (__name__ == "__main__"):
    feature = sys.argv[1]

    p = CDFPlotter(feature)
    p.plot("spam.csv")
    p.plot("ham.csv")
    p.decorate()

    pyplot.show()
