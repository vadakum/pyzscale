#!/bin/bash --login


export proj_base_path=/home/qoptrprod/apps/pyzscale
export instrument_path=/home/qoptrprod/data/dumps/
export zscale_config_path=~/.zscale
export log_path=~/logs

cd $proj_base_path
source ./.py311env/bin/activate
export PYTHONPATH=$proj_base_path:$PYTHONPATH:

if [[ $1 == "" ]]
then
    day_name=`date +"%a" | tr '[:upper:]' '[:lower:]'`
    botcfg="botcfg.${day_name}.json"
    echo "bot config not passed in, using day wise bot file => ${botcfg}"
else
   botcfg=$1
fi

nohup python ./scale_bot/scale_bot_main.py -c ${zscale_config_path}/creds.json -b ${zscale_config_path}/${botcfg} > ${log_path}/scalebot.out 2>&1 &

sleep 1
echo "checking if bot has started ..."
ps -f
