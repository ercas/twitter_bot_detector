#!/usr/bin/env python3
# dynamically load feature extractors

import importlib
import os
from .templates import FeatureExtractor

FEATURE_EXTRACTORS = {}

for module_name in [
    module_path[:-3] # remove the ".py$"
    for module_path in filter(
        lambda f: not f.startswith("__"),
        os.listdir(os.path.dirname(os.path.realpath(__file__)))
    )
]:
    module = importlib.import_module(".%s" % module_name, "feature_extractors")

    print("Searching for feature extractors in feature_extractors/%s.py"
          % module_name)
    for name in dir(module):
        attr = getattr(module, name)
        if (
            (type(attr) is type)
            and (issubclass(attr, FeatureExtractor))
            and (attr is not FeatureExtractor)
        ):
            print("> Found %s" % name)
            FEATURE_EXTRACTORS[name] = attr

print()
