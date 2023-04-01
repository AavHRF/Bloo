#!/bin/bash

poetry run python runner.py 2>&1 | tee bloo.log &