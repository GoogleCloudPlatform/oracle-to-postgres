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

export STREAM_NAME?=oracle-to-postgres
export GCS_BUCKET?=gs://${PROJECT_ID}
export PUBSUB_TOPIC?=${STREAM_NAME}
export PUBSUB_SUBSCRIPTION?=${PUBSUB_TOPIC}-subscription

export CLOUD_SQL?=<Cloud SQL>
export DATABASE_USER?=postgres
export DATABASE_PASSWORD?=postgres

export ORACLE_HOST?=<ORACLE_HOST>
export ORACLE_PORT?=1521
export ORACLE_USER?=system
export ORACLE_PASSWORD?=oracle
export ORACLE_DATABASE?=XE

export ORACLE_DSN:=dbi:Oracle:host=${ORACLE_HOST};sid=${ORACLE_DATABASE};port=${ORACLE_PORT}

# The PrivateConnection, in the format:
# projects/${PROJECT_ID}/locations/${REGION}/privateConnections/<PRIVATE_CONNECTION>
export PRIVATE_CONNECTION_NAME?=""

# Desired Oracle Schemas and object types to replicate
# For schemas, leave blank for all.
export ORACLE_SCHEMAS?=
export ORACLE_TYPES?=TABLE VIEW

# Oracle host for DataStream incase this is different from local
export ORACLE_DATASTREAM_HOST?=${ORACLE_HOST}
export ORACLE_DATASTREAM_PORT?=1521

export DATAFLOW_JOB_PREFIX?=oracle-to-postgres
export TEMPLATE_IMAGE_SPEC?=gs://teleport-dataflow-staging/images/datastream-to-postgres-image-spec.json
export DATASTREAM_ROOT_PATH?=/ora2pg/${STREAM_NAME}/
export GCS_STREAM_PATH?=${GCS_BUCKET}${DATASTREAM_ROOT_PATH}

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
	docker run --rm datastream \
		--action list \
		--project-number ${PROJECT_NUMBER} \
		--stream-prefix ${STREAM_NAME} \
		--source-prefix "oracle-${STREAM_NAME}" \
		--gcs-prefix "gcs-${STREAM_NAME}" \
		--gcs-bucket ${GCS_BUCKET} \
		--gcs-root-path "/ora2pg/" \
		--private-connection ${PRIVATE_CONNECTION_NAME} \
		--oracle-host ${ORACLE_DATASTREAM_HOST} \
		--oracle-port ${ORACLE_DATASTREAM_PORT} \
		--oracle-user ${ORACLE_USER} \
		--oracle-password ${ORACLE_PASSWORD} \
		--oracle-database ${ORACLE_DATABASE} \
		--schema-names "${ORACLE_SCHEMAS}"
	gcloud sql instances list --project=${PROJECT_ID} | grep "${CLOUD_SQL}"
	./dataflow.sh

build: variables
	echo "Build Oracle to Postgres Docker Images: ${PROJECT_ID}"
	docker pull gcr.io/google.com/cloudsdktool/cloud-sdk:latest
	./data_validation.sh build
	docker build datastream_utils/ -t datastream
	./ora2pg.sh build

deploy-resources: variables
	echo "Deploy Oracle to Postgres Resources: ${PROJECT_ID}"
	./deploy_resources.sh
	./data_validation.sh deploy

ora2pg: variables
	./ora2pg.sh run

deploy-ora2pg: variables
	./ora2pg.sh deploy

deploy-datastream: variables
	echo "Deploy DataStream from Oracle to GCS: ${PROJECT_ID}"
	docker run --rm datastream \
		--action create \
		--project-number ${PROJECT_NUMBER} \
		--stream-prefix ${STREAM_NAME} \
		--source-prefix "oracle-${STREAM_NAME}" \
		--gcs-prefix "gcs-${STREAM_NAME}" \
		--gcs-bucket ${GCS_BUCKET} \
		--gcs-root-path "${DATASTREAM_ROOT_PATH}" \
		--private-connection ${PRIVATE_CONNECTION_NAME} \
		--oracle-host ${ORACLE_DATASTREAM_HOST} \
		--oracle-port ${ORACLE_DATASTREAM_PORT} \
		--oracle-user ${ORACLE_USER} \
		--oracle-password ${ORACLE_PASSWORD} \
		--oracle-database ${ORACLE_DATABASE} \
		--schema-names "${ORACLE_SCHEMAS}"

deploy-dataflow: variables
	echo "Deploy Dataflow from GCS to Postgres: ${PROJECT_ID}"
	./dataflow.sh create

validate: variables
	./data_validation.sh run

destroy-datastream: variables
	@echo "Tearing Down DataStream: ${PROJECT_ID}"
	docker run --rm datastream \
		--action tear-down \
		--project-number ${PROJECT_NUMBER} \
		--stream-prefix ${STREAM_NAME} \
		--source-prefix "oracle-${STREAM_NAME}" \
		--gcs-prefix "gcs-${STREAM_NAME}" \
		--gcs-bucket ${GCS_BUCKET} \
		--gcs-root-path "${DATASTREAM_ROOT_PATH}" \
		--private-connection ${PRIVATE_CONNECTION_NAME} \
		--oracle-host ${ORACLE_DATASTREAM_HOST} \
		--oracle-port ${ORACLE_DATASTREAM_PORT} \
		--oracle-user ${ORACLE_USER} \
		--oracle-password ${ORACLE_PASSWORD} \
		--oracle-database ${ORACLE_DATABASE} \
		--schema-names "${ORACLE_SCHEMAS}"

destroy-dataflow: variables
	@echo "Tearing Down Dataflow: ${PROJECT_ID}"
	./dataflow.sh destroy

destroy: variables
	@echo "Tearing Down DataStream to Postgres: ${PROJECT_ID}"
	docker run --rm datastream \
		--action tear-down \
		--project-number ${PROJECT_NUMBER} \
		--stream-prefix ${STREAM_NAME} \
		--source-prefix "oracle-${STREAM_NAME}" \
		--gcs-prefix "gcs-${STREAM_NAME}" \
		--gcs-bucket ${GCS_BUCKET} \
		--gcs-root-path "${DATASTREAM_ROOT_PATH}" \
		--private-connection ${PRIVATE_CONNECTION_NAME} \
		--oracle-host ${ORACLE_DATASTREAM_HOST} \
		--oracle-port ${ORACLE_DATASTREAM_PORT} \
		--oracle-user ${ORACLE_USER} \
		--oracle-password ${ORACLE_PASSWORD} \
		--oracle-database ${ORACLE_DATABASE} \
		--schema-names "${ORACLE_SCHEMAS}"
	gsutil -m rm ${GCS_STREAM_PATH}**
	./dataflow.sh destroy
	./data_validation.sh destroy
