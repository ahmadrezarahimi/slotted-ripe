#!/bin/bash

echo -n "Choose a mode (1. Benchmark  2. Load From CSV) : "
read mode

if [ $mode -eq 1 ]; then
    echo -n "Do you want to run the benchmark with default parameters? n=[2,3,4,5,6] L=[10,20,30,40,50] (y/n) "
    read default_params

    if [ "$default_params" == "y" ]; then
        python3 main.py -m benchmark
    else
        echo -n "Enter the starting value for n: "
        read n_start
        echo -n "Enter the step size for n: "
        read n_step
        echo -n "Enter the number of steps for n: "
        read n_steps
        echo -n "Enter the starting value for L: "
        read L_start
        echo -n "Enter the step size for L: "
        read L_step
        echo -n "Enter the number of steps for L: "
        read L_steps

        python3 main.py -m benchmark -n_start $n_start -n_step $n_step -n_steps $n_steps -L_start $L_start -L_step $L_step -L_steps $L_steps

    fi
elif [ $mode -eq 2 ]; then
    python3 main.py -m load
else
    echo "Invalid mode selected"
    exit 1
fi
