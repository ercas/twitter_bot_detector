twitter_bot_detector
====================

``twitter_bot_detector`` is a utility that attempts to detect twitter bots,
given information about a user and a list of their tweets, obtained from the
`Twitter API <https://dev.twitter.com/overview/api>`_.

Most concepts are taken from the following papers:

* `The Rise of Social Bots <https://arxiv.org/pdf/1407.5225.pdf>`_, by Ferrara,
  Varol, Davis, Menczer, & Flammini
* `Detecting Automation of Twitter Accounts: Are You a Human, Bot, or Cyborg?
  <http://ieeexplore.ieee.org/document/6280553/?arnumber=6280553>`_, by Chu,
  Gianvecchio, & Wang

The following data is included in this repository:

* ``training/caverlee_{ham,spam}_geotagged.txt``: Lists of user IDs from the
  caverlee-2011 dataset associated with geotagged tweets
* ``training/twitter_clients.csv``: A list of Twitter clients found in a subset
  of our sample data, ordered by the number of occurrances. The ``MOSTLY_BOT``
  column of the first 100 clients have manually been entered as ``-1``, ``0``,
  ``1``, or left blank, where ``-1`` indicates that an account's tweets appear
  to be mostly manually-written, ``0`` indicates that the tweets seem to be a
  mix of manually-written and computer-generated tweets or that the tweets
  appear to be computer-generated but with significant human interaction, ``1``
  indicates that the tweets appear to be mostly computer-generated with minimal
  human interaction, and blank indicates that a decision could not be made.

usage
-----

configuration
~~~~~~~~~~~~~

Due to the fragmented nature of the source, all ``twitter_bot_detector``
configuration is done by editing a single ``config.ini`` file that stores all
settings that are meant to be configured or modified by the end-user.
Initially, this file does not exist, and upon running ``botdetector.py`` for
the first time, it will be created by copying ``config.ini.skel``.

The following is a list of all sections and keys in the ``config.ini`` file:

.. list-table::

   * - name
     - type
     - description
   * - **credentials**
     - **section**
     - Credentials used to authenticate APIs
   * - .google_api_key
     - string
     - The Google API key to be used to initialise the Safe Browsing sbserver
   * - .twitter_*
     - string
     - A collection of four API keys and secrets needed to make authenticated
       requests to the Twitter API
   * - **sources**
     - **section**
     - External sources containing data that ``twitter_bot_detector`` uses
   * - .caverlee_2011
     - string url
     - The URL pointing to a zip file of the caverlee-2011 dataset
   * - **setup**
     - **section**
     - Contains information about the state of ``twitter_bot_detector``
       components
   * - .trained_crm114
     - string y/n
     - Indicates whether or not the CRM114 discriminator has been used **do not
       touch; will be moved to a different file in the future**
   * - **feature_extractors**
     - **section**
     - Configuration for the various feature extractors
   * - .google_sbserver_address
     - string
     - The address that the Safe Browsing ``sbserver`` will serve from
   * - .google_sbserver_db_path
     - string path
     - The path where the Safe Browsing ``sbserver`` will store its database
   * - .google_safebrowsing_bloom
     - string path
     - The path where the ``AverageSafeBrowsing`` feature extractor will store
       a bloom filter of seen URLs
   * - .google_safebrowsing_bloom_capacity
     - int
     - The capacity of the ``AverageSafeBrowsing`` bloom filter
   * - .google_safebrowsing_bloom_err_rate
     - float
     - The error rate of the ``AverageSafeBrowsing`` bloom filter
   * - .google_safebrowsing_expand_urls
     - int 1/0
     - Indicates whether or not the ``AverageSafeBrowsing`` feature extractor
       should attempt to expand all URLs - the sbserver does not recognize
       shortened URLs; turning this on will have the feature extractor make a
       request to every URL that passes the initial check in an attempt to
       expand shortened URLs
   * - .otp_bbox
     - comma-separated array of 4 floats
     - The leftmost, bottommost, rightmost, and topmost coordinates to use to
       generate the graph for the ``OTPTopSpeeds`` feature extractor
   * - .otp_name
     - string
     - The name of the graph to be generated and used by the ``OTPTopSpeeds``
       feature extractor
   * - .top_n_speed
     - int
     - The number of top speeds to average for the ``OTPTopSpeeds`` and
       ``StraightLineTopSpeeds`` feature extractors
   * - **classifier**
     - **section**
     - Configuration for the classifier
   * - .features
     - comma-separated array of strings
     - A list of all feature extractors to use, or ``all`` if all available
       feature extractors should be used
   * - .n_estimators
     - int
     - The number of trees to use in the random forest
   * - **training**
     - **section**
     - Contains training data
   * - .root
     - string
     - The root directory that training data will be stored in
   * - .crm114
     - string
     - The subdirectory of ``training.root`` that crm114 training data will be
       stored in
   * - .tweet_sources
     - string
     - The file in ``training.root`` containing annotated tweet source devices
   * - .spam_geotagged
     - string
     - The file in ``training.root`` containing the spam user IDs associated
       with geotagged tweets
   * - .ham_geotagged
     - string
     - The file in ``training.root`` containing the ham user IDs associated
       with geotagged tweets

..

hacking
-------

writing feature extractors
~~~~~~~~~~~~~~~~~~~~~~~~~~

All source code for feature extractors is contained in the
``feature_extractors/`` directory. To create a new feature extractor:

1. Create a new class that inherits from
   ``feature_extractors.templates.FeatureExtractor``, sits in a script in the
   ``feature_extractors/`` directory. The name of this class will be the name
   of the feature.
2. Define a ``run`` method that accepts two arguments: a `Twitter User
   <https://dev.twitter.com/overview/api/users>`_ and a list of `Tweets
   <https://dev.twitter.com/overview/api/tweets>`_, and returns a floating
   point or integer.

Classes in the feature extractor directory that inherit from
``FeatureExtractor`` will automatically be made available to the main script.

The following is an example of a valid feature extractor:

.. code-block:: python

    #!/usr/bin/env python3

    from .templates import FeatureExtractor

    class TweetCount(FeatureExtractor):
        """ Returns the number of tweets """
        def run(self, user, tweets):
            return len(tweets)

..
