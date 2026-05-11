#!/bin/sh
set -eu

mkdir -p attachments cache files logs voice

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    retries="${DATABASE_WAIT_RETRIES:-30}"
    delay="${DATABASE_WAIT_SECONDS:-2}"

    while [ "$retries" -gt 0 ]; do
        if python -c "from db.session import create_db_engine; connection = create_db_engine().connect(); connection.close()"; then
            break
        fi

        retries=$((retries - 1))

        if [ "$retries" -eq 0 ]; then
            echo "Database is not available"
            exit 1
        fi

        echo "Waiting for database..."
        sleep "$delay"
    done

    alembic upgrade head
fi

exec "$@"
