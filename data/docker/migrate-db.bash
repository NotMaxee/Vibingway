#!/bin/bash

# Define the path to migration files as the key and the path to the
# file that indicates the migration has been ran as the value
#!/bin/bash

# Define the path to migration files as the key and the path to the
# file that indicates the migration has been ran as the value
declare -A migrations
migrations["/data/db/1-initdb.sql"]="/migration-data/complete/1-initdb.sql"

# Run migrations
for migration in "${!migrations[@]}"; do
    # If the migration has not been ran, run it
    if [ ! -f "${migrations[$migration]}" ]; then
        echo "Running migration at $migration"
        psql $POSTGRES_CONNECTION_STRING -f $migration
        
        # If the migration failed, exit
        if [ $? -ne 0 ]; then
            echo "Migration failed"
            exit 1
        fi

        # Mark the migration as complete
        mkdir -p $(dirname "${migrations[$migration]}")
        echo "Marking migration as complete at ${migrations[$migration]}"
        touch "${migrations[$migration]}"
    else
        echo "Migration '${migrations[$migration]}' has already been ran"
    fi
done

# If all migrations were ran, exit
echo "All migrations complete"