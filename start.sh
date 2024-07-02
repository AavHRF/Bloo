#!/bin/bash

if ! command -v poetry &> /dev/null
then
    echo "poetry not installed. using pip instead. please consider using poetry!"
    source /venv/bin/activate
    python runner.py 2>&1 | tee bloo.log
else
    poetry run python runner.py 2>&1 | tee bloo.log
fi
