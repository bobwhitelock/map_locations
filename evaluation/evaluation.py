import os
import pickle

from config import SPATIALML_SIMPLE_DIR, SPATIALML_SIMPLE_LOCATIONS_DIR, \
    SPATIALML_IDENTIFIED_LOCATIONS_HIGHEST_POP_DIR, SPATIALML_IDENTIFIED_LOCATIONS_RANDOM_DIR


def evaluation(identified_locations_dir):

    # create overall lists containing the list of locations for each file for both the identified locations and the
    # gold standard, by unpickling the previously pickled files
    list_of_lists_of_identified_locs = []
    list_of_lists_of_gold_standard_locs = []
    for spatialml_file in os.listdir(SPATIALML_SIMPLE_DIR): # TODO change dir used to just testing files?
        # print("Unpickling locations from {}...".format(spatialml_file))

        # unpickle locations from specified dir
        with open(identified_locations_dir + spatialml_file, 'rb') as pickled_file:
            list_of_lists_of_identified_locs.append(pickle.load(pickled_file))

        # unpickle gold standard locations
        with open(SPATIALML_SIMPLE_LOCATIONS_DIR + spatialml_file, 'rb') as pickled_file:
            list_of_lists_of_gold_standard_locs.append(pickle.load(pickled_file))

    assert len(list_of_lists_of_identified_locs) == len(list_of_lists_of_gold_standard_locs), "length of lists should be equal"
    
    calculate_micro_average_f_measures(list_of_lists_of_identified_locs, list_of_lists_of_gold_standard_locs)


