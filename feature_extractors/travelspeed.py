#!/usr/bin/env python3
# Find the top n speeds by straight line or road network

import math

import otpmanager
import route_distances

from .templates import FeatureExtractor
from util import config_loader

RADIUS_OF_EARTH = 6371000

def law_of_cosines(lon1, lat1, lon2, lat2):
    """ Calculate the distance between two points on a sphere using the law of
    cosines

    Args:
        lon1, lat1: Floating point components of the first coordinate pair.
        lon2, lat2: Floating point components of the second coordinate pair.

    Returns:
        A floating point representing the distance between the two points, in
            meters.
    """

    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    return math.acos(
        (math.sin(lat1) * math.sin(lat2))
        + (math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    ) * RADIUS_OF_EARTH

class OTPTopSpeeds(FeatureExtractor):
    """ Find the average speed, in meters per second, of the top n fastest
    trips made by this user. n is defined in the "feature_extractors" section
    of config.ini; distances are calculated using OpenTripPlanner. """

    def __init__(self):
        config = config_loader.ConfigLoader().load()

        self.top_n = int(config["feature_extractors"]["top_n_speeds"])
        self.manager = otpmanager.OTPManager(
            config["feature_extractors"]["otp_name"],
            *tuple([
                float(x)
                for x in config["feature_extractors"]["otp_bbox"].split(",")
            ])
        )
        self.manager.start()
        self.router = route_distances.OTPDistances(
            "localhost:%d" % self.manager.port
        )

    def run(self, user, tweets):
        travel_speeds = []

        for i in range(len(tweets) - 1):
            origin = tweets[i]["coordinates"]["coordinates"]
            dest = tweets[i + 1]["coordinates"]["coordinates"]

            route = self.router.route(
                origin[0], origin[1], dest[0], dest[1],
                mode = "drive"
            )

            if (route):
                travel_time = (
                    int(tweets[i+1]["timestamp_ms"])
                    - int(tweets[i]["timestamp_ms"])
                ) / 1000
                travel_speeds.append(route["distance"] / travel_time)

        if (len(travel_speeds) > 0):
            top_n = sorted(travel_speeds)[-self.top_n:]
            return sum(top_n)/len(top_n)

        else:
            return 0

class StraightLineTopSpeeds(FeatureExtractor):
    """ Find the average speed, in meters per second, of the top n fastest
    trips made by this user. n is defined in the "feature_extractors" section
    of config.ini; distances are calculated using the law of cosines. """

    def __init__(self):
        config = config_loader.ConfigLoader().load()
        self.top_n = int(config["feature_extractors"]["top_n_speeds"])

    def run(self, user, tweets):

        travel_speeds = []

        for i in range(len(tweets) - 1):
            origin = tweets[i]["coordinates"]["coordinates"]
            dest = tweets[i + 1]["coordinates"]["coordinates"]

            travel_time = (
                int(tweets[i+1]["timestamp_ms"])
                - int(tweets[i]["timestamp_ms"])
            ) / 1000
            travel_distance = law_of_cosines(
                origin[0], origin[1], dest[0], dest[1]
            )
            travel_speeds.append(travel_distance / travel_time)

        if (len(travel_speeds) > 0):
            top_n = sorted(travel_speeds)[-self.top_n:]
            return sum(top_n)/len(top_n)

        else:
            return 0
