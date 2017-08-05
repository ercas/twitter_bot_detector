#!/usr/bin/env python3

import configparser
import csv
import os
import shutil
import sys

from feature_extractors import FEATURE_EXTRACTORS
from util import train_crm114, config_loader

class FeatureExtractor(object):

    def __init__(self):
        """ Initialize FeatureExtractor """

        config = config_loader.ConfigLoader().load()

        training_dir = config["training"]["root"]
        if (not os.path.isdir(training_dir)):
            os.mkdir(training_dir)

        # dictionary of initialized feture extractors
        self.extractors = {}

    def initialize_feature_extractors(self, extractors):
        """ Initialize feature extractors if they have not been initialized yet

        Args:
            extractors: A list of feature extractors to be initialized
        """

        if (extractors == "all"):
            extractors = FEATURE_EXTRACTORS.keys()
        for extractor in extractors:
            if (not extractor in self.extractors):
                print("Initializing %s" % extractor)
                self.extractors[extractor] = FEATURE_EXTRACTORS[extractor]()

    def extract_features(self, user, tweets, features = "all"):
        """ Extract features

        Features are objects inheriting from
        feature_extractors.templates.FeatureExtractor and are defined in the
        scripts located in the feature_extractors module.

        Each feature extractor should take the user's JSON and an array of the
        user's tweets as arguments and return an integer or floating point.

        If a feature extractor does not return an integer or floating point, it
        is not added to the results dictionary.

        Args:
            user: A dictionary of the twitter user
            tweets: A list of tweet dictionaries
            features: A list of features to extract, or "all" to extract all of
                them

        Returns:
            A dictionary where the indices are the feature names and the values
            are the results
        """

        results = {}

        if (features == "all"):
            features = FEATURE_EXTRACTORS.keys()

        self.initialize_feature_extractors(features)

        for feature_extractor in sorted(features):
            assert feature_extractor in FEATURE_EXTRACTORS, (
                   "Feature extractor %s is undefined" % feature_extractor)

            print("Running %s" % feature_extractor)
            result = self.extractors[feature_extractor].run(user, tweets)
            if ((type(result) is int) or (type(result) is float)):
                results[feature_extractor] = result
            else:
                print("Feature extractor %s returned non-numeric value: %s" % (
                    feature_extractor, result
                ))

        return results

def sample_users(collection, n_users):
    """ Sample n unique users from a MongoDB collection of tweets

    Args:
        collection: A pymongo.collection.Collection object
        n_users: The number of users to sample

    Returns:
        A list of Twitter user dicts
    """

    return [
        doc["user"]
        for doc in collection.aggregate([
            {"$group": {
                "_id": "$user.id",
                "user": {"$first": "$user"}
            }},
            {"$sample": {"size": 3}}
        ])
    ]

def analyze_users(feature_extractor, users, output_csv_path,
                  feature_extractors = "all"):
    """ Create feature vectors from the given users

    Args:
        feature_extractor: A FeatureExtractor object
        users: A list of Twitter user dicts
        output_csv_path: The path that the feature vectors should be written to
        feature_extractors: A list of feature extractors to use, or "all" if
            all available feature extractors should be used
    """

    if (feature_extractors == "all"):
        feature_extractors = FEATURE_EXTRACTORS.keys()
    feature_extractors = sorted(feature_extractors)

    with open(output_csv_path, "w") as f:
        writer = csv.DictWriter(
            f, fieldnames = ["user_id", "username"] + feature_extractors
        )
        writer.writeheader()
        for user in users:
            user_id = user["id"]
            username = user["screen_name"]

            print("========== Running new test on user: @%s" % username)
            print("Querying tweets")
            tweets = list(collection.find({"user.id": user_id}))
            print("Collected %d tweets\n" % len(tweets))

            results = feature_extractor.extract_features(
                user = user,
                tweets = tweets,
                feature_extractors = feature_extractors
            )
            results.update({
                "user_id": user_id,
                "username": username
            })

            writer.writerow(results)

            print(results)
            print()

    print("Wrote feature vectors to %s" % output_csv_path)

def load_feature_vectors(csv_path, fields_to_remove = ["user_id", "username"]):
    """ Load feature vectors from a CSV generated by analyze_users

    Features that have been extracted during the feature extraction stage are
    extracted from the CSV column labels; when training a classifier, all that
    is needed is to make sure that both CSV files have the same columns

    Args:
        csv_path: The path to the csv file
        fields_to_remove: Extra fields in the CSV file that contain extra data
            and must be ignored. If no fields are to be removed, supply an
            empty list.

    Returns:
        A list of feature vectors with the features sorted by feature extractor
        names
    """

    feature_vectors = []

    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        feature_extractors = sorted(
            set(reader.fieldnames) - set(fields_to_remove)
        )

        for row in reader:
            row = {
                key: float(row[key])
                for key in feature_extractors
            }
            feature_vectors.append([
                row[feature_extractor]
                for feature_extractor in feature_extractors
            ])

    return feature_vectors

def train_classifier(spam_csv, ham_csv, n_estimators = 10):
    """ Train a random forest classifier by reading CSVs of feature vectors
    generated by analyze_users

    Args:
        spam_csv: The path to the CSV containing spammer feature vectors
        ham_csv: The path to the CSV containing normal user feature vectors
        n_estimators: The number of trees in the random forest

    Returns:
        A trained sklearn.ensemble.RandomForestClassifier object
    """

    classifier = sklearn.ensemble.RandomForestClassifier(
        n_estimators = n_estimators
    )

    spam_feature_vectors = load_feature_vectors(spam_csv)
    ham_feature_vectors = load_feature_vectors(ham_csv)

    feature_vectors = spam_feature_vectors + ham_feature_vectors
    class_labels = (["spam"] * len(spam_feature_vectors)
                    + ["ham"] * len(ham_feature_vectors))

    classifier.fit(feature_vectors, class_labels)

    return classifier

if (__name__ == "__main__"):
    import pymongo

    collection = pymongo.MongoClient()["local"]["geotweets"]
    feature_extractor = FeatureExtractor()

    feature_extractors = list(FEATURE_EXTRACTORS.keys())
    feature_extractors.remove("Invalid")

    analyze_users(
        feature_extractor,
        sample_users(collection, 3),
        "out.csv",
        feature_extractors = feature_extractors
    )
    #test_random_users(collection, feature_extractor, 3)
