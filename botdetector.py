#!/usr/bin/env python3

import configparser
import os
import shutil
import sys

from feature_extractors import FEATURE_EXTRACTORS
from util import train_crm114, config_loader

class BotDetector(object):

    def __init__(self):
        """ Initialize BotDetector """

        config = config_loader.ConfigLoader().load()

        training_dir = config["training"]["root"]
        if (not os.path.isdir(training_dir)):
            os.mkdir(training_dir)

        self.extractors = {}

    def run_tests(self, user, tweets, tests = "all"):
        """ Run tests

        Tests are defined as methods of the BotDetector class and begin with
        the name "test_", followed by the test's name.

        Each test should take the user's JSON and an array of the user's tweets
        as arguments and return an integer or floating point.

        If a test does not return an integer or floating point, it is not
        added to the results dictionary.

        Args:
            user: A dictionary of the twitter user
            tweets: A list of tweet dictionaries
            tests: A list of tests to run, or "all" to run all of them

        Returns:
            A dictionary where the indices are the test names and the values
            are the results
        """

        results = {}

        if (tests == "all"):
            tests = FEATURE_EXTRACTORS.keys()

        for test_name in sorted(tests):
            assert test_name in FEATURE_EXTRACTORS, (
                   "Feature extractor %s is undefined" % test_name)

            if (not test_name in self.extractors):
                print("Initializing %s" % test_name)
                self.extractors[test_name] = FEATURE_EXTRACTORS[test_name]()

            print("Running %s" % test_name)
            result = self.extractors[test_name].run(user, tweets)
            if ((type(result) is int) or (type(result) is float)):
                results[test_name] = result
            else:
                print("Test %s returned invalid value: %s" % (
                    test_name, result
                ))

        return results

if (__name__ == "__main__"):
    import pymongo

    botdetector = BotDetector()

    #collection = pymongo.MongoClient("localhost:27016")["local"]["geotweets"]
    #collection = pymongo.MongoClient()["local"]["geotweets"]
    collection = pymongo.MongoClient()["local"]["tweets2"]

    print("Sampling random user")
    user = collection.aggregate([{"$sample": {"size": 1}}]).next()["user"]
    print("User: @%s" % user["screen_name"])
    print("Querying tweets")
    tweets = list(collection.find({"user.id": user["id"]}))
    print("Collected %d tweets\n" % len(tweets))

    print("\nResults: %s" % botdetector.run_tests(
        user = user,
        tweets = tweets,
        tests = "all"
    ))
