#!/bin/bash --login


export proj_base_path=/home/qoptrprod/apps/pyzscale
export instrument_path=/home/qoptrprod/data/dumps/
export log_path=~/logs

cd $proj_base_path
source ./.py311env/bin/activate
export PYTHONPATH=$proj_base_path:$PYTHONPATH:

clear
sleep 1
watch --color -n 3 python ./scale_bot/scale_bot_watch.py -b QGBOT-001 -p -o

