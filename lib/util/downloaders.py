#python3
import os
import logging
from Bio import SeqIO

# We download Genome Files: gfu is Genome File Util
def download_genome_convert_to_fna(gfu, genome_ref, scratch_dir):
    GenomeToGenbankResult = gfu.genome_to_genbank({'genome_ref': genome_ref})
    genbank_fp = GenomeToGenbankResult['genbank_file']['file_path']
    genome_fna_filename = "genome_fna"
    genome_fna_fp = os.path.join(scratch_dir, genome_fna_filename)

    #The following creates a file at genome_fna_fp
    SeqIO.convert(genbank_fp, "genbank", genome_fna_fp, "fasta")

    #Following gets important info from genbank file
    gt_config_dict = get_gene_table_config_dict(genbank_fp)

    return [genome_fna_fp, gt_config_dict, genbank_fp]


def download_fastq(dfu, fastq_refs_list, scratch_dir, output_fp):
    # We get multiple shock objects at once.
    get_shock_id_params = {"object_refs": fastq_refs_list, 
            "ignore_errors": False}
    get_objects_results = dfu.get_objects(get_shock_id_params)
    logging.debug(get_objects_results['data'][0])
    logging.debug(len(get_objects_results['data']))
    
    # We want to associate a ref with a filename and get a dict that has this
    # association

    raise Exception("STOP - INCOMPLETE")
    fq_shock_id = get_objects_results['data'][0]['data']['lib']['file']['id']
    fastq_download_params = {'shock_id': fq_shock_id,'file_path': fastq_fp, 'unpack':'unpack'}
    #Here we download the fastq file itself:
    logging.info("DOWNLOADING FASTQ FILE " + str(i))
    file_info = dfu.shock_to_file(fastq_download_params)
    logging.info(file_info)

# We want scaffold_name and description_name
def get_gene_table_config_dict(genbank_fp):
    record = SeqIO.read(genbank_fp, "genbank") 
    print(record.description)
    print(record.id)
    
    gene_table_config_dict = {
            "keep_types": ["1"],
            "scaffold_name": record.id,
            "description": record.description}

    return gene_table_config_dict

def test():
    get_gene_table_config_dict(
            '/Users/omreeg/tmp/Test_Files/E_Coli_BW25113.gbk')

