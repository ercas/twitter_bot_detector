#!/usr/bin/env python3

import crm114 # From https://github.com/ercas/crm114-python
import os

TRAINING_DIR = "training/"

CRM114_TRAINING_SUBDIR = "crm114/"

class BotDetector(object):

    def __init__(self, training_dir = TRAINING_DIR):
        """ Initialize BotDetector """

        if (not os.path.isdir(training_dir)):
            os.mkdir(training_dir)

        self.crm = crm114.Classifier(
            "%s/%s" % (training_dir, CRM114_TRAINING_SUBDIR),
            ["spam", "ham"]
        )

    def run_tests(self, user, tweets, tests = "all"):
        """ Run tests

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
            tests = sorted([
                test[5:]
                for test in filter(lambda x: x.startswith("test_"), dir(self))
            ])

        print("Tests to run: %s" % ",".join(tests))

        for test_name in tests:
            print("Running test: %s" % test_name)
            func = getattr(self, "test_%s" % test_name)
            results[test_name] = func(user, tweets)

        return results

    ## Begin tests

    def test_username_length(self, user, tweets):
        """ Returns the length of the user's screen name """

        return len(user["screen_name"])

    def test_followers_to_friends_ratio(self, user, tweets):
        """ Returns a user's follower count divided by their friends count """

        return user["followers_count"] / user["friends_count"]

    def test_links_ratio(self, user, tweets):
        """ Returns the proportion of tweets containing links """

        num_tweets = len(tweets)
        tweets_with_links = 0

        for tweet in tweets:
            if (len(tweet["entities"]["urls"]) > 0):
                tweets_with_links += 1

        return tweets_with_links / num_tweets

    def test_test(self, user, tweets):
        """ Always returns 1 """

        return 1

if (__name__ == "__main__"):
    import pymongo

    collection = pymongo.MongoClient()["local"]["tweets2"]
    user = collection.aggregate([{"$sample": {"size": 1}}]).next()["user"]
    tweets = list(collection.find({"user.id": user["id"]}))

    print(BotDetector().run_tests(
        user = user,
        tweets = tweets
    ))
