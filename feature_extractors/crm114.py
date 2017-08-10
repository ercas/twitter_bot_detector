#!/usr/bin/env python3
# Feature extractor that uses the CRM114 classifier

from .templates import FeatureExtractor
from util import config_loader

import crm114 # From https://github.com/ercas/crm114-python

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

# Chu, Gianvecchio, & Wang
class AverageCRM114(FeatureExtractor):

    def __init__(self):
        config = config_loader.ConfigLoader().load()
        crm114_dir = "%s/%s" % (
            config["training"]["root"], config["training"]["crm114"]
        )

        if (config["setup"]["trained_crm114"] == "n"):
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

    def run(self, user, tweets):
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
