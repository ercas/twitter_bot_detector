#!/usr/bin/env python3

import configparser
import csv
import os
import sklearn.ensemble
import sklearn.externals
import shutil
import sys

from feature_extractors import FEATURE_EXTRACTORS
from util import train_crm114, config_loader

def sample_user_ids(collection, n_users):
    """ Sample n unique user IDs from a MongoDB collection of tweets

    Args:
        collection: A pymongo.collection.Collection object
        n_users: The number of user IDs to sample

    Returns:
        A list of Twitter user IDs
    """

    return [
        doc["_id"]
        for doc in collection.aggregate([
            {"$group": {
                "_id": "$user.id"
            }},
            {"$sample": {"size": 3}}
        ])
    ]

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
                print("Initializing feature extractor %s" % extractor)
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

        print("========== Extracting features for user @%s" % user["screen_name"])

        for feature_extractor in sorted(features):
            assert feature_extractor in FEATURE_EXTRACTORS, (
                   "Feature extractor %s is undefined" % feature_extractor)

            print("Running %s" % feature_extractor)
            result = self.extractors[feature_extractor].run(user, tweets)

            # Result validation
            if ((type(result) is int) or (type(result) is float)):
                results[feature_extractor] = result
            else:
                print("Feature extractor %s returned non-numeric value: %s" % (
                    feature_extractor, result
                ))

        print()

        return results

class Classifier(object):

    """ Classifier

    Attributes:
        feature_extractor: A FeatureExtractor object
        classifier: A sklearn.ensemble.RandomForestClassifier object
        features: A list of features being considered
    """

    def __init__(self):
        """ Initializes Classifier """

        config = config_loader.ConfigLoader().load()
        features = config["classifier"]["features"].split(",")

        self.collection = None
        self.feature_extractor = FeatureExtractor()
        self.classifier = sklearn.ensemble.RandomForestClassifier(
            n_estimators = int(config["classifier"]["n_estimators"])
        )

        if ((features == "all") or (features == ["all"])):
            features = FEATURE_EXTRACTORS.keys()
        self.features = sorted(features)

    def connect(self, db, collection):
        """ Connect to a MongoDB collection

        Args:
            db: The database to connect to
            collection: The collection to connect to
        """

        self.collection = pymongo.MongoClient()[db][collection]

    def collect_tweets(self, user_id):
        """ Query Mongo for tweets by a user

        To save on memory, we remove the "user" field from the tweets because
        it is redundant

        Args:
            user_id: The user ID to query for

        Returns:
            A dict containing the user's Tweet objects and a User object
        """

        assert self.collection is not None

        data = {
            "tweets": [],
            "user": None
        }

        cursor = self.collection.find(
            {"user.id": user_id},
            no_cursor_timeout = True
        )
        for doc in cursor:
            data["user"] = doc.pop("user") # Keep overwriting the "user" field
            data["tweets"].append(doc)
        cursor.close()

        return data

    def dict_to_feature_vector(self, features):
        """ Convert a dictionary generated by FeatureExtrctor.extract_features
        to a feature vector

        Args:
            features: A dictionary generated by
                FeatureExtractor.extract_features

        Returns:
            A feature vector in the form of a list
        """

        # convert to floats and remove extra fields (e.g. user, username)
        features = {
            key: float(features[key])
            for key in self.features
        }

        # convert to feature vector
        return [
            features[feature_extractor]
            for feature_extractor in self.features
        ]

    def gen_feature_matrix(self, user_ids, output_csv_path):
        """ Create feature vectors from the given users

        Args:
            users: A list of Twitter user IDs
            output_csv_path: The path that the feature vectors should be written to
            feature_extractors: A list of feature extractors to use, or "all" if
                all available feature extractors should be used
        """

        with open(output_csv_path, "w") as f:
            writer = csv.DictWriter(
                f,
                fieldnames = ["user_id", "username"] + self.features
            )
            writer.writeheader()
            for user_id in user_ids:
                print("========== Querying tweets for user ID %d" % user_id)

                data = self.collect_tweets(user_id)
                username = data["user"]["screen_name"]

                print("Collected %d tweets\n" % len(data["tweets"]))

                results = self.feature_extractor.extract_features(
                    user = data["user"],
                    tweets = data["tweets"],
                    features = self.features
                )
                results.update({
                    "user_id": user_id,
                    "username": username
                })

                writer.writerow(results)

                print(results)
                print()

        print("Wrote feature vectors to %s" % output_csv_path)

    def load_feature_vectors(self, csv_path):
        """ Load feature vectors from a CSV generated by extract_features

        Features that have been extracted during the feature extraction stage are
        extracted from the CSV column labels; when training a classifier, all that
        is needed is to make sure that both CSV files have the same columns

        Args:
            csv_path: The path to the csv file

        Returns:
            A list of feature vectors with the features sorted by feature extractor
            names
        """

        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)

            return [
                self.dict_to_feature_vector(row)
                for row in reader
            ]

    def train(self, spam_csv, ham_csv):
        """ Train a random forest classifier by reading CSVs of feature vectors
        generated by extract_features

        Args:
            spam_csv: The path to the CSV containing spammer feature vectors
            ham_csv: The path to the CSV containing normal user feature vectors
            n_estimators: The number of trees in the random forest

        Returns:
            A trained sklearn.ensemble.RandomForestClassifier object
        """

        spam_feature_vectors = self.load_feature_vectors(spam_csv)
        ham_feature_vectors = self.load_feature_vectors(ham_csv)

        feature_vectors = spam_feature_vectors + ham_feature_vectors
        class_labels = (["spam"] * len(spam_feature_vectors)
                        + ["ham"] * len(ham_feature_vectors))

        self.classifier.fit(feature_vectors, class_labels)

    def predict(self, user_ids):
        """ Classify users

        Args:
            user_ids: A list of user IDs to classify

        Returns:
            A dict of classifications for those user IDs
        """
        feature_vectors = []

        if (type(user_ids) is not list):
            user_ids = [user_ids]
        user_ids = sorted(user_ids)

        for user_id in user_ids:
            data = self.collect_tweets(user_id)
            feature_vectors.append(
                    self.dict_to_feature_vector(
                    self.feature_extractor.extract_features(
                        user = data["user"],
                        tweets = data["tweets"],
                        features = self.features
                    )
                )
            )

        return dict(zip(
            user_ids,
            self.classifier.predict(feature_vectors)
        ))

    def save(self, output_file):
        """ Save the current classifier as a pickle to a given path

        Args:
            output_file: The path to save the classifier to
        """

        sklearn.externals.joblib.dump(self.classifier, output_file)
        print("Saved classifier to %s" % output_file)

    def load(self, input_file):
        """ Overwrite the current classifier with one saved as a pickle at the
        given path

        Args:
            input_file: The path to load a new classifier from
        """

        self.classifier = sklearn.externals.joblib.load(input_file)
        print("Loaded classifier from %s" % input_file)


