#!/bin/bash
set -e

if [ "$1" = 'pg_ctlcontrol' ]; then

    exec gosu pg_ctlcontrol "$@"
fi

exec "$@"

