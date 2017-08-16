#!/usr/bin/env python3
# Simple feature extractors that maintain no internal state

from .templates import FeatureExtractor
import dateutil.parser

class Test(FeatureExtractor):
    """ For testing purposes: returns 1 """
    def run(self, user, tweets):
        return 1

'''
class Invalid(FeatureExtractor):
    """ For testing purposes: return nothing """
    def run(self, user, tweets):
        pass
'''

# Ferrara, Varol, Davis, Menczer, & Flammini
class AverageRetweetsPerTweet(FeatureExtractor):
    """ Returns the average number of retweets per tweet """
    def run(self, user, tweets):
        total_retweets = 0
        for tweet in tweets:
            total_retweets += tweet["retweet_count"]
        return total_retweets/len(tweets)

class AverageHashtagsPerTweet(FeatureExtractor):
    """ Returns the average number of retweets per tweet """
    def run(self, user, tweets):
        total_hashtags = 0
        for tweet in tweets:
            total_hashtags += len(tweet["entities"]["hashtags"])
        return total_hashtags/len(tweets)

# Lee, Eoff, & Caverlee
class AverageMentionsPerTweet(FeatureExtractor):
    """ Returns the average number of users mentioned per tweet """
    def run(self, user, tweets):
        total_mentions = 0
        for tweet in tweets:
            total_mentions += len(tweet["entities"]["user_mentions"])
        return total_mentions/len(tweets)

# Chu, Gianvecchio, & Wang
class FollowersToFriendsRatio(FeatureExtractor):
    """ Returns a user's follower count divided by their friends count """
    def run(self, user, tweets):
        friends = user["friends_count"]

        if (friends == 0):
            return 0
        else:
            return user["followers_count"] / friends

class TweetCount(FeatureExtractor):
    """ Returns the number of tweets """
    def run(self, user, tweets):
        return len(tweets)

# Chu, Gianvecchio, & Wang
class TweetsWithLinksProportion(FeatureExtractor):
    """ Returns the proportion of tweets containing links """
    def run(self, user, tweets):
        num_tweets = len(tweets)
        tweets_with_links = 0

        for tweet in tweets:
            if (len(tweet["entities"]["urls"]) > 0):
                tweets_with_links += 1

        return tweets_with_links / num_tweets

# Ferrara, Varol, Davis, Menczer, & Flammini
class UsernameLength(FeatureExtractor):
    """ Returns the length of the user's screen name """
    def run(self, user, tweets):
        return len(user["screen_name"])

# Chu, Gianvecchio, & Wang
class UserIsVerified(FeatureExtractor):
    """ Returns 1 if a user is verified and 0 if not """
    def run(self, user, tweets):
        return int(user["verified"])

# Chu, Gianvecchio, & Wang
class UserJoinDate(FeatureExtractor):
    """ Returns the user's join date as a Unix timestamp """
    def run(self, user, tweets):
        return int(dateutil.parser.parse(user["created_at"]))