if (__name__ == "__main__"):
    import pymongo

    classifier = Classifier()

    # train spam
    classifier.connect("caverlee_2011", "spam")
    classifier.gen_feature_matrix(
        [13076522,16894297,16689819,5169871,16103653,11756702,14451520,10870512,16088048,16062813,15791454,10500072,15109598,16827174,8729092,11073902,16069206,15280950,5693062,15267659,1303381,16876002,15470773,15265269,11721472,16492068,16695328,15831817,15417706,16751024,14239363,16578783,11488822,15235767,14170609,14515351,16732408,15575441,6267832,14548188,14213042,15903869,16681194,16712700,15399951,13898062,7891352,15038084,16614336,15670317,14565842,14675924,15793787,14486811,4046051,16543782,15042759,15789733,15057807,2269491,14138443,16325332,16091975,16531768,10336042,14815178,16807407,14151220,16810740,2157321,14703881,16680079,15690188,10278192,15933218,14335577,12516722,16868319,964981,8208482,7601182,13694202,14744838,15930396,14306558,16736650,14185487,15854078,16250671,16722428,14507201,11403462,14947437,15412019,15958265,15211524,16194524,16656453,16507195,16616272],
        "spam.csv"
    )

    # train ham
    classifier.connect("caverlee_2011", "ham")
    classifier.gen_feature_matrix(
        [1479681,746493,5768612,6226962,3407301,6000292,3853071,639393,930581,431449710,5490362,4666751,1754641,6185922,5942122,5734332,3279441,5545702,5982032,4183941,5499142,5729562,6394912,1114011,6524962,5975342,709433,4148811,2192201,653843,823806,3895231,647073,6199812,6116332,784998,6462652,9375,5045711,5187721,2986671,1101481,1144181,5610822,3557911,1551941,808851,4795431,813669,1919751,5804942,2304641,6518212,1524641,4472691,5585092,2615,1095931,6283142,6060782,6393752,46183,6245442,3488401,3297261,2681441,5536782,5460902,12527,5486552,716013,756206,5641112,678323,6515802,5849872,6430992,2149371,4324361,4202781,3817911,56733,3602891,859571,3671881,6433962,5958822,5429672,3789291,5867462,5777162,666633,5513932,5663072,849591,6258452,3975731,1357191,5525392,5995592],
        "ham.csv"
    )

    # predict
    classifier.connect("caverlee_2011", "ham")
    classifier.train("spam.csv", "ham.csv")
    classifier.save("out.pkl")
    user_ids = [6367262,5768612,5429772,13602,3111701,4324361,859571,1421521,3655401,56733]
    print("\n========== Making predictions: %s" % ", ".join([
        str(x) for x in user_ids
    ]))
    print(classifier.predict(user_ids))
