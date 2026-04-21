#!/bin/sh
# Sets git to use the .githooks directory in the repo
if [ ! -d ".githooks" ]; then
  echo ".githooks directory not found."
  exit 1
fi

git config core.hooksPath .githooks
if [ $? -eq 0 ]; then
  echo "Git hooks path set to .githooks"
else
  echo "Failed to set git hooks path"
  exit 1
fi
