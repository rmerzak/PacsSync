#!/bin/bash
set -e

# Install any packages specified in the PIP_PACKAGES environment variable
if [ -n "$PIP_PACKAGES" ]; then
    echo "Installing additional packages: $PIP_PACKAGES"
    pip install --no-cache-dir $PIP_PACKAGES
fi

# Execute the command passed to docker run
exec "$@" 