#! /bin/bash

for test in $(ls *.py); do
    echo $test
    python3 "${test}"
done
