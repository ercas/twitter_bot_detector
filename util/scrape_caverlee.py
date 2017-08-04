#!/usr/bin/env python3

import configparser
import json
import os
import tweepy

CONFIG_FILE = "config.ini"

CAVERLEE_DIR = "training/caverlee_2011/"
SPAMMERS = "%s/content_polluters.txt" % CAVERLEE_DIR
NOT_SPAMMERS = "%s/legitimate_users.txt" % CAVERLEE_DIR

OUTDIR = "training/caverlee_2011_tweets/"
SPAMMERS_OUTDIR = "spam/"
NOT_SPAMMERS_OUTDIR = "ham/"

PAGE_LIMIT = 3

class Scraper(object):

    def __init__(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)

        auth = tweepy.OAuthHandler(
            config["credentials"]["twitter_consumer_key"],
            config["credentials"]["twitter_consumer_secret"]
        )
        auth.set_access_token(
            config["credentials"]["twitter_access_key"],
            config["credentials"]["twitter_access_secret"]
        )
        self.api = tweepy.API(
            auth, wait_on_rate_limit = True, wait_on_rate_limit_notify = True
        )

    def scrape_user(self, user_id, page = 0, page_limit = PAGE_LIMIT):
        tweets = []

        print("retrieving page %d of user %s" % (page, user_id))
        timeline = self.api.user_timeline(
            user_id, count = 200, page = 15
        )

        tweets = [
            tweet._json
            for tweet in self.api.user_timeline(
                user_id, count = 200, page = page
            )
        ]

        if (len(tweets) > 0):
            if ((page_limit is None) or (page < page_limit)):
                tweets += self.scrape_user(user_id, page + 1)

        return tweets

if (__name__ == "__main__"):
    scraper = Scraper()

    outdir = "%s/%s" % (OUTDIR, SPAMMERS_OUTDIR)
    if (not os.path.isdir(outdir)):
        os.makedirs(outdir)

    with open(SPAMMERS, "r") as in_fp:
        for line in in_fp.readlines():
            user_id = line.split("\t")[0]
            outfile = "%s/%s.json" % (outdir, user_id)
            if (os.path.isfile(outfile)):
                print("already retrieved user %s" % user_id)
            else:
                tweets = scraper.scrape_user(user_id)
                with open(outfile, "w") as out_fp:
                    json.dump(tweets, out_fp)
