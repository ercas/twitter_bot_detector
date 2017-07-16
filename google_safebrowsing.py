#!/usr/bin/env python3
# Wrapper interface for sbserver from https://github.com/google/safebrowsing/

import atexit
import requests
import subprocess
import time

ADDRESS = "localhost:8080"

DB_PATH = "training/google_safebrowsing.db"

# The maximum amount of time that sbserver is given to start up
MAX_STARTUP_TIME = 5

def expand(url):
    """ Try to "expand" a short URL

    Args:
        url: The URL to expand

    Returns:
        The expanded URL. This will be the same as the original URL if a link
        shortener was not used.
    """

    # TODO the only thing that matters in the context of this script is the
    # domain name, so it would be a good idea to cache expanded domain names to
    # prevent multiple requests to a single domain other than URL shortener
    # domains.
    #
    # 1. see if url's domain name is cached
    # 2a. if the domain name is cached, return the cached domain name
    # 2b. if not, make a request and see if the header has a location field. be
    #    sure to keep track of the number of requests we make.
    # 3a. if there is a location field on the first request, repeat at step 2
    # 3b. if not, return this url and cache the domain name

    try:
        response = requests.get(url, allow_redirects = False)
    except requests.exceptions.MissingSchema:
        response = requests.get("http://%s" % url, allow_redirects = False)

    #assert response.status_code == 200

    if ("location" in response.headers):
        return expand(response.headers["location"])
    else:
        return url

class SafeBrowsing(object):

    def __init__(self, api_key, db_path = DB_PATH, address = ADDRESS):
        """ Initialize SafeBrowsing class

        Args:
            api_key: The Google API key to use to initialize sbserver
            db_path: The path to store the safe browsing database in
            address: The address that sbserver should serve from
        """

        self.proc = subprocess.Popen(
            ["sbserver", "-apikey", api_key, "-db", db_path,
             "-srvaddr", address],
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE
        )
        atexit.register(self.proc.kill)
        self.address = ADDRESS

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

    def lookup(self, url, _expanded = False):
        """ Look up a URL

        This function will automatically try to "expand" a short URL by making
        a request directly to the web server.

        Args:
            url: The URL to look upu
        """

        content = self._sblookup(url)

        if ("matches" in content):
            return content["matches"][0]["threatType"]
        else:
            if (_expanded):
                return False
            else:
                return self.lookup(expand(url), _expanded = True)

    def shutdown(self):
        """ Shutdown sbserver """

        self.proc.kill()
