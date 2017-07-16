twitter_bot_detector
====================

``twitter_bot_detector`` is a utility that attempts to detect twitter bots,
given information about a user and a list of their tweets, obtained from the
`Twitter API <https://dev.twitter.com/overview/api>`_.

Most concepts are taken from the following papers:

* `The Rise of Social Bots <https://arxiv.org/pdf/1407.5225.pdf>`_, by Ferrara,
  Varol, Davis, Menczer, & Flammini
* `Detecting Automation of Twitter Accounts: Are You a Human, Bot, or Cyborg?
  <ieeexplore.ieee.org/document/6280553/>`_, by Chu, Gianvecchio, & Wang

The following data is included in this repository:

* ``training/twitter_clients.csv``: A list of Twitter clients found in a subset
  of our sample data, ordered by the number of occurrances. The ``MOSTLY_BOT``
  column of the first 100 clients have manually been entered as ``-1``, ``0``,
  ``1``, or left blank, where ``-1`` indicates that an account's tweets appear
  to be mostly manually-written, ``0`` indicates that the tweets seem to be a
  mix of manually-written and computer-generated tweets or that the tweets
  appear to be computer-generated but with significant human interaction, ``1``
  indicates that the tweets appear to be mostly computer-generated with minimal
  human interaction, and blank indicates that a decision could not be made.
