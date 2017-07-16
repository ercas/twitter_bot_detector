#!/usr/bin/env python3
# build a list of Twitter clients by parsing the tweets of a MongoDB collection

import csv
import pymongo
import sys

OUTPUT_FILE = "twitter_clients.csv"

WRITE_INTERVAL = 10000

def write(output_file, dict_):
    """ Write a tally dictionary to a CSV file

    Args:
        output_file: The path of the output file
        dict_: A dictionary where the keys are strings and the values are ints
    """

    with open(output_file, "w") as f:
        f.write("COUNT,CLIENT\n")

        for row in sorted(
            dict_.items(),
            key = lambda x: x[1],
            reverse = True
        ):
            f.write("%s,%s\n" % (row[1], row[0]))

def main(address, db, collection, output_file = OUTPUT_FILE):
    clients = {}
    seen = 0

    cursor = pymongo.MongoClient(address)[db][collection].find(
        {"source": {"$exists": True}},
        no_cursor_timeout = True
    )

    for tweet in cursor:
        source = tweet["source"].split("/")[2].split("\"")[0]

        if (not source in clients):
            print("\nFound new client: %s           " % source)
            clients[source] = 1
        else:
            clients[source] += 1

        seen += 1
        sys.stdout.write("\rProcessed %d tweets" % seen)
        sys.stdout.flush()

        if (seen % WRITE_INTERVAL == 0):
            print("\nWriting snapshot of tallies")
            write(output_file, clients)


    cursor.close()

if (__name__ == "__main__"):
    import optparse

    parser = optparse.OptionParser()

    parser.add_option("-a", "--address", dest = "address",
                      default = "localhost:27017",
                      help = "The host and port where Mongo is located")
    parser.add_option("-d", "--db", dest = "db",
                      help = "The database where the tweets are stored")
    parser.add_option("-c", "--collection", dest = "collection",
                      help = "The collection where the tweets are stored")
    (options, args) = parser.parse_args()

    options = vars(options)
    if (not all(options.values())):
        parser.print_help()
    else:
        main(**options)
