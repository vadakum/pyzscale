#!/bin/bash --login

in=""
read -p "enter yes to kill: " in
if [[ $in == "yes" ]]
then
    echo "confirmation received, killing the bot"
    pkill -9 -f ./scale_bot/scale_bot_main.py
else
    echo "not killing the bot"
fi
