#!/bin/bash --login


cd ~/logs/
TODAY=$(date '+%Y%m%d')
nohup redis-server > redis${TODAY}.log 2>&1 &
