#!/usr/bin/env python3

import configparser
import crm114 # From https://github.com/ercas/crm114-python
import csv
import os
import shutil
import sys

import google_safebrowsing
from util import train_crm114

CONFIG_FILE = "config.ini"
CONFIG_FALLBACK = "config.ini.skel"

TRAINING_DIR = "training/"

# These are located in TRAINING_DIR
CRM114_TRAINING = "crm114"
TWEET_SOURCE_TRAINING = "twitter_clients.csv"

def prompt_yn(prompt):
    """ Persistent y/n prompt that only accepts yes or no

    Args:
        prompt: The prompt to be displayed

    Returns:
        True if the user answered with something that starts with "y" or did
        not provide an answer; False if the user answered with something that
        starts with "n"
    """

    response = input("%s (Y/n) " % prompt)

    if (len(response) == 0):
        return True
    else:
        first = response[0].lower()
        if ((first == "y")):
            return True
        elif (first == "n"):
            return False
        else:
            return prompt_yn(prompt)

class BotDetector(object):

    def __init__(self, training_dir = TRAINING_DIR):
        """ Initialize BotDetector """

        if (not os.path.isdir(training_dir)):
            os.mkdir(training_dir)

        if (os.path.isfile(CONFIG_FILE)):
            self.config = configparser.ConfigParser()
            try:
                self.config.read(CONFIG_FILE)
            except configparser.ParsingError as error:
                print(error)
                print("Please correct the errors and try again")
                sys.exit(1)
        else:
            print("Could not find %s; copying %s -> %s" % (
                CONFIG_FILE, CONFIG_FALLBACK, CONFIG_FILE
            ))
            shutil.copyfile(CONFIG_FALLBACK, CONFIG_FILE)
            print("Please edit this file before running again.")
            sys.exit(1)

        # crm classifier
        print("Initializing CRM114 discriminator")
        crm114_dir = "%s/%s" % (training_dir, CRM114_TRAINING)
        if (self.config["setup"]["trained_crm114"] == "n"):
            print("The CRM114 discriminator must be trained first.")
            response = prompt_yn("Train now using the caverlee-2011 dataset?")
            if (response):
                assert train_crm114.train(crm114_dir), "Training failed"
                self.config["setup"]["trained_crm114"] = "y"
                with open(CONFIG_FILE, "w") as f:
                    self.config.write(f)
            else:
                sys.exit(1)
        self.crm = crm114.Classifier(crm114_dir, ["spam", "ham"])

        # google sbserver client
        print("Initializing Google Safe Browsing sbserver and client")
        self.sbclient = google_safebrowsing.SafeBrowsing(
            api_key = self.config["credentials"]["google_api_key"]
        )

        # tweet sources dict
        print("Initializing tweet sources")
        self.tweet_sources = {
            "mostly_human": [],
            "mixed": [],
            "mostly_bot": []
        }
        with open("%s/%s" % (TRAINING_DIR, TWEET_SOURCE_TRAINING), "r") as f:
            for row in csv.DictReader(f):
                mostly_bot = row["MOSTLY_BOT"]
                client = row["CLIENT"]
                if (mostly_bot == "-1"):
                    self.tweet_sources["mostly_human"].append(client)
                elif (mostly_bot == "0"):
                    self.tweet_sources["mixed"].append(client)
                elif (mostly_bot == "1"):
                    self.tweet_sources["mostly_bot"].append(client)

        print("Finished initialization\n")

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
            tests = sorted([
                test[5:]
                for test in filter(lambda x: x.startswith("test_"), dir(self))
            ])
            print("Tests to run: %s" % ", ".join(tests))

        for test_name in tests:
            print("Running test: %s" % test_name)
            result = getattr(self, "test_%s" % test_name)(user, tweets)
            if ((type(result) is int) or (type(result) is float)):
                results[test_name] = result
            else:
                print("Test %s returned invalid value: %s" % (
                    test_name, result
                ))

        return results

    ## Test definitions

    def test_username_length(self, user, tweets):
        """ Returns the length of the user's screen name """

        return len(user["screen_name"])

    def test_followers_to_friends_ratio(self, user, tweets):
        """ Returns a user's follower count divided by their friends count """

        return user["followers_count"] / user["friends_count"]

    def test_tweets_with_links_proportion(self, user, tweets):
        """ Returns the proportion of tweets containing links """

        num_tweets = len(tweets)
        tweets_with_links = 0

        for tweet in tweets:
            if (len(tweet["entities"]["urls"]) > 0):
                tweets_with_links += 1

        return tweets_with_links / num_tweets

    def test_tweet_source_bot_score(self, user, tweets):
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

    def test_tweet_count(self, user, tweets):
        """ Returns the number of tweets """

        return len(tweets)

    def test_tweet_crm(self, user, tweets):
        """ Returns the average CRM114 discriminator classification score

        The crm114 module returns a tuple containing the category and a
        probability. For this test, there are only two categories - "spam", and
        "ham", a.k.a. not spam. For spam, the raw probability is used; for not
        spam, the raw probability is multiplied by negative 1. """

        scores = []

        for tweet in tweets:
            result = self.crm.classify(tweet["text"])
            if (result[0] == "ham"):
                scores.append(-result[1])
            else:
                scores.append(result[1])

        n_scores = len(scores)
        if (n_scores == 0):
            return 0
        else:
            return sum(scores)/n_scores

    def test_malicious_urls_googlesb(self, user, tweets):

        score = 0

        for tweet in tweets:
            for url in tweet["entities"]["urls"]:
                if (self.sbclient.lookup(url["expanded_url"])):
                    score += 1

        return score

    ## Placeholder test definitions

    def test_test(self, user, tweets):
        """ For testing purposes: returns 1 """

        return 1

    def test_invalid(self, user, tweets):
        """ For testing purposes: return nothing """

        pass

if (__name__ == "__main__"):
    import pymongo

    botdetector = BotDetector()

    collection = pymongo.MongoClient("localhost:27016")["local"]["geotweets"]
    #collection = pymongo.MongoClient()["local"]["tweets2"]

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
