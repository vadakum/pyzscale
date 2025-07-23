#!/bin/bash --login


export proj_base_path=~/Documents/pyzscale/
export instrument_path=/home/qoptrprod/data/dumps/
export zscale_config_path=~/.zscale

cd $proj_base_path
source ./.py311env/bin/activate
export PYTHONPATH=$proj_base_path:$PYTHONPATH:
python ./md/instrument_downloader.py -c ${zscale_config_path}/creds.json -i $instrument_path


