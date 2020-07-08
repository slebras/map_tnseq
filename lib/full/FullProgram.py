#!python3

import os
import sys
import logging
import json
import random
import string
import copy
from full.MapTnSeq import RunMapTnSeq
from full.DesignRandomPool import RunDesignRandomPool
from full.HTMLReport import CreateHTMLString, GetSingleModelHTML


"""
Note:
    Limit on total number of Map TnSeq runs is arbitrarily set to 100 
    within program

    Only change to maptnseq config is fastq_fp_list and genome_fp
    designrandompool needs genes.GC, 
"""

def CompleteRun(map_cfg_fp, drp_cfg_fp, tmp_dir, pool_output_fp, models_dir):
    """
    All inputs are strings

    map_cfg_d: (the dict from map_cfg_fp)
        modeltest: (bool)
    """

    # Checking inputs exist
    for x in [map_cfg_fp, drp_cfg_fp]:
        if not os.path.exists(x):
            raise Exception(x + " does not exist, cannot run without configs")


    # Loading MapTNSEQ Config Dictionary from JSON to python
    with open(map_cfg_fp, "r") as g:
        map_cfg = json.loads(g.read())["values"]

    

    pre_HTML_d = {}

    # Here we test for a working model
    if map_cfg["modeltest"]:
        good_models_list = FindWorkingModel(map_cfg, models_dir)

        HTML_str = GetSingleModelHTML(good_models_list)

        # Print out HTML
        html_fp = os.path.join("tmp", randomString(6) + ".html")
        with open(html_fp, "w") as f:
            f.write(HTML_str)
        logging.info("Wrote html file to " + html_fp)
        return html_fp

    # We know what model we're using
    model_use = map_cfg["model_fp"]

    pre_HTML_d["models_info"] = {
                "model_in_use": model_use
                }

    map_cfg["model_fp"] = model_use 
    # One run per fastq file
    num_mts_runs = len(map_cfg['fastq_fp_list'])
    if  num_mts_runs > 100:
        raise Exception("Cannot run Map Tnseq on more than 100 files " \
                + "\n Currently: " + str(num_mts_runs))

    pre_HTML_d["MapTnSeq_reports_list"] = []
    MapTS_Output_fps = []
    # maxReads set to ten billion arbitrarily
    map_cfg['maxReads'] = 10**10
    map_cfg['modeltest'] = False 

    current_map_cfg = copy.deepcopy(map_cfg)

    for i in range(num_mts_runs):

        current_map_cfg["fastq_fp"] = map_cfg['fastq_fp_list'][i]

        # Here we write the output filepath of the program 
        if i < 10:
            prefix = "0"
        else:
            prefix = ""

        # (current MapTnSeq Table File)
        cMTS_output_fp = os.path.join(tmp_dir, "MTS_Table_" + prefix + str(i) + ".tsv")
        current_map_cfg['output_fp'] = cMTS_output_fp
        MapTS_Output_fps.append(cMTS_output_fp)

        logging.info("Running map tn seq on {}.\n Output {}".format(
                                                current_map_cfg["fastq_fp"], cMTS_output_fp))

        report_dict = RunMapTnSeq(current_map_cfg, False)
        pre_HTML_d["MapTnSeq_reports_list"].append(report_dict)

        # We reset the vars 
        current_map_cfg = copy.deepcopy(map_cfg)


    # LOADING DESIGN RANDOM POOL INPUT
    with open(drp_cfg_fp, "r") as g:
        drp_cfg = json.loads(g.read())["values"]

    # Adding map tn seq table files:
    drp_cfg["map_tnseq_table_fps"] = MapTS_Output_fps
    drp_cfg["output_fp"] =  pool_output_fp

    # Running Design Random Pool
    DRP_report_dict = RunDesignRandomPool(drp_cfg, False)
    pre_HTML_d["DRP_report_dict"] = DRP_report_dict


    HTML_str = CreateHTMLString(pre_HTML_d)
    # Print out HTML
    html_fp = os.path.join(tmp_dir, randomString(6) + ".html")
    with open(html_fp, "w") as f:
        f.write(HTML_str)
    logging.info("Wrote html file to " + html_fp)

    return html_fp






def FindWorkingModel(mts_dict, models_dir):
    """
    Given the directory with all the models, run through each and do a 
    maxReads = 1000 test on each.
    models_dir is "./DATA/models"
    We need a single fastq file out of the list to do the test run.
    We choose the first one in the list fastq_fp_list

    Outputs:
        succesful_models: (list) list of lists, each sublist [model_fp, value]
        
    """

    # Getting all models files
    models_list = [os.path.join(models_dir, x) for x in os.listdir(models_dir)]

    # Getting the first fastq file set
    mts_dict['fastq_fp'] = mts_dict['fastq_fp_list'][0]

    # Ensuring max reads is 10000 
    mts_dict['maxReads'] = 10000
    mts_dict['modeltest'] = True
    mts_dict['output_fp'] = 'placeholder'
    succesful_models = []

    # Run through all the models
    for model_fp in models_list:
        new_program_d = copy.deepcopy(mts_dict)
        new_program_d['model_fp'] = model_fp
        returnCode, returnValue = RunMapTnSeq(new_program_d, False)
        if isinstance(returnCode, int):
            if returnCode == 0:
                succesful_models.append([model_fp, returnValue])
            logging.info("RETURN CODE: " + str(returnCode))

    just_good_models = [x[0] for x in succesful_models]
    logging.info("SUCCESFUL MODELS: " + "\n".join(just_good_models) + "\n")

    return succesful_models


def getBestModel(s_mdls_l):
    # succesful_models_list
    # s_mdls_l: (list) list of lists, each sublist [model_fp, value]
    # We want to return the best value of these
    max_val = 0
    max_index = 0
    for i in range(len(s_mdls_l)):
        cm = s_mdls_l[i]
        if cm[1] > max_val:
            max_val = cm[1]
            max_index = i

    best_model = s_mdls_l[max_index][0]
    logging.info("The best model was {} with a value of {}".format(best_model, max_val))

    return best_model 








def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


def test():
    logging.basicConfig(level=logging.DEBUG)
    # Program should be run FullProgram.py map_cfg.json drp_cfg.json tmp_dir output_fp
    args = sys.argv
    if args[1] == "how":
        print("Program should be run python3 FullProgram.py map_cfg.json drp_cfg.json" \
                + " tmp_dir output_fp")
        sys.exit(os.EX_OK)
    map_cfg_fp = args[1] # map tn seq config file path (contains all)
    drp_cfg_fp = args[2] # design random pool config file path (contains all)
    tmp_dir = args[3] # tmp dir to do work
    pool_output_fp = args[4] # the pool file to write to


    CompleteRun(map_cfg_fp, drp_cfg_fp, tmp_dir, pool_output_fp)



def main():
    test()

    return None

if __name__ == "__main__":
    main()