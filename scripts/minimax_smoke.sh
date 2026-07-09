#!/usr/bin/env bash
# Deprecated wrapper — use: enron-smoke [single|easy|full]
exec enron-smoke "${@:-single}"
