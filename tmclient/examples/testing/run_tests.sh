#! /bin/bash
#
# Run a test script against a local TM server, optionally checking out
# code from different branches for comparison.
#

# This script makes a number of assumptions about the execution
# environment, which may make it unsuitable for general usage as-is:
#
# * The companion test script is hard-coded to be `test_datasets.py`
#   (in the same source directory as `run_tests.sh`)
#
# * The `allure` [1] and `junit2html` [2] commands are used to compile
#   the `.xml` files into a human-readable HTML report. They are not
#   part of a standard Ubuntu or CentOS distribution and must be
#   installed separately.
#
# * The user running the tests has enough privileges to execute `sudo
#   service uwsgi restart` to restart the TM server (necessary after
#   checking out new code).
#
# [1]: https://bintray.com/qameta/generic/allure2
# [2]: https://github.com/inorton/junit2html/tree/master/junit2htmlreport

#
me="$(basename $0)"

usage () {
cat <<EOF
Usage: $me [options] -- DATASET_DIR [PARAMS_FILE] [test script options]

Run a test script against a local TM server, checking out code from
different branches.  Optional argument NUM sets the number of times
the test suite is run (by default: 1).

Options:

  --branches, -b    List of Git branches to test (comma-separated).
  --replicates NUM, -N NUM
                    Run each test suite NUM times over.
  --help, -h        Print this help text.

EOF
}


## defaults

branches='master develop'
N=1


## helper functions

# see /usr/include/sysexit.h
EX_OK=0           # successful termination
EX_USAGE=1        # command line usage error
EX_DATAERR=65     # data format error
EX_NOINPUT=66     # cannot open input
EX_NOUSER=67      # addressee unknown
EX_NOHOST=68      # host name unknown
EX_UNAVAILABLE=69 # service unavailable
EX_SOFTWARE=70    # internal software error
EX_OSERR=71       # system error (e.g., can't fork)
EX_OSFILE=72      # critical OS file missing
EX_CANTCREAT=73   # can't create (user) output file
EX_IOERR=74       # input/output error
EX_TEMPFAIL=75    # temp failure; user is invited to retry
EX_PROTOCOL=76    # remote error in protocol
EX_NOPERM=77      # permission denied
EX_CONFIG=78      # configuration error


have_command () {
    command -v "$1" >/dev/null 2>/dev/null
}

if have_command tput; then
    TXT_NORMAL=$(tput sgr0)

    TXT_BOLD=$(tput bold)
    TXT_DIM=$(tput dim)
    TXT_STANDOUT=$(tput smso)

    TXT_BLACK=$(tput setaf 0)
    TXT_BLUE=$(tput setaf 4)
    TXT_CYAN=$(tput setaf 6)
    TXT_GREEN=$(tput setaf 2)
    TXT_MAGENTA=$(tput setaf 5)
    TXT_RED=$(tput setaf 1)
    TXT_WHITE=$(tput setaf 7)
    TXT_YELLOW=$(tput setaf 3)
    TXT_NOCOLOR=$(tput op)
else
    TXT_NORMAL=''

    TXT_BOLD=''
    TXT_DIM=''
    TXT_STANDOUT=''

    TXT_BLACK=''
    TXT_BLUE=''
    TXT_CYAN=''
    TXT_GREEN=''
    TXT_MAGENTA=''
    TXT_RED=''
    TXT_WHITE=''
    TXT_YELLOW=''
    TXT_NOCOLOR=''
fi

die () {
  rc="$1"
  shift
  (
      echo -n "${TXT_BOLD}$me: ${TXT_RED}ERROR:${TXT_NOCOLOR} ";
      if [ $# -gt 0 ]; then echo "$@"; else cat; fi
      echo -n "${TXT_NORMAL}"
  ) 1>&2
  exit $rc
}

warn () {
    (
        echo -n "$me: ${TXT_YELLOW}WARNING:${TXT_NOCOLOR} ";
        if [ $# -gt 0 ]; then echo "$@"; else cat; fi
    ) 1>&2
}

require_command () {
  if ! have_command "$1"; then
    die 1 "Could not find required command '$1' in system PATH. Aborting."
  fi
}


## parse command-line

short_opts='b:hN:'
long_opts='branches:,help,replicates:'

# test which `getopt` version is available:
# - GNU `getopt` will generate no output and exit with status 4
# - POSIX `getopt` will output `--` and exit with status 0
getopt -T > /dev/null
rc=$?
if [ "$rc" -eq 4 ]; then
    # GNU getopt
    args=$(getopt --name "$me" --shell sh -l "$long_opts" -o "$short_opts" -- "$@")
    if [ $? -ne 0 ]; then
        die 1 "Type '$me --help' to get usage information."
    fi
    # use 'eval' to remove getopt quoting
    eval set -- $args
else
    # old-style getopt, use compatibility syntax
    args=$(getopt "$short_opts" "$@")
    if [ $? -ne 0 ]; then
        die 1 "Type '$me --help' to get usage information."
    fi
    set -- $args
fi

while [ $# -gt 0 ]; do
    case "$1" in
        -b|--branches)
            branches="$(echo $2 | tr , ' ')"
            shift
            ;;
        -h|--help)
            usage;
            exit 0
            ;;
        -N|--replicates)
            N="$2"
            shift
            ;;
        --)
            shift;
            break
            ;;
    esac
    shift
done


N="${1:-$N}"
shift


## main

require_command git
require_command python
require_command sudo
require_command timeout


restart () {
    sudo service uwsgi stop
    sleep 5
    sudo service uwsgi start
    sleep 5
}

run_tests () {
    local N="$1"
    local branch="$2"
    local prep="$3"
    shift 3

    # checkout the right code
    for repo in tmserver tmlibrary jtlibrary; do
        pushd "$HOME/$repo"
        git checkout "$branch"
        popd
    done

    # always restart server after checking code out
    restart

    local test_dir="${branch}-${prep}"
    mkdir -pv "$test_dir"
    pushd "$test_dir"

    for n in $(seq 1 $N); do
        if [ "$prep" = 'restart' ]; then
            restart
        fi

        # run actual tests
        timeout --signal=TERM --kill-after=15m 2h \
            python $HOME/test_datasets.py --force -vv \
                $HOME/data/v0.3.3 $HOME/TESTS.yml "$@" \
                    2>&1 | tee "test_datasets.${n}.log"
    done

    popd
}


set -x

for branch in $branches; do
    for prep in restart norestart; do
        run_tests $N $branch $prep "$@"
    done
done

# otherwise `allure` (as installed by the Ubuntu package) won't run
unset JAVA_HOME

reports_out="$HOME/www/$(date +'%Y-%m-%d@%H.%M')/"
allure_out="$reports_out/summary"
junit2html_out="$reports_out/details"
for srcdir in *; do
    destdir=$(basename "$srcdir")

    if have_command allure; then
        mkdir -pv "$allure_out/$destdir" \
            && allure generate -c -o "$allure_out/$destdir" "$srcdir"
    else
        warn "No 'allure' command found, not generating test summary HTML report."
    fi

    if have_command junit2html; then
        mkdir -pv "$junit2html_out/$destdir" \
            && junit2html --report-matrix="$junit2html_out/$destdir/index.html" "$srcdir"/*.xml
    else
        warn "No 'junit2html' command found, not generating test details HTML report."
    fi
done
