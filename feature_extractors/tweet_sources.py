#!/usr/bin/env python3
# Feature extractor that checks Tweet sources against a manually-annotated list

from .templates import FeatureExtractor
from util import config_loader

import csv

class TweetSources(FeatureExtractor):

    def __init__(self):
        config = config_loader.ConfigLoader().load()
        self.tweet_sources = {
            "mostly_human": [],
            "mixed": [],
            "mostly_bot": []
        }

        with open("%s/%s" % (
            config["training"]["root"], config["training"]["tweet_sources"]
        ), "r") as f:
            for row in csv.DictReader(f):
                mostly_bot = row["MOSTLY_BOT"]
                client = row["CLIENT"]
                if (mostly_bot == "-1"):
                    self.tweet_sources["mostly_human"].append(client)
                elif (mostly_bot == "0"):
                    self.tweet_sources["mixed"].append(client)
                elif (mostly_bot == "1"):
                    self.tweet_sources["mostly_bot"].append(client)

    def run(self, user, tweets):
        """ Returns the average score of the tweets' sources, where -1 means
        that all tweets came from a mostly human source, 0 means that all
        tweets came from a mixed human/bot source, and 1 means that all tweets
        came from a mostly bot source """

        scores = []

        for tweet in tweets:
            if ("source" in tweet):
                # this is the same cleanup algorithm as what is used in
                # util/gen_client_list.py
                try:
                    source = tweet["source"].split("\"")[1].split("/")[2]
                except IndexError:
                    continue

                if (source in self.tweet_sources["mostly_human"]):
                    scores.append(-1)
                elif (source in self.tweet_sources["mixed"]):
                    scores.append(0)
                elif (source in self.tweet_sources["mostly_bot"]):
                    scores.append(1)

        n_scores = len(scores)
        if (n_scores == 0):
            return 0
        else:
            return sum(scores)/n_scores
