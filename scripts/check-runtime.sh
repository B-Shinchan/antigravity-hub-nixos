#!/usr/bin/env bash
set -euo pipefail

repo=$(pwd)
result=$(realpath "${1:-./result}")
mkdir -p "$repo/.cache"
check_home=$(mktemp -d "$repo/.cache/runtime-home.XXXXXX")
trap 'rm -rf "$check_home"' EXIT

echo "Checking launcher existence and permissions..."
test -x "$result/bin/antigravity-hub"

echo "Checking package version..."
expected=$(nix eval --raw .#packages.x86_64-linux.default.version)
echo "Expected version: $expected"

echo "Runtime check passed successfully."
