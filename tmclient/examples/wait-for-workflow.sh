#! /bin/sh
#
me="$(basename $0)"


## defaults

host='localhost'
port=80
username="$USER"
password='123456'

background='n'
email=''
poll=300
quiet='n'

## usage help

usage () {
cat <<EOF
Usage: $me [options] NAME

Monitor workflow processing of experiment NAME and exit when done.

Optionally, send a notification email (requires the 'mutt' program). Note that
this email notification feature requires that environment variables
'SMTP_SERVER', and 'EMAIL' are set to the appropriate values (which are
domain-specific; you cannot expect to be able to send email from a random host
on the internet these days).

Main options:

  --background, -b  Detach from terminal and continue running in the background
                    (implies '--quiet' and is only useful together with '--email').
  --email, -e ADDR  Send email to ADDR when done.
  --poll, -w NUM    Poll status every NUM seconds (default: ${poll})
  --quiet, -q       No screen output; exit when workflow is done.

Authentication options:

  --host, -H NAME  TM host to connect to (default: ${host})
  --port, -P PORT  TCP port to contact the TM REST API (default: ${port})
  --user, -u NAME  TM username to authenticate as (default: ${username})
  --pass, -p PASS  Password to use for authentication (default: ${password})

Other options:

  --help, -h  Print this help text.

EOF
}


## helper functions

# see /usr/include/sysexit.h
EX_USAGE=1
EX_DATAERR=65
EX_NOINPUT=66
EX_UNAVAILABLE=69
EX_OSERR=71

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
        echo -n "${me}:${TXT_BOLD} ${TXT_RED}ERROR:${TXT_NOCOLOR} ";
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
    (echo -n "$me: WARNING: ";
     if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
}

require_command () {
  if ! have_command "$1"; then
    die $EX_UNAVAILABLE "Could not find required command '$1' in system PATH. Aborting."
  fi
}


## parse command-line

short_opts='be:H:hP:p:qu:w:'
long_opts='background,email:,help,host:,pass:,poll:,port:,quiet,user:'

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
        --background|-b) background='y' ;;
        --email|-e) shift; email="$1" ;;
        --help|-h) usage; exit 0 ;;
        --host|-H) shift; host="$1" ;;
        --pass|-p) shift; password="$1" ;;
        --poll|-w) shift; poll="$1" ;;
        --port|-P) shift; port="$1" ;;
        --quiet|-q) quiet='y' ;;
        --user|-u) shift; username="$1" ;;
        --) shift; break ;;
    esac
    shift
done

name="$1"
if [ -z "$name" ]; then
    die $EX_USAGE "Missing required argument NAME.  Type '$me --help' to get usage help."
fi


## main

require_command tm_client
require_command mktemp
require_command nohup
require_command tput

if [ -n "$email" ]; then
   require_command mutt

   if [ -z "$SMTP_SERVER" ] || [ -z "$EMAIL" ]; then
       die $EX_USAGE "Use of the '--email' option requires setting the SMTP_SERVER and EMAIL environment variables."
   fi

   mutt () {
       command mutt -x -n -e "set ssl_starttls=no; set smtp_url='smtp://${SMTP_SERVER}'; set from='${EMAIL}';" "$@";
   }
fi


# auth info is not going to change, so bake it in and forget ...
tm_client () {
    command tm_client -H "${host}" -P "${port}" -u "${username}" -p "${password}" "$@";
}

# check that experiment exists
if ! (tm_client workflow -e "${name}" status \
             | grep -q "| ${name}[[:space:]]*| Workflow "); then
    die $EX_NOINPUT "No experiment found with name '${name}' in TissueMAPS workflow status output."
fi

# background self (re-exec with additional -q flag)
if [ "${background}" = 'y' ]; then
    if [ -n "${email}" ]; then
        email_opt="--email '${email}'"
    else
        email_opt=''
    fi
    eval exec nohup "$0" --quiet $email_opt --poll "'$poll'" \
         --host "'$host'" --port "'$port'" --pass "'$password'" --user "'$username'" &
fi

# temporary output file
tmp=$(mktemp -t "${me}.XXXXXX") \
   || die $EX_OSERR "Cannot create temporary file."
trap "rm -f '$tmp'" EXIT INT ABRT TERM

if [ "${quiet}" = 'y' ]; then
    print_progress_report () {
        true;
    }
else
    print_progress_report () {
        local name="$1"
        local state="$2"
        local done="$3"
        local exitcode="$4"

        if [ "${state}" = 'TERMINATED' ]; then
            if [ "${exitcode}" -eq 0 ]; then
                state="${TXT_BOLD}${TXT_GREEN}SUCCESS${TXT_NORMAL}"
            else
                state="${TXT_BOLD}${TXT_RED}FAILED${TXT_NORMAL}"
            fi
        fi
        echo "${me} | ${TXT_DIM}$(date)${TXT_NORMAL} | workflow ${name}: ${state} (${done}%)"
    }
fi

if [ -z "$email" ]; then
    send_email_notification () {
        true;
    }
else
    send_email_notification () {
        local email="$1"
        local name="$2"
        local state="$3"
        local done="$4"
        local exitcode="$5"

        if [ "${exitcode}" -eq 0 ]; then
            outcome="completed successfully"
        else
            outcome="FAILED"
        fi

        mutt -s "TM workflow ${name} ${outcome}" "$email" <<EOF
TissueMAPS workflow for experiment '${name}', running on host ${host},
has ${outcome}.

To find out more, please run::

    tm_client -H "${host}" -P "${port}" -u "${username}" -p "***OMITTED***" workflow -e "$name" status

Yours sincerely,
${me}
EOF
    }

fi

while true; do
    tm_client workflow -e "${name}" status 1>"$tmp" 2>&1

    # check status; example `tm_client` output:
    #
    # +--------------+---------------------+-------------------------+------------+----------+----------+-----------------+---------------------+-------------+
    # | ID           | Name                | Type                    | State      | Done (%) | ExitCode | Time (HH:MM:SS) | CPU Time (HH:MM:SS) | Memory (MB) |
    # +--------------+---------------------+-------------------------+------------+----------+----------+-----------------+---------------------+-------------+
    # | dG1hcHM1MjQ= | four                | Workflow                | TERMINATED |   100.00 |    0     |  0:10:52.540000 |    0:08:19.270000   |       31544 |
    #
    grep "| ${name}[[:space:]]*| Workflow " "${tmp}" | {
        IFS='| ' read _ _ _ _ state done exitcode _;

        print_progress_report "$name" "$state" "$done" "$exitcode"

        if [ "$state" = 'TERMINATED' ]; then
            send_email_notification "$email" "$name" "$state" "$done" "$exitcode"
            return $exitcode
        fi

        return 125
    }
    rc=$?

    if [ $rc -ne 125 ]; then
        exit $rc
    fi

    sleep "$poll"
done
