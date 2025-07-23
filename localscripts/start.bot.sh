#!/bin/bash --login


export proj_base_path=~/Documents/pyzscale/
export instrument_path=/home/qoptrprod/data/dumps/
export zscale_config_path=~/.zscale
export log_path=~/logs

cd $proj_base_path
source ./.py311env/bin/activate
export PYTHONPATH=$proj_base_path:$PYTHONPATH:

if [[ $1 == "" ]]
then
    echo "Please pass in the botconfig json file name"
    exit 1
fi
botcfg=$1

nohup python ./scale_bot/scale_bot_main.py -c ${zscale_config_path}/creds.json -b ${zscale_config_path}/${botcfg} > ${log_path}/scalebot.out 2>&1 &

sleep 1
ps -f
