#!/bin/bash

# Start the analysis worker
echo "Starting analysis worker..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the worker
python analysis_worker.py