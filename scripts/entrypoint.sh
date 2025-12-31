#!/bin/bash
#
# Custom Docker image entrypoint for Microsoft playwright container images for
# use with smith-tea-calendar.

# Install `uv`. We need a newer version of Python than what's available inside
# the image.
pip install uv

uvx playwright install chromium
uvx smith-tea-calendar "$@"
