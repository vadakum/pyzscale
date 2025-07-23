#!/bin/bash --login


export proj_base_path=~/Documents/pyzscale/
export instr_base_path=/home/qoptrprod/data/dumps
export log_path=~/logs

source ${proj_base_path}/.py311env/bin/activate
export PYTHONPATH=${proj_base_path}:$PYTHONPATH

cd $proj_base_path
