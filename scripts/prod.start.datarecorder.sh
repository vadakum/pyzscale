#!/bin/bash --login


export proj_base_path=/home/qoptrprod/apps/pyzscale
export instr_base_path=/home/qoptrprod/data/dumps
export dump_base_path=/home/qoptrprod/data/dumps
export log_path=/home/qoptrprod/logs

source ${proj_base_path}/.py311env/bin/activate
export PYTHONPATH=${proj_base_path}/:$PYTHONPATH:

cd $proj_base_path
nohup python ./md/md_dumper_main.py -d $dump_base_path > ${log_path}/dumper.out 2>&1 &

