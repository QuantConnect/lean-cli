#!/usr/bin/env bash

set -e
set -x

fail () {
    echo "$@" 1>&2
    exit 1
}

if [[ -z "$QC_USER_ID" || -z "$QC_API_TOKEN" ]]; then
    fail "These tests require QC_USER_ID and QC_API_TOKEN to be set"
fi

mkdir regression-testing
cd regression-testing

lean config set user-id "$QC_USER_ID"
lean config set api-token "$QC_API_TOKEN"
lean config set default-language python

lean init
