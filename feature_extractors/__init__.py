#!/usr/bin/env python3
# dynamically load feature extractors

import importlib
from .templates import FeatureExtractor

MODULES = [ "crm114", "google_safebrowsing", "simple", "tweet_sources" ]
FEATURE_EXTRACTORS = {}

for module_name in MODULES:
    module = importlib.import_module(".%s" % module_name, "feature_extractors")
    for name in dir(module):
        attr = getattr(module, name)
        if (
            (type(attr) is type)
            and (issubclass(attr, FeatureExtractor))
            and (attr is not FeatureExtractor)
        ):
            FEATURE_EXTRACTORS[name] = attr
