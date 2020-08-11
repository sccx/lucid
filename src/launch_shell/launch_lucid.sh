#!/bin/bash

PATH=""

echo "RUNNING JOB"


/usr/local/spark/bin/spark-submit \
    --master spark://10.0.0.10:7077 \
    --jars /usr/local/spark/jars/org.postgresql_postgresql-42.2.14.jar \
    --py-files $HOME/twit_tracker/twitter_credentials.py $HOME/twit_tracker/lucid.py


