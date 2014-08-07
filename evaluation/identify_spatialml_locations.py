""" Script to run pipeline and identify and disambiguate locations from the raw SpatialMl files, and pickle list of
    locations to a corresponding file.
"""

import os
import pickle

from config import SPATIALML_RAW_DIR, SPATIALML_IDENTIFIED_LOCATIONS_HIGHEST_POP_DIR
from utilities import read_from_file
from corenlp_interface import corenlp_tag_text
from identification import identify

# WARNING: takes quite a few minutes to process all files as need to make request to corenlp server for each file and
# access database multiple times for most files

def identify_spatialml_raw_locations():
    """ Main logic of script - for all raw SpatialML files run pipeline on and pickle resulting list of locations to
        a corresponding file.
    """

    for spatialml_file in os.listdir(SPATIALML_RAW_DIR):

        print("Processing {}...".format(spatialml_file))

        # run text in file through pipeline to get list of IdentifiedLocations
        text = read_from_file(SPATIALML_RAW_DIR + spatialml_file)
        corenlp_tagged_text =corenlp_tag_text(text)
        locations = identify(corenlp_tagged_text)

        # TODO deal with using different disambig methods better
        # pickle locations to corresponding file in corresponding dir
        with open(SPATIALML_IDENTIFIED_LOCATIONS_HIGHEST_POP_DIR + spatialml_file, 'wb') as pickle_file:
            pickle.dump(locations, pickle_file)


if __name__ == '__main__':
    identify_spatialml_raw_locations()
