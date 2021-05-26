# Oracle to PostgreSQL Toolkit

## Migration Setup
To use the Oracle to PostgreSQL toolkit, clone the directory and edit the Makefile to add your configurations.

`git clone https://github.com/GoogleCloudPlatform/oracle-to-postgres.git`

### Requirements

- An Oracle Database which is supported by Datastream
    - You are able to enable LogMiner
    - Your [Oracle Database is supported by Datastream](https://cloud.google.com/datastream/docs/sources?hl=pl#oracleknownlimitations)
- A PostgreSQL database, by default a Cloud SQL for PostgreSQL instance is expected.
- A bastion VM with access to connect to both Oracle and PostgreSQL
    - Connectivity to Datastream can be direct or utilize the VM as a bastion with forward tunnels
    - Clone this repository into your environment
    - Add your Oracle rpm files to the `oracle/` directory
    - Install Docker & gcloud on the VM
- During setup the tool will enable required APIs and deploy required resources if they do not already exist
    - Dataflow, Cloud Storage, Pub/Sub, Datastream, Compute, SQLAdmin, and Networking (more details can be found in `deploy_resources.sh`)
    - The Cloud Storage bucket and Pub/Sub topic and subscription will be created if they do not exist.  You should ensure your VM user has proper access to create the following:
        - Create Cloud Storage buckets
        - Create a Pub/Sub topic and subscription
        - Enable Cloud Storage Pub/Sub notifications on your bucket (must be a bucket owner)
    - Cloud SQL will be deployed if it does not already exist

Nearly all parameters you will require are controlled via the Makefile.  
There are a small number of configurations you may need to edit for Ora2Pg, Dataflow, and Datastream which  are networking dependent.  If you are using a private networking setup, please see the added instructions at the end of each stage.

## Migration Stages
The stages of a migration are intended to be iterative as you will sometimes need to restart replication to account for new configurations.  Due to this iterative nature, we suggest using a QA or Dev environment first, before moving into production.

### Building Resources (make build)
After you have created the required resources and added your configurations at the top of your `Makefile`, you will be ready to build the Docker images used during replication.
The Docker images which are built are as follows
- [Ora2Pg](http://ora2pg.darold.net/): A docker image which is used to run Ora2Pg.
- GCloud: For more recent APIs we use a docker gcloud to ensure the latest version of gcloud
- Datastream management: This image is used to list, deploy, and delete Datastream resources.
- [Data validation](https://github.com/GoogleCloudPlatform/professional-services-data-validator): An image built from Google's open source Data Validation tooling.

### Deploying Resources (make deploy-resources)

This stage will ensure all the expected resources exist, and if not will create them.  The logic is designed to be run several times if needed, and will not recreate existing resources.
The final step in the resource deployment is to test the connection details from the current VM to both Oracle and PostgreSQL.  These tests are performed by the data validation docker image, which will also store connection details for future use.

### Executing Ora2Pg (make ora2pg)

The next step in a migration is to run the Ora2Pg schema conversion tooling.  The raw Ora2Pg files will all be stored in `ora2pg/data/` along with a single file with the accumulated conversions for the current run (`ora2pg/data/output.sql`).
The table definitions created by Ora2Pg by default are often all you will require. However, if customization is required this can be done by editing `ora2pg/config/ora2pg.conf` and re-running the `make ora2pg` step. You should be sure to manually review the `output.sql` file to confirm your expected conversion has been run.

Although they will not be applied directly by default, any of the Ora2Pg object types can be converted, you will find the raw SQL files in `ora2pg/data/` and you can manually address issues and upload non-data objects to PostgreSQL as needed (ie. PL/SQL).

### Applying Ora2Pg (make deploy-ora2pg)

When you are confident in the Ora2Pg conversion, then you are ready to apply the schema in your PostgreSQL database.  Running the apply step will load your schema file into Cloud Storage and import it into your Cloud SQL for PostgreSQL database.
If you need to customize using a non-CloudSQL database then simply import the `ora2pg/data/output.sql` file directly using the PostgreSQL CLI.

#### Re-running make deploy-ora2pg

Once a schema is applied, future runs of the same schema will fail. If you need to re-apply the schema you should first run the following SQL DROP command against each PostgreSQL schema in question:
`DROP SCHEMA IF EXISTS <schema_name> CASCADE;`

### Deploying Datastream (make deploy-datastream)

When your schema has been applied, you are ready to begin data replication.  The datastream deployment stage will create a set of connection profiles and a stream using your supplied configuration.
If you wish to perform this stage manually in the UI, please feel free to follow the steps outlined in the [Datastream Quickstart and Documentation](https://cloud.google.com/datastream/docs/quickstart).

#### Private Connectivity

To use the [PrivateConnection feature in Datastream](https://cloud.google.com/datastream/docs/create-a-private-connectivity-configuration), begin by creating a PrivateConnection in the UI.  You will then be able to add this reference in your Makefile to be used in the Datastream creation.

### Deploying Dataflow (make deploy-dataflow)

Deploying Dataflow will create a streaming Dataflow job from the Datastream to PostgreSQL template.  This job will replicate data from Cloud Storage into PostgreSQL as soon as it is deployed.  The specific setting for Dataflow can be seen in `dataflow.sh`, though generally the defaults will be able to replicate into PostgreSQL as quickly as possible (scaling up PostgreSQL resources will often scale up data replication if this is needed).

#### Private Connectivity

To add private connectivity to Dataflow, please add the private networking configurations to `dataflow.sh`.  These configurations will include changing the dataflow run command:
- Adding `--disable-public-ips`
- Specifying you desired `--network`

#### Redeploying Data Replication

To redeploy data replication you should first cancel the old Dataflow job. When you are ready to re-deploy, a rewrite to any Cloud Storage file will cause it to be consumed (and avoid the need to restart Datastream replication). Running the following rewrite command will read all files again once Dataflow is redeployed.
`gsutil -m rewrite -r -k gs://bucket/path/to/data/`

### Data Validation (make validate)

Once your data appears to be replicating (or before) you can run data validation to check on the row count comparisons between each source and target table.
Running validation will allow you to understand when you replication is up to date and during the cutover allow you to validate all data matches before starting a cutover.

For more details on the options around Data Validation, please see the open source [Data Validation Tool documentation](https://github.com/GoogleCloudPlatform/professional-services-data-validator).
