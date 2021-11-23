# Copyright 2020 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


export PROJECT_ID?=<PROJECT_ID>
export PROJECT_NUMBER?=<PROJECT_NUMBER>
export REGION?=us-central1
export CLOUDSDK_CONFIG?=${HOME}/.config/gcloud/

export STREAM_NAME?=oracle-to-postgres
export GCS_BUCKET?=gs://${PROJECT_ID}
export PUBSUB_TOPIC?=${STREAM_NAME}
export PUBSUB_SUBSCRIPTION?=${PUBSUB_TOPIC}-subscription

export CLOUD_SQL?=<Cloud SQL>
export DATABASE_USER?=postgres
export DATABASE_PASSWORD?=postgres
export DATABASE_HOST?=

export ORACLE_HOST?=<ORACLE_HOST>
export ORACLE_PORT?=1521
export ORACLE_USER?=system
export ORACLE_PASSWORD?=oracle
export ORACLE_DATABASE?=XE

export ORACLE_DSN:=dbi:Oracle:host=${ORACLE_HOST};sid=${ORACLE_DATABASE};port=${ORACLE_PORT}

# The PrivateConnection, in the format:
# projects/${PROJECT_ID}/locations/${REGION}/privateConnections/<PRIVATE_CONNECTION>
export PRIVATE_CONNECTION_NAME?=
export ORACLE_CP_NAME?="oracle-${STREAM_NAME}"
export GCS_CP_NAME?="gcs-${STREAM_NAME}"

# Desired Oracle Schemas and object types to replicate
# For schemas, leave blank for all.
export ORACLE_SCHEMAS?=
export ORACLE_TYPES?=TABLE VIEW

# Oracle host for DataStream incase this is different from local
export ORACLE_DATASTREAM_HOST?=${ORACLE_HOST}
export ORACLE_DATASTREAM_PORT?=1521

export DATAFLOW_JOB_PREFIX?=oracle-to-postgres
export TEMPLATE_IMAGE_SPEC?=gs://dataflow-templates/2021-11-12-00_RC00/flex/Cloud_Datastream_to_SQL
export DATASTREAM_ROOT_PATH?=ora2pg/${STREAM_NAME}/
export GCS_STREAM_PATH?=${GCS_BUCKET}/${DATASTREAM_ROOT_PATH}

# Data Validation
# export PSO_DV_CONFIG_HOME?=${GCS_BUCKET}/dvt/

# Docker Image Tags
export DOCKER_GCLOUD?=gcr.io/google.com/cloudsdktool/cloud-sdk:latest
export DOCKER_DATASTREAM?=datastream
export DOCKER_DVT?=data-validation
export DOCKER_ORA2PG?=ora2pg

variables:
	@echo "Project ID: ${PROJECT_ID}"
	@echo "CloudSQL Output: ${CLOUD_SQL}"
	@echo "GCS Bucket: ${GCS_BUCKET}"
	@echo "GCS Datastream Path: ${GCS_STREAM_PATH}"

	@echo ""
	@echo "Build Docker Images Used in Ora2PG: make build"
	@echo "Deploy Required Resources: make deploy-resources"
	@echo "Run Ora2PG SQL Conversion Files: make ora2pg"
	@echo "Apply Ora2PG SQL to PSQL: make deploy-ora2pg"
	@echo "Deploy DataStream: make deploy-datastream"
	@echo "Deploy Dataflow: make deploy-dataflow"
	@echo "Validate Oracle vs Postgres: make validate"

list: variables
	@echo "List All Oracle to Postgres Objects: ${PROJECT_ID}"
	gcloud beta datastream streams list --location=${REGION} --project=${PROJECT_ID} --quiet
	gcloud sql instances list --project=${PROJECT_ID} | grep "${CLOUD_SQL}"
	./dataflow.sh

build: variables
	echo "Build Oracle to Postgres Docker Images: ${PROJECT_ID}"
	docker build datastream_utils/ -t ${DOCKER_DATASTREAM}
	docker build . -f DataValidationDockerfile -t ${DOCKER_DVT}
	docker build . -f Ora2PGDockerfile -t ${DOCKER_ORA2PG}

cloud-build: variables build
	echo "Push Ora2PG Docker Images to GCR: ${PROJECT_ID}"
	docker push ${DOCKER_DATASTREAM}
	docker push ${DOCKER_DVT}
	docker push ${DOCKER_ORA2PG}

deploy-resources: variables
	echo "Deploy Oracle to Postgres Resources: ${PROJECT_ID}"
	./deploy_resources.sh
	./data_validation.sh deploy

ora2pg: variables
	./ora2pg.sh run

ora2pg-drops: variables ora2pg
	sed -i '1s/^/DROP SCHEMA IF EXISTS hr CASCADE;\n/' ora2pg/data/output.sql

deploy-ora2pg: variables
	./ora2pg.sh deploy

deploy-datastream: variables
	echo "Deploy DataStream from Oracle to GCS: ${PROJECT_ID}"
	# Create Connection Profiles
	gcloud beta datastream connection-profiles create ${ORACLE_CP_NAME} --display-name ${ORACLE_CP_NAME} --type ORACLE --database-service=${ORACLE_DATABASE} --oracle-hostname=${ORACLE_DATASTREAM_HOST} --oracle-port=${ORACLE_DATASTREAM_PORT} --oracle-username=${ORACLE_USER} --oracle-password=${ORACLE_PASSWORD} --private-connection-name=${PRIVATE_CONNECTION_NAME} --location=${REGION} --project=${PROJECT_ID} --quiet || true
	gcloud beta datastream connection-profiles create ${GCS_CP_NAME} --display-name ${GCS_CP_NAME} --type GOOGLE-CLOUD-STORAGE --bucket-name "${PROJECT_ID}" --root-path "/${DATASTREAM_ROOT_PATH}" --location=${REGION} --project=${PROJECT_ID} --quiet || true

	# Create & Start Datastream Stream
	gcloud beta datastream streams create ${STREAM_NAME} --display-name ${STREAM_NAME} --backfill-all \
	--source-name="${ORACLE_CP_NAME}" --oracle-source-config=datastream_utils/source_config.json --oracle-excluded-objects=datastream_utils/source_excluded_objects.json \
	--destination-name="${GCS_CP_NAME}" --gcs-destination-config=datastream_utils/destination_config.json \
	--location=${REGION} --project=${PROJECT_ID} --quiet || true
	sleep 20
	gcloud beta datastream streams update ${STREAM_NAME} --state=RUNNING --update-mask=state --location=${REGION} --project=${PROJECT_ID} --quiet || true

deploy-dataflow: variables
	echo "Deploy Dataflow from GCS to Postgres: ${PROJECT_ID}"
	./dataflow.sh create

validate: variables
	./data_validation.sh run

destroy-datastream: variables
	@echo "Tearing Down DataStream: ${PROJECT_ID}"
	gcloud beta datastream streams delete ${STREAM_NAME} --location=${REGION} --project=${PROJECT_ID} --quiet
	gcloud beta datastream connection-profiles delete ${ORACLE_CP_NAME} --location=${REGION} --project=${PROJECT_ID} --quiet
	gcloud beta datastream connection-profiles delete ${GCS_CP_NAME} --location=${REGION} --project=${PROJECT_ID} --quiet

destroy-dataflow: variables
	@echo "Tearing Down Dataflow: ${PROJECT_ID}"
	./dataflow.sh destroy

destroy: variables destroy-dataflow destroy-datastream
	@echo "Tearing Down DataStream to Postgres: ${PROJECT_ID}"
	gsutil -m rm ${GCS_STREAM_PATH}**
