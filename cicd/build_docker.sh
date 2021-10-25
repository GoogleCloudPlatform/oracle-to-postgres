#!/bin/bash

export PROJECT_ID=dms-heterogeneous

cp -r ../oracle .
gcloud builds submit --project=${PROJECT_ID} --tag=gcr.io/${PROJECT_ID}/build-oracle-to-postgres

# Cleanup
rm -rf oracle/
