#!/bin/bash
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

if [ "${DATABASE_HOST}" == "" ]
then
    export DATABASE_HOST=$(gcloud sql instances list --project=${PROJECT_ID} | grep "${CLOUD_SQL}" | awk '{print $6;}')
fi

if [ "$1" == "build" ]
then
    docker build . -f DataValidationDockerfile -t data-validation
elif [ "$1" == "deploy" ]
then
    docker run -v ${PWD}/data_validation/.config/:/root/.config --rm ${DOCKER_DVT} \
        connections add -c oracle Raw --json "{\"host\":\"${ORACLE_HOST}\",\"user\":\"${ORACLE_USER}\",\"password\":\"${ORACLE_PASSWORD}\",\"source_type\":\"Oracle\",\"database\":\"${ORACLE_DATABASE}\"}"

    docker run -v ${PWD}/data_validation/.config/:/root/.config --rm ${DOCKER_DVT} \
        connections add -c postgres Raw --json "{\"host\":\"${DATABASE_HOST}\",\"user\":\"${DATABASE_USER}\",\"password\":\"${DATABASE_PASSWORD}\",\"source_type\":\"Postgres\",\"database\":\"postgres\"}"
elif [ "$1" == "run" ]
then
    export TABLES_LIST=$(docker run -v ${PWD}/data_validation/.config/:/root/.config --rm ${DOCKER_DVT} find-tables --source-conn oracle --target-conn postgres)
    docker run -v ${PWD}/data_validation/.config/:/root/.config --rm ${DOCKER_DVT} \
        run --source-conn oracle --target-conn postgres --tables-list "${TABLES_LIST}" --type Column
elif [ "$1" == "destroy" ]
then
    docker rmi -f ${DOCKER_DVT}
    rm -rf data_validation/.config/
else
    docker run -v ${PWD}/data_validation/.config/:/root/.config --rm ${DOCKER_DVT} --help
fi
