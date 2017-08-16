#!/usr/bin/env python3

from .templates import FeatureExtractor
import sklearn.feature_extraction.text

# Lee, Eoff, & Caverlee
class AverageTweetContentSimilarity(FeatureExtractor):
    """ Find the average cosine similarity of tweets """
    def run(self, user, tweets):
        similarities = []
        len_ = len(tweets)

        if (len_ == 1):
            return 0

        else:
            # https://stackoverflow.com/a/8897648
            vectorizer = sklearn.feature_extraction.text.TfidfVectorizer()
            tf_idf = vectorizer.fit_transform([tweet["text"] for tweet in tweets])
            tf_idf_matrix = (tf_idf * tf_idf.T).toarray()

            for i in range(len_ - 1):
                for j in range(i + 1, len_):
                    similarities.append(tf_idf_matrix[i][j])

            return float(sum(similarities) / len(similarities))
