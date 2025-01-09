#!/usr/bin/env bash

# determine the directy of this file
if [ -n "$ZSH_VERSION" ]; then
    # shellcheck disable=SC2296
    this_file="${(%):-%x}"
else
    this_file="${BASH_SOURCE[0]}"
fi
this_dir="$( cd "$( dirname "$this_file" )" && pwd )"

# virtual environment location
venv_path=${this_dir}/.env 

source_lcg_stack() {
    local lcg_path=/cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh
    echo "Sourcing LCG stack from ${lcg_path}"
    source ${lcg_path}
}

action() {
    # LCG stack
    # source_lcg_stack

    _addpy() {
        [ -n "$1" ] && export PYTHONPATH="$1:$PYTHONPATH"
    }
    _addbin() {
        [ -n "$1" ] && export PATH="$1:$PATH"
    }

    if [ ! -f "${venv_path}/bin/activate" ]; then
        echo "No virtual environment created yet! Creating a new one at ${venv_path}"
        python3.12 -m venv ${venv_path}
        source "${venv_path}/bin/activate"
        python -m pip install --upgrade pip setuptools~=69.1.0 wheel
        echo "Installing software dependencies..."
        python -m pip install -r "${this_dir}/requirements.txt"
    else
        source "${venv_path}/bin/activate"
    fi

    if ! python -c "import simcal" &> /dev/null; then
        echo "Installing simcal..."
        python -m pip install .
    fi

    echo "==================================================="
    echo "simcal is ready to calibrate your simulation model!"
    echo "==================================================="
    
}

action "$@"
