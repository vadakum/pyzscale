#!/bin/bash --login


export proj_base_path=~/Documents/pyzscale/
export instrument_path=/home/qoptrprod/data/dumps/
export zscale_config_path=~/.zscale
export log_path=~/logs

cd $proj_base_path
source ./.py311env/bin/activate
export PYTHONPATH=$proj_base_path:$PYTHONPATH:
nohup python ./md/oc_market_data_main.py -c ${zscale_config_path}/creds.json -i $instrument_path > ${log_path}/md.out 2>&1 &
sleep 1
ps -f