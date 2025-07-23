#!/bin/bash --login


export proj_base_path=/home/qoptrprod/apps/pyzscale
export instr_base_path=/home/qoptrprod/data/dumps
export zscale_config_path=~/.zscale
export log_path=/home/qoptrprod/logs

cd $proj_base_path
source ${proj_base_path}/.py311env/bin/activate
export PYTHONPATH=${proj_base_path}/:$PYTHONPATH:

nohup python ./md/oc_market_data_main.py -c ${zscale_config_path}/creds.json -i $instr_base_path > ${log_path}/md.out 2>&1 &
