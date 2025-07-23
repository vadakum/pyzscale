#!/bin/bash --login


export proj_base_path=~/Documents/pyzscale
export log_path=~/logs

source ${proj_base_path}/.py311env/bin/activate
export PYTHONPATH=${proj_base_path}/:$PYTHONPATH:

log=${log_path}/jupyter.log

cd ${proj_base_path}/notebooks

nohup jupyter lab > $log 2>&1 &

echo "sleeping for 3 sec... before cat ${log}/jupyter.log"

sleep 3

cat $log



