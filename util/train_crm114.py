#!/usr/bin/env python3
# contains interactive procedure for downloading Twitter spam training data and
# using it to train the crm114 classifier

import configparser
import crm114
import os
import requests
import shutil
import subprocess
import sys
import zipfile

TEMP_DIR = "training/temp"
OUT_DIR = "training/caverlee_2011"
DL_PATH = "caverlee-2011.zip"

def save_file(url, output_path):
    """ Save a URL to a file

    Args:
        url: A string containing the URL to be saved.
        output_path: A string containing the path that the file will be saved
            to.

    Returns:
        True if the download succeeds, False if the download fails.
    """

    print(url)

    try:
        response = requests.get(url, stream = True)
    except:
        print("=> Download failed: %s" % url)
        return False

    if (response.status_code == 200):
        try:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size = 512):
                    if (chunk):
                        f.write(chunk)
                        sys.stdout.write("\r=> %s (%dkb)" % (output_path,
                                                             f.tell()/1024))
                        sys.stdout.flush()
                sys.stdout.write("\r=> %s (%dkb)" % (output_path,
                                                     f.tell()/1024))
                sys.stdout.flush()
            print("")
            return True

        except Exception as err:
            print("\n=> Error: %s (%s)" % (err, url))

    else:
        print("=> Download failed: %s" % url)
        return False

def train_caverlee(crm114_dir, category, input_file):
    print("Training category: \"%s\"" % category)

    # This is much faster and memory efficient than doing it the Python way
    subprocess.check_output(
        "cut -f 3 %s | "
        "crm '-{ learn <osb unique microgroom> (%s/%s.css) }'" % (
            input_file, crm114_dir, category
        ),
        shell = True
    )

def train(crm114_dir):
    config = configparser.ConfigParser()
    config.read("config.ini")

    if (save_file(config["sources"]["caverlee_2011"], DL_PATH)):

        # Create clean TEMP_DIR
        if (not os.path.isdir(TEMP_DIR)):
            os.makedirs(TEMP_DIR)
        else:
            for file_ in os.listdir(TEMP_DIR):
                shutil.rmtree("%s/%s" % (TEMP_DIR, file_))

        # Extract to TEMP_DIF
        print("Unzipping file")
        with zipfile.ZipFile(DL_PATH, "r") as z:
            z.extractall(TEMP_DIR)
        os.remove(DL_PATH)

        # Move desired files out of TEMP_DIR and remove TEMP_DIR
        if (os.path.isdir(OUT_DIR)):
            shutil.rmtree(OUT_DIR)
        os.rename("%s/social_honeypot_icwsm_2011" % TEMP_DIR, OUT_DIR)
        shutil.rmtree(TEMP_DIR)

        # Create clean crm114_dir
        if (not os.path.isdir(crm114_dir)):
            os.makedirs(crm114_dir)
        else:
            for file_ in os.listdir(crm114_dir):
                os.remove("%s/%s" % (crm114_dir, file_))

        # Train classifier
        train_caverlee(crm114_dir, "ham",
                       "%s/legitimate_users_tweets.txt" % OUT_DIR)
        train_caverlee(crm114_dir, "spam",
                       "%s/content_polluters_tweets.txt" % OUT_DIR)

        return True
