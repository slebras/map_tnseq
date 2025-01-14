#!python3

import os
import sys
import logging
import json
import random
import string
import copy
import shutil
from full.MapTnSeq import RunMapTnSeq
from full.DesignRandomPool import RunDesignRandomPool
from full.HTMLReport import CreateHTMLdir
from full.GeneTableGenomePoolFileToScfPosBC import GeneTable_Barcodes_To_BarcodeGenes
from full.ScfPosBC_To_BarChartData import ScfPosBC_Info_To_Scaffolds
from full.ScfPosBC_to_MhtnData import PosScfBCDataToZScrPointsForValues
from util.upload_pool import upload_mutantpool_to_KBase

"""
Note:
    Limit on total number of Map TnSeq runs is arbitrarily set to 100 
    within program

    Only change to maptnseq config is fastq_fp_list and genome_fp
    designrandompool needs genes.GC, 
"""

def CompleteRun(map_cfg_fp, drp_cfg_fp, tmp_dir, pool_output_fp, gnm_nm, 
                KB_pool_bool, cfg_d, vp,
                models_dir=None):
    """
    Args:
        map_cfg_d (str): Path to config JSON dict for MapTnSeq 
            Among others, contains keys:
                genome_fp: (file path to genome fna file in tmp dir)

        drp_cfg_fp (str): Path to config JSON dict for Design Random Pool

        tmp_dir (str): Path to directory

        pool_output_fp (str): Output mutant pool file path.

        gnm_nm (str): Genome's scientific name.

        KB_pool_bool (boolean): Should we create a Mutant Pool Object within KBase?

        vp: validated params 
            Among others, contains keys:
                tnseq_model_name
    Returns:
        None

    Description:
        First we load the two config dicts to be used in MapTnSeq and Design 
        Random Pool.
        Then we initialize the dict we'll be using for HTML and add the
        genome name and TnSeq model info to it.
        Then, for each FASTQ input we run MapTnSeq and generate a TSV 
        file to be an input to DesignRandomPool. In doing this, we make
        a copy of the original MapTnSeq run_dict and update the variable
        keys (specifically 'fastq_fp' and 'output_fp').
    
            
    """

    # Checking inputs exist
    for x in [map_cfg_fp, drp_cfg_fp]:
        if not os.path.exists(x):
            raise Exception(x + " does not exist, cannot run without configs")


    # Loading MapTNSEQ Config Dictionary from JSON to python
    # why do we load this to JSON instead of passing it around as a python dict?
    with open(map_cfg_fp, "r") as g:
        map_cfg = json.loads(g.read())["values"]

    # LOADING DESIGN RANDOM POOL Config Dictionary from JSON to python
    # to be used after map tn seq has finished running
    with open(drp_cfg_fp, "r") as g:
        drp_cfg = json.loads(g.read())["values"]
    
    # Initializing dict to be used for HTML generation
    pre_HTML_d = {"genome_name": gnm_nm, "orig_fq_fns": map_cfg["orig_fq_fns"]}


    # We know what model we're using
    model_use_fp = map_cfg["model_fp"]

    #We get the model string
    with open(model_use_fp, "r") as f:
        # This includes pastEnd if that's there
        model_str = f.read().rstrip()

    pre_HTML_d["models_info"] = {
                "model_in_use": model_use_fp,
                "model_str": model_str,
                "model_name": os.path.basename(model_use_fp)
    }

    # One run per fastq file
    num_mts_runs = len(map_cfg['fastq_fp_list'])
    if  num_mts_runs > 100:
        raise Exception("Cannot run Map Tnseq on more than 100 files " \
                + "\n Currently: " + str(num_mts_runs))

    pre_HTML_d["MapTnSeq_reports_list"] = []
    MapTS_Output_fps = []

    if 'maxReads' not in map_cfg or map_cfg['maxReads'] is None:
        # maxReads set to ten billion arbitrarily
        map_cfg['maxReads'] = 10**10
    map_cfg['modeltest'] = False 

    current_map_cfg = copy.deepcopy(map_cfg)

    for i in range(num_mts_runs):

        current_map_cfg["fastq_fp"] = map_cfg['fastq_fp_list'][i]

        # (current MapTnSeq Table File)
        cMTS_output_fp = os.path.join(tmp_dir, "MTS_Table_" + str(i).zfill(3) + ".tsv")
        current_map_cfg['output_fp'] = cMTS_output_fp
        MapTS_Output_fps.append(cMTS_output_fp)

        logging.info("Running MapTnSeq on {}.\n Output {}".format(
                                                current_map_cfg["fastq_fp"], cMTS_output_fp))

        MTS_return_dict = RunMapTnSeq(current_map_cfg, DEBUGPRINT=False)
        pre_HTML_d["MapTnSeq_reports_list"].append(MTS_return_dict)

        # We reset the vars 
        current_map_cfg = copy.deepcopy(map_cfg)



    # Adding map tn seq table files to Design Random Pool Config:
    drp_cfg["map_tnseq_table_fps"] = MapTS_Output_fps
    drp_cfg["output_fp"] =  pool_output_fp

    # Running Design Random Pool
    DRP_report_dict = RunDesignRandomPool(drp_cfg, False)
    pre_HTML_d["DRP_report_dict"] = DRP_report_dict


    # Here we upload the mutant pool to KBase to make a mutantpool Object
    if KB_pool_bool:
        logging.info("UPLOADING mutant pool to KBASE through DataFileUtil")
        upload_params = {
                'username': cfg_d['username'],
                'genome_ref': vp['genome_ref'],
                'tnseq_model_name': vp['tnseq_model_name'],
                'fastq_refs': vp['fastq_ref_list'],
                'pool_description': vp['pool_description'] ,
                'workspace_id': cfg_d['ws_id'],
                'gene_hit_frac': DRP_report_dict['gene_hit_frac'],
                'ws_obj': cfg_d['ws'],
                'mutantpool_fp': cfg_d['pool_fp'],
                'mutantpool_name': vp['output_name'] + ".pool",
                'dfu': cfg_d['dfu']
                }
        upload_mutantpool_results = upload_mutantpool_to_KBase(upload_params)
        logging.info("Upload mutant pool Results:")
        logging.info(upload_mutantpool_results)


    logging.info("Beginning to create HTML Directory.")

    HTMLDisplayFiles_dir = "/kb/module/lib/map_tnseq/HTMLDisplayFiles"
   
    # We create the directories and HTML output (imported from HTMLReport.py)
    stats_dir, EBC_dir, MH_dir = CreateHTMLdir(tmp_dir, HTMLDisplayFiles_dir)

    # We write pre_HTML_d to output JS files
    # Preparing data for Statistics Data
    js_stats_data_fp = os.path.join(stats_dir, "StatsData.js")
    with open(js_stats_data_fp, "w") as f:
        f.write("window.statistics_d = " + json.dumps(pre_HTML_d, indent=2))

    # Preparing data for JS Display
    scfPosBC_fp = os.path.join(tmp_dir, "ScfPosBC.json")
    experiment_id = "Placeholder"
    GeneTable_Barcodes_To_BarcodeGenes(drp_cfg["genes_table_fp"], 
            pool_output_fp, 
            map_cfg['genome_fp'], 
            scfPosBC_fp, 
            gnm_nm,
            experiment_id
            )


    # Expanding Bar Chart Data
    EBC_data_dir = os.path.join(EBC_dir, "DATA")
    os.mkdir(EBC_data_dir)

    ScfPosBC_Info_To_Scaffolds(scfPosBC_fp, 
                                10, 
                                drp_cfg["genes_table_fp"], 
                                map_cfg["genome_fp"], 
                                EBC_data_dir
                                )
    
    # We move a specific file to the right loc
    shutil.move(os.path.join(EBC_data_dir,"EBC_Scaffolds_Init_Data.js"), EBC_dir)


    #MH Plot Data
    MH_data_fp = os.path.join(MH_dir, "MH_Data.js")
    PosScfBCDataToZScrPointsForValues(scfPosBC_fp, MH_data_fp, "1")

    return None






def FindWorkingModel(mts_dict, models_dir):
    """
    Given the directory with all the models, run through each and do a 
    maxReads = 10000 test on each.
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
    pool_output_fp = args[4] # the mutant pool to write to


    CompleteRun(map_cfg_fp, drp_cfg_fp, tmp_dir, pool_output_fp)



def main():
    test()

    return None

if __name__ == "__main__":
    main()


"""
DO NOT DELETE: WE COULD USE THIS TO FIND THE MODEL IF UNKNOWN
# Here we test for a working model
if map_cfg["modeltest"]:
    good_models_list = FindWorkingModel(map_cfg, models_dir)

    HTML_str = GetSingleModelHTML(good_models_list)

    # Print out HTML
    with open(html_fp, "w") as f:
        f.write(HTML_str)
    logging.info("Wrote html file to " + html_fp)

    #We return that the modeltest bool is true and that no mutant pool is created
    return [html_fp, True]
"""
