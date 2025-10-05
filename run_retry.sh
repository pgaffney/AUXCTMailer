#!/bin/bash
# Wrapper script to run retry_failed_emails.py with virtual environment activated

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run the retry script with all passed arguments
python retry_failed_emails.py "$@"
