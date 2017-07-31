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

ADDRESS = "localhost:8080"

DB_PATH = "training/google_safebrowsing.db"

BLOOM_PATH = "training/urls.bloom"

BLOOM_CAPACITY = 1000000

BLOOM_ERROR_RATE = 0.01

PROBE_REQUEST_TIMEOUT = 1.5

# The maximum amount of time that sbserver is given to start up
MAX_STARTUP_TIME = 10

class SafeBrowsing(object):

    def __init__(self, api_key, expand_urls = True, db_path = DB_PATH,
                 address = ADDRESS, bloom_path = BLOOM_PATH,
                 bloom_capacity = BLOOM_CAPACITY,
                 bloom_error_rate = BLOOM_ERROR_RATE):
        """ Initialize SafeBrowsing class

        Args:
            api_key: The Google API key to use to initialize sbserver
            expand_urls: Whether or not SafeBrowsing should attempt to expand
                any URL that passes the initial lookup
            db_path: The path to store the safe browsing database in
            address: The address that sbserver should serve from
            bloom_path: The path where the bloom filter containing the url
                expansion cache should be saved
            bloom_capacity: The capacity of the bloom filters
            bloom_error_rate: The error rate of the bloom filters
        """

        self.proc = subprocess.Popen([
            "sbserver",
            "-apikey", api_key,
            "-db", db_path,
            "-srvaddr", address
        ])
        atexit.register(self.proc.kill)
        self.address = ADDRESS
        self.expand_urls = expand_urls

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

    def expand(self, url):
        """ Try to "expand" a short URL

        Args:
            url: The URL to expand

        Returns:
            The expanded URL. This will be the same as the original URL if a
            link shortener was not used.
        """

        #domain = url.split("//")[-1].split("/")[0]

        #if (not domain in self.bloom_cache):
        if (not url in self.bloom_cache):
            try:
                try:
                    response = requests.get(url, allow_redirects = False,
                                            timeout = PROBE_REQUEST_TIMEOUT)
                except requests.exceptions.MissingSchema:
                    response = requests.get("http://%s" % url,
                                            allow_redirects = False,
                                            timeout = PROBE_REQUEST_TIMEOUT)
            except requests.exceptions.Timeout:
                return url

            if ((response.status_code >= 200) and (response.status_code < 400)):
                if ("location" in response.headers):
                    print("following %s -> %s" % (
                        url,
                        response.headers["location"]
                    ))
                    return self.expand(response.headers["location"])
                else:
                    #self.bloom_cache.add(domain)
                    self.bloom_cache.add(url)

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

class AverageSafeBrowsing(FeatureExtractor):

    def __init__(self):
        config = config_loader.ConfigLoader().load()

        self.sbclient = SafeBrowsing(
            api_key = config["credentials"]["google_api_key"]
        )

    def run(self, user, tweets):
        """ Returns the number of URLs deemed malicious by the Google Safe
        Browsing API """

        score = 0

        for tweet in tweets:
            for url in tweet["entities"]["urls"]:
                if (self.sbclient.lookup(url["expanded_url"])):
                    score += 1

        return score
