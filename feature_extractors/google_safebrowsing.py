#!/usr/bin/env python3
# Feature extractor that interfaces with sbserver from
# https://github.com/google/safebrowsing/

from .templates import FeatureExtractor
from util import config_loader

import atexit
import os
import pybloomfilter
import requests
import subprocess
import time

BLOOM_PATH = "training/urls.bloom"

PROBE_REQUEST_TIMEOUT = 1.5

# The maximum amount of time that sbserver is given to start up
MAX_STARTUP_TIME = 10

class SafeBrowsing(object):

    def __init__(self):
        """ Initialize SafeBrowsing class

        Args:
            api_key: The Google API key to use to initialize sbserver
            expand_urls: Whether or not SafeBrowsing should attempt to expand
                any URL that passes the initial lookup
            db_path: The path to store the safe browsing database in
        """

        config = config_loader.ConfigLoader().load()
        feature_config = config["feature_extractors"]

        self.expand_urls = bool(int(
            feature_config["google_safebrowsing_expand_urls"]
        ))
        self.address = feature_config["google_sbserver_address"]

        bloom_path = feature_config["google_safebrowsing_bloom"]
        bloom_capacity = int(
            feature_config["google_safebrowsing_bloom_capacity"]
        )
        bloom_error_rate = float(
            feature_config["google_safebrowsing_bloom_err_rate"]
        )

        self.proc = subprocess.Popen([
            "sbserver",
            "-apikey", config["credentials"]["google_api_key"],
            "-db", feature_config["google_sbserver_db_path"],
            "-srvaddr", self.address
        ])
        atexit.register(self.proc.kill)

        if (os.path.isfile(bloom_path)):
            self.bloom_cache = pybloomfilter.BloomFilter.open(bloom_path)
        else:
            self.bloom_cache = pybloomfilter.BloomFilter(
                bloom_capacity, bloom_error_rate, bloom_path
            )

        # Wait for server to start
        start_time = time.time()
        while True:
            try:
                requests.get("http://%s" % self.address)
                break
            except:
                if (time.time() - start_time > MAX_STARTUP_TIME):
                    raise Exception("sbserver took too long to start up")
                else:
                    time.sleep(0.1)

    def _sblookup(self, url):
        """ Raw sbserver request

        Args:
            url: The URL to look up

        Returns:
            The raw JSON of the response
        """

        response = requests.post(
            "http://%s/v4/threatMatches:find" % self.address,
            json = {
                "threatInfo": {
                    "threatEntries": [
                        {"url": url}
                    ]
                }
            }
        )

        assert response.status_code == 200

        return response.json()

    def expand(self, url, previous_url = None, n_recursions = 0):
        """ Try to "expand" a short URL

        Args:
            url: The URL to expand

        Returns:
            The expanded URL. This will be the same as the original URL if a
            link shortener was not used.
        """

        # normalize the url
        domain = url.split("//")[-1].split("/")[0].lower()
        path = "/".join(url.split("//")[-1].split("/")[1:])

        https_url = "https://%s/%s" % (domain, path)
        http_url = "http://%s/%s" % (domain, path)
        if (url.startswith("https://")):
            url = https_url
        else:
            url = http_url

        if (not url in self.bloom_cache):

            try:
                response = requests.get(
                    url,
                    allow_redirects = False,
                    timeout = PROBE_REQUEST_TIMEOUT,
                    verify = False
                )

            except requests.exceptions.Timeout:
                return url

            except Exception as e:
                print("ERROR for %s: %s" % (url, e))
                return url

            if ((response.status_code >= 200) and (response.status_code < 400)):

                if ("location" in response.headers):
                    next_url = response.headers["location"]

                    # link relative to root
                    if (next_url[0] == "/"):
                        next_url = "/".join(url.split("/")[:3] + [next_url])

                    print("following %s -> %s" % (url, next_url))
                    print("OK1")
                    return self.expand(next_url, url, n_recursions + 1)

                # no redirect instructions in the headers
                else:
                    self.bloom_cache.add(url)

            # status code is not >= 200 and < 400 (e.g. 404, etc)
            else:
                self.bloom_cache.add(url)

        # in cache
        else:
            pass

        return url

    def lookup(self, url, _expanded = False):
        """ Look up a URL

        This function will automatically try to "expand" a short URL by making
        a request directly to the web server.

        Args:
            url: The URL to look up
            _expanded: Indicates if this URL has been expaned already. URLs
                short URLs must be expanded before being checked against the
                database

        Returns:
            The URL's threat type, or None if it has none
        """

        content = self._sblookup(url)

        if ("matches" in content):
            return content["matches"][0]["threatType"]

        # if no match, attempt to expand the url
        elif (self.expand_urls):
            if (_expanded):
                return False
            else:
                return self.lookup(self.expand(url), _expanded = True)
        return False

    def shutdown(self):
        """ Shutdown sbserver """

        self.proc.kill()

# Chu, Gianvecchio, & Wang
class AverageSafeBrowsing(FeatureExtractor):
    """ Returns the number of URLs deemed malicious by the Google Safe Browsing
    API """

    def __init__(self):
        self.sbclient = SafeBrowsing()

    def run(self, user, tweets):

        score = 0

        for tweet in tweets:
            for url in tweet["entities"]["urls"]:
                if (self.sbclient.lookup(url["expanded_url"])):
                    score += 1

        return score
