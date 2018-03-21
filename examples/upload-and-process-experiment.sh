#! /bin/sh
#
me="$(basename $0)"


## defaults

host='localhost'
port=80
username='devuser'
password='123456'
wait='n'
analysis='n'

## usage help

usage () {
cat <<EOF
Usage: $me [options] DATADIR [NAME]

Upload all files in directory DATADIR as experiment NAME and start processing
the workflow. If NAME is not explicitly provided, the name of directory DATADIR
is used as the experiment name.

The script makes a few assumptions on how the files are laid out into DATADIR:

* that DATADIR contains a file 'workflow_description.yaml' which defines the
  TissueMAPS workflow to run;

* that DATADIR contains a subdirectory 'jterator' which in turn contains
  a file 'pipeline.yaml' and a subdirectory 'handles' with the descriptions
  of the jterator pipeline and each jterator module, respectively.

* that DATADIR contains a subdirectory 'plates/' which in turn contains
  subdirectories, each of which contains files for a single plate. The
  subdirectory name will be used as the plate name in TissueMAPS.

* that each plate subdirectory contains an 'acquisitions/' directory, which in
  turn contains subdirectories, one for each acquisition. The subdirectory name
  will be used as the acquisition name in TissueMAPS.

Options:

  --host, -H NAME  TM host to connect to (default: ${host})
  --port, -P PORT  TCP port to contact the TM REST API (default: ${port})
  --user, -u NAME  TM username to authenticate as (default: ${username})
  --pass, -p PASS  Password to use for authentication (default: ${password})
  --analysis       Upload a jterator image analysis pipeline and submit
  --wait           Check workflow status after submitting

  --help, -h  Print this help text.

EOF
}


## helper functions

EX_USAGE=1
EX_DATAERR=65
EX_NOINPUT=66


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

have_command () {
  command -v "$1" >/dev/null 2>/dev/null
}

require_command () {
  if ! have_command "$1"; then
    die $EX_USAGE "Could not find required command '$1' in system PATH. Aborting."
  fi
}

# color text output
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


## parse command-line

short_opts='H:hP:p:u:w'
long_opts='help,host:,pass:,port:,user:,wait'

# test which `getopt` version is available:
# - GNU `getopt` will generate no output and exit with status 4
# - POSIX `getopt` will output `--` and exit with status 0
getopt -T > /dev/null
rc=$?
if [ "$rc" -eq 4 ]; then
    # GNU getopt
    args=$(getopt --name "$me" --shell sh -l "$long_opts" -o "$short_opts" -- "$@")
    if [ $? -ne 0 ]; then
        die $EX_USAGE "Type '$me --help' to get usage information."
    fi
    # use 'eval' to remove getopt quoting
    eval set -- $args
else
    # old-style getopt, use compatibility syntax
    args=$(getopt "$short_opts" "$@")
    if [ $? -ne 0 ]; then
        die $EX_USAGE "Type '$me --help' to get usage information."
    fi
    set -- $args
fi

while [ $# -gt 0 ]; do
    case "$1" in
        --host|-H) shift; host="$1" ;;
        --pass|-p) shift; password="$1" ;;
        --port|-P) shift; port="$1" ;;
        --user|-u) shift; username="$1" ;;
        --wait|-w)
            if have_command watch; then
                wait=='y'
            else
                warn "Option '--wait' requires the 'watch' command, which is not available on this system. Ignoring it."
            fi
            ;;
        --analysis|-a) analysis='y' ;;
        --help|-h) usage; exit 0 ;;
        --) shift; break ;;
    esac
    shift
done

datadir="$1"
if [ -z "$datadir" ]; then
    die $EX_USAGE "Missing required argument DATADIR.  Type '$me --help' to get usage help."
fi
if ! [ -d "$datadir" ]; then
    die $EX_DATAERR "Path '$datadir' is not a directory."
fi
if ! [ -d "${datadir}"/plates ]; then
    die $EX_NOINPUT "Cannot enumerate plates: no directory `plates/` inside '${datadir}'."
fi
if ! [ -r "${datadir}/workflow_description.yaml" ]; then
    die $EX_NOINPUT "Missing workflow description file in directory '$datadir'"
fi

if [ "$analysis" = 'y' ]; then
  if ! [ -d "${datadir}/jterator" ]; then
      die $EX_NOINPUT "Missing jterator project directory in directory '$datadir'"
  fi
  if ! [ -r "${datadir}/jterator/pipeline.yaml" ]; then
      die $EX_NOINPUT "Missing jterator pipeline description file in directory '$datadir/jterator'"
  fi
  if ! [ -d "${datadir}/jterator/handles" ]; then
      die $EX_NOINPUT "Missing jterator handles directory in directory '$datadir/jterator'"
  fi
fi

name="$2"
if [ -z "$name" ]; then
    name=$(basename "$datadir")
fi


## main

require_command tm_client
require_command watch

# shortcut
tm_client () {
    echo "== Running: ${TXT_BOLD}tm_client -H '${host}' -P '${port}' -u '${username}' -p '${password}' $@ ${TXT_NORMAL}..."
    command \
        time --format="${TXT_DIM}... Summary: exitcode %x,  %E elapsed (%es = %Us user + %Ss system), max %MkB memory${TXT_NORMAL}" \
        tm_client -H "${host}" -P "${port}" -u "${username}" -p "${password}" "$@";
}

# Create a new experiment and upload image files:

tm_client experiment create -n "${name}"

for plate_dir in "${datadir}"/plates/*; do
    if ! [ -d "$plate_dir" ]; then
        warn "Non-directory entry '$plate_dir' -- skipping"
        continue
    fi
    plate_name=$(basename "$plate_dir")
    tm_client plate -e "${name}" create -n "${plate_name}"
    if ! [ -d "${plate_dir}"/acquisitions ]; then
        warn "Cannot enumerate acquisitions in plate '$plate_name': no directory `acquisitions/` inside '${plate_dir}'. Skipping."
        continue
    fi
    for acquisition_dir in "${plate_dir}"/acquisitions/*; do
        if ! [ -d "$acquisition_dir" ]; then
            warn "Non-directory entry '$acquisition_dir' -- skipping"
            continue
        fi
        acquisition_name=$(basename "$acquisition_dir")
        tm_client acquisition -e "${name}" create -p "$plate_name" -n "$acquisition_name"
        tm_client microscope-file -e "${name}" upload -p "$plate_name" -a "$acquisition_name" "$acquisition_dir"
    done
done

# Upload workflow description:

tm_client workflow -e "${name}" upload --file "${datadir}/workflow_description.yaml"

# Upload jterator project description:

if [ "$analysis" = 'y' ]; then
  tm_client jtproject -e "${name}" upload "${datadir}/jterator"
fi

# Submit workflow:

tm_client workflow -e "${name}" submit

# Check workflow:

if [ "$wait" = 'y' ]; then
    exec watch -d -n 60 "tm_client workflow -e '${name}' status"
fi
