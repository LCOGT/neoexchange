import os
from sys import argv
from glob import glob

from astropy.stats import sigma_clipped_stats
from astropy.table import Table, Column
import numpy as np


def run(config):

    tables = glob(f"{config['dataroot']}/202209??/{config['target_name']}_*/Temp_cvc_multiap/{config['target_name']}_data_*.txt")
    tables += glob(f"{config['dataroot']}/202210??/{config['target_name']}_*/Temp_cvc_multiap/{config['target_name']}_data_*.txt")

    output_table = make_summary_table(tables)
    filepath = output_target_data_table(config, output_table)
    print(f"Wrote summary table to {filepath}")

def make_summary_table(tables):
    data = []
    for table_filepath in tables:
        table = Table.read(table_filepath, format='ascii.commented_header')
        chunks = os.path.splitext(os.path.basename(table_filepath))[0].split('_')
        if len(chunks) == 3:
            obs_filter = chunks[2]
        datadir = table_filepath.split(os.path.sep)[-3]
        mean, median, std = sigma_clipped_stats(table['Magnitude'], sigma=3)

        # Find midpoint
        first = table['MJD'].min()
        last = table['MJD'].max()
        midpoint = (first+last)/2.0

        entry = [midpoint, mean, median, obs_filter, datadir]
        data.append(entry)
    data = np.array(data)

    # Format as an astropy Table:
    column_list = [ 
                    Column(data[:,0], name='mjd', dtype=np.float64, format='.6f'),
                    Column(data[:,1], name='mean_mag', dtype=np.float64, format='.5f'),
                    Column(data[:,2], name='median_mag', dtype=np.float64, format='.5f'),
                    Column(data[:,3], name='filter', dtype=str),
                    Column(data[:,4], name='datadir', dtype=str)]

    output_table = Table(column_list)
    return output_table

def output_target_data_table(config, target_data):
    """Function to output the target data table as a ECSV table"""

    filepath = set_output_file_path(config, target_data)

    # This is done to avoid concatenation of files that are produced more than
    # once.
    if os.path.isfile(filepath):
        os.remove(filepath)

    target_data.write(filepath, format='ascii.ecsv')
    return filepath

def set_output_file_path(config, descriptor):

    bandpass = descriptor['filter'][0]
    filepath = os.path.join(config['dataroot'],
                config['target_name']+'_data_'+str(bandpass)+'.ecsv')
    return filepath

def get_args():
    config = {}
    if len(argv) == 1:
        config['dataroot'] = input('Please enter the dataroot path: ')
    else:
        config['dataroot'] = argv[1]

    config['target_name'] = '65803'
    return config


if __name__ == '__main__':
    config = get_args()
    run(config)
