#!/bin/bash --login


export proj_base_path=~/Documents/pyzscale/
export instr_base_path=/home/qoptrprod/data/dumps
export dump_base_path=/home/qoptrprod/data/dumps

cd $proj_base_path
source ./.py311env/bin/activate
export PYTHONPATH=$proj_base_path:$PYTHONPATH:
nohup python ./md/md_dumper_main.py -d $dump_base_path > ~/logs/dumper.out 2>&1 &