def calculate_micro_average_f_measures(list_of_lists_of_identified_locs, list_of_lists_of_gold_standard_locs):

    distance_threshold = 100

    recog_true_positives = 0
    recog_false_positives = 0
    recog_false_negatives = 0

    overall_true_positives = 0
    overall_false_positives = 0
    overall_false_negatives = 0

    # map of recognised locational references to actual, only for those where coordinates for both are identified,
    # to be used for evaluating disambiguation of correctly recognised locations below
    recognised_loc_refs_to_actual = {}

    # calculate figures for each document in turn
    for index in range(len(list_of_lists_of_identified_locs)):
        current_ided_locs = list_of_lists_of_identified_locs[index]
        current_gold_standard_locs = list_of_lists_of_gold_standard_locs[index]

        # list of locs in current gold standard locs which have been recognised, so after finding all true positives
        # can identify false negatives
        recognised_gold_standard_locs = []

        # find and add to sums of true and false positives for recognition
        for ided_loc in current_ided_locs:
            for gold_standard_loc in current_gold_standard_locs:

                # if same reference identified as location in both lists then is a true positive
                if consider_equal_references(ided_loc, gold_standard_loc):
                    recog_true_positives += 1
                    recognised_gold_standard_locs.append(gold_standard_loc)

                    # if gold standard location has a coordinate given and location reference found has been
                    # identified with a coordinate, add both to map so can evaluate disambiguation of recognized
                    # locations below
                    if gold_standard_loc.coordinate and ided_loc.identified_geoname and \
                            ided_loc.identified_geoname.coordinate:
                        recognised_loc_refs_to_actual[ided_loc] = gold_standard_loc

                    # break here as have determined is a recognition true positive as same text marked in gold
                    # standard - if this never happens and so break never reached, for-else clause below executes and
                    #  have determined as a recognition false positive
                    break

            # if ided loc not found in the gold standard then is a false positive for recognition
            else:
                recog_false_positives += 1

        # add to false negatives for recognition for each gold standard loc not found
        for gold_standard_loc in current_gold_standard_locs:
            if gold_standard_loc not in recognised_gold_standard_locs:
                recog_false_negatives += 1


        # Create new lists for those gold standard locations which include coordinates, and those identified locations
        # minus the ones which correspond to the gold standard locations without coordinates. These are for use in
        # evaluating the full pipeline, we remove list entries where no gold standard coordinates exist as no way to
        # tell if pipeline has identified these correctly.
        full_current_gold_standard_locs = [loc for loc in current_gold_standard_locs if loc.coordinate]
        potentially_full_current_ided_locs = list(current_ided_locs)
        for gold_standard_loc in current_gold_standard_locs:
            if not gold_standard_loc.coordinate:
                for ided_loc in potentially_full_current_ided_locs:
                    if ided_loc.start == gold_standard_loc.start and ided_loc.stop == gold_standard_loc.stop:
                        potentially_full_current_ided_locs.remove(ided_loc)

        # list of locs in current full gold standard locs which have been recognised, so after finding all true
        # positives can identify false negatives
        identified_full_gold_standard_locs = []

        # find and add to sums of true and false positives for overall pipeline
        for ided_loc in potentially_full_current_ided_locs:
            for gold_standard_loc in full_current_gold_standard_locs:

                # for an identified location to be a true positive for full pipeline it must both be identified as a
                # geoname with some coordinate (so comparison can be made), and must match a gold standard location
                # according to both consider_equal_references() and consider_identified_same()
                if ided_loc.identified_geoname and ided_loc.coordinate:
                    if consider_equal_references(ided_loc, gold_standard_loc) and \
                            consider_identified_same(ided_loc, gold_standard_loc, distance_threshold):
                                overall_true_positives += 1
                                identified_full_gold_standard_locs.append(gold_standard_loc)
                                break

            # if an identified location is not determined to be a true positive (so break above never reached),
            # it is a false positive
            else:
                overall_false_positives += 1

        # add to false negatives for overall pipeline for each gold standard location not found
        for gold_standard_loc in full_current_gold_standard_locs:
            if gold_standard_loc not in identified_full_gold_standard_locs:
                overall_false_negatives += 1


    # perform precision, recall, and F-measure calculations for recognition of locations and overall pipeline:
        # micro-average precision = sum(true positives) / sum(total positives)
        # micro-average recall = sum(true positives) / sum(true positives + false negatives)
        # micro-average F-measure = harmonic mean of precision and recall

    recog_precision = recog_true_positives / (recog_true_positives + recog_false_positives)
    recog_recall = recog_true_positives / (recog_true_positives + recog_false_negatives)
    recog_f_measure = harmonic_mean(recog_precision, recog_recall)

    overall_precision = overall_true_positives / (overall_true_positives + overall_false_positives)
    overall_recall = overall_true_positives / (overall_true_positives + overall_false_negatives)
    overall_f_measure = harmonic_mean(overall_precision, overall_recall)


    # calculate disambiguation precision from just recognised locations (recall not relevant)
    disambig_true_positives = 0
    disambig_false_positives = 0

    for recognised_loc in recognised_loc_refs_to_actual:
        actual_loc = recognised_loc_refs_to_actual[recognised_loc]

        if consider_identified_same(recognised_loc, actual_loc, distance_threshold):
            disambig_true_positives += 1
        else:
            disambig_false_positives += 1

    disambig_precision = disambig_true_positives / (disambig_true_positives + disambig_false_positives)

    # output results
    print("\n")

    print("Recognition")
    print("precision:", recog_precision)
    print("recall:", recog_recall)
    print("F-measure:", recog_f_measure)

    print("\n")

    print("Disambiguation")
    print("precision:", disambig_precision)

    print("\n")

    print("Overall")
    print("precision:", overall_precision)
    print("recall:", overall_recall)
    print("F-measure:", overall_f_measure)


def harmonic_mean(precision, recall):
    return (2 * precision * recall) / (precision + recall)


def consider_equal_references(candidate_loc_ref, actual_loc_ref):
    """ Return boolean value of whether can consider locational references to be the same; this is True if and only
        if they occupy the exact same area.
    """

    if candidate_loc_ref.start == actual_loc_ref.start and candidate_loc_ref.stop == actual_loc_ref.stop:
        return True
    else:
        return False


def consider_identified_same(identified_loc, actual_loc, distance_threshold):
    """ Return boolean value of whether can consider the two locations to be identified as the same location. For
        this to be True they must have the same name and coordinates within the given distance threshold.
    """

    if identified_loc.name == actual_loc.name and \
            identified_loc.coordinate.distance_to(actual_loc.coordinate) <= distance_threshold:
        return True
    else:
        return False

if __name__ == '__main__':
    # evaluation(SPATIALML_IDENTIFIED_LOCATIONS_HIGHEST_POP_DIR)
    evaluation(SPATIALML_IDENTIFIED_LOCATIONS_RANDOM_DIR)