#/bin/bash
uncompyle6_merge_33_owd=$(pwd)
cd $(dirname ${BASH_SOURCE[0]})
if . ./setup-python-3.3.sh; then
    git merge python-3.6-to-3.10
fi
cd $uncompyle6_merge_33_owd
