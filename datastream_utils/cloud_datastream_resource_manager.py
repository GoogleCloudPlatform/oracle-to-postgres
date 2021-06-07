"""Utilities to start and manage a CDC stream from Cloud Datastream."""

import logging
import time
from typing import List, Tuple
import uuid

try:
  from google3.google.cloud.datastream import datastream  # pylint: disable=g-import-not-at-top
except ModuleNotFoundError:
  import datastream  # pytype: disable=import-error  pylint: disable=g-import-not-at-top


DEFAULT_REGION = "us-central1"

DATASTREAM_URL = "https://datastream.googleapis.com/"

DATASTREAM_EXPORT_FILEFORMAT_AVRO = "avro"
DATASTREAM_EXPORT_FILEFORMAT_JSON = "json"

DEFAULT_DATASTREAM_EXPORT_FILEFORMAT = DATASTREAM_EXPORT_FILEFORMAT_AVRO

DEFAULT_GCS_ROOT_PATH = "/rootprefix/"
DEFAULT_STREAM_NAME = "datastream-test"
DEFAULT_SOURCE_CP_NAME = "oracle-cp"
DEFAULT_DEST_CP_NAME = "gcs-cp"


class CloudDatastreamResourceManager(object):
  """Resource manager to start a CDC stream from Cloud Datastream.

  This resource manager creates the set of resources to create a stream from
  Cloud Datastream, and starts the stream.

  On Teardown, all resources are deleted.
  """

  def __init__(
      self,
      project_number,
      gcs_bucket_name,
      region=None,
      client=None,
      authorized_http=None,
      stream_name=None,
      source_cp_name=None,
      target_cp_name=None,
      oracle_cp=None,
      mysql_cp=None,
      allowed_tables=None,
      gcs_root_path=None,
      add_uid_suffix=True,
      datastream_api_url=None,
      datastream_export_file_format=None,
      private_connection_name=None,
  ):
    """Initialize the CloudDatastreamResourceManager.

    Args:
      project_number: The GCP Project number identifying your project.
      gcs_bucket_name: The GCS bucket name without gs:// added.
      region: The GCP region where DataStream is deployed.
      client: The Datastream client to be used.
      authorized_http: An authorized http to be supplied
          to the Datastream client.
      stream_name: The name or prefix of the stream.
      source_cp_name: The name or prefix of the source CP.
      target_cp_name: The name or target of the source CP.
      oracle_cp: The connection profile configuration for an Oracle source.
      mysql_cp: The connection profile configuration for a MySQL source.
      allowed_tables: A List of allowed schema and table tuples.
      gcs_root_path: The GCS root directory for DataStream (ie. /rootpath/).
      add_uid_suffix: Whether or not to add a UID to all stream objects.
      datastream_api_url: The URL to use when calling DataStream.
      datastream_export_file_format: avro/json
      private_connection_name: The name of the PrivateConnection to
          use if required
          (eg. projects/<project-id>/locations/<loc>/
          privateConnections/<private-conn-name>).
    """
    self.project_number = project_number
    self.region = region or DEFAULT_REGION

    self._stream_name = stream_name or DEFAULT_STREAM_NAME
    self._source_cp_name = source_cp_name or DEFAULT_SOURCE_CP_NAME
    self._target_cp_name = target_cp_name or DEFAULT_DEST_CP_NAME
    self._suffix = str(uuid.uuid4())[:8] if add_uid_suffix else ""

    self.oracle_cp = oracle_cp
    self.mysql_cp = mysql_cp
    self.private_connection_name = private_connection_name
    self.allowed_tables = allowed_tables or []

    self.gcs_bucket_name = gcs_bucket_name.replace("gs://", "")
    self._gcs_root_path = gcs_root_path or DEFAULT_GCS_ROOT_PATH
    self.datastream_export_file_format = (
        datastream_export_file_format or DEFAULT_DATASTREAM_EXPORT_FILEFORMAT
        )
    if client:
      self.client = client
    else:
      logging.info("Creating DataStream Client with Authorized HTTP")
      api_url = datastream_api_url or DATASTREAM_URL
      self.client = datastream.DatastreamV1alpha1(
          url=api_url, http=authorized_http, get_credentials=True)

  @property
  def datastream_parent(self):
    return "projects/%s/locations/%s" % (self.project_number, self.region)

  @property
  def suffix(self):
    if self._suffix:
      return "-%s" % self._suffix
    return ""

  @property
  def path_suffix(self):
    if self._suffix:
      return "%s/" % self._suffix
    return ""

  @property
  def stream_name(self):
    return self._stream_name + self.suffix

  @property
  def full_stream_name(self):
    return self.datastream_parent + "/streams/" + self.stream_name

  @property
  def source_connection_name(self):
    return self._source_cp_name + self.suffix

  @property
  def full_source_connection_name(self):
    return (
        self.datastream_parent +
        "/connectionProfiles/" +
        self.source_connection_name
        )

  @property
  def dest_connection_name(self):
    return self._target_cp_name + self.suffix

  @property
  def full_dest_connection_name(self):
    return (
        self.datastream_parent +
        "/connectionProfiles/" +
        self.dest_connection_name
        )

  @property
  def gcs_root_path(self):
    return self._gcs_root_path + self.path_suffix

  @property
  def gcs_bucket(self):
    return "gs://%s" % self.gcs_bucket_name

  @property
  def gcs_location(self):
    return self.gcs_bucket + self.gcs_root_path

  def SetUp(self):
    """Create and start all resources for a CDC Datastream.

    In this order:
    - Create a source Database Connection Profile
    - Create a destintation GCS Connection Profile
    - Create a stream that reads from source into destination
    - Start the stream
    """
    logging.info("Setting up Source Connection Profile")
    # Create the Oracle Connection Profile
    self._CreateDatabaseConnectionProfile()

    logging.info("Setting up GCS Connection Profile")
    self._CreateGcsConnectionProfile(
        self.dest_connection_name,
        bucket_name=self.gcs_bucket_name,
        root_path=self.gcs_root_path)

    logging.info("Creating stream on Datastream")
    stream_op_result = self._CreateStream(self.stream_name,
                                          self.full_source_connection_name,
                                          self.full_dest_connection_name,
                                          self.datastream_export_file_format)

    if stream_op_result.error:
      raise ValueError(str(stream_op_result))

    logging.info("Starting CDC stream on Datastream")
    result = self._UpdateStreamState(
        self.full_stream_name, datastream.Stream.StateValueValuesEnum.RUNNING)

    if result.error:
      raise ValueError(str(result.error))

  def TearDown(self):
    """Stop and delete all resources started in SetUp.

    In this order:
    - Stop stream, then delete it
    - Delete destination GCS Connection Profile
    - Delete source Database Connection Profile
    """
    self._StopAndDeleteStream(self.full_stream_name)

    self._DeleteConnectionProfile(self.full_source_connection_name)
    self._DeleteConnectionProfile(self.full_dest_connection_name)

  def Describe(self):
    return "Manage a stream from Cloud Datastream."

  def ListStreams(self):
    streams = self._ListStreams()
    for stream in streams.streams:
      if not self._stream_name in stream.name:
        continue
      stream_log = "Stream Name: %s" % stream.name
      stream_cp_source_log = "\tSource CP: %s" % stream.sourceConfig.sourceConnectionProfileName
      stream_cp_dest_log = "\tDest CP: %s" % stream.destinationConfig.destinationConnectionProfileName

      logging.info(stream_log)
      logging.info(stream_cp_source_log)
      logging.info(stream_cp_dest_log)

  def _UpdateStreamState(self, stream_name, state):
    request = datastream.DatastreamProjectsLocationsStreamsPatchRequest(
        name=stream_name,
        stream=datastream.Stream(state=state),
        updateMask="state")

    response = self.client.projects_locations_streams.Patch(request)
    return self._WaitForCompletion(response)

  def _WaitForCompletion(self, response, timeout=120):
    # After requesting an operation, we need to wait for its completion
    start = time.time()
    while not response.done:
      time.sleep(5)
      response = self.client.projects_locations_operations.Get(
          datastream.DatastreamProjectsLocationsOperationsGetRequest(
              name=response.name))

      if time.time() - start > timeout:
        logging.warning("Timed out waiting for operation completion %s",
                        response.name)
        break

    return response

  def _DeleteConnectionProfile(self, cp_name):
    delete_req = (
        datastream.DatastreamProjectsLocationsConnectionProfilesDeleteRequest(
            name=cp_name))

    try:
      return self.client.projects_locations_connectionProfiles.Delete(
          delete_req)
    except datastream.HttpError:
      logging.exception("Unable to delete connection profile %r.",
                        cp_name)
      return None

  def _StopAndDeleteStream(self, stream_name):
    try:
      self._UpdateStreamState(stream_name,
                              datastream.Stream.StateValueValuesEnum.PAUSED)
    except datastream.HttpError:
      logging.exception("There was an issue stopping Datastream stream %r.",
                        stream_name)
      return None

    delete_request = datastream.DatastreamProjectsLocationsStreamsDeleteRequest(
        name=stream_name)

    return self.client.projects_locations_streams.Delete(delete_request)

  def _ListStreams(self):
    request = (
        datastream.DatastreamProjectsLocationsStreamsListRequest(
            parent=self.datastream_parent))
    return self.client.projects_locations_streams.List(request)

  def _ListConnectionProfiles(self):
    request = (
        datastream.DatastreamProjectsLocationsConnectionProfilesListRequest(
            parent=self.datastream_parent))
    return self.client.projects_locations_connectionProfiles.List(request)

  def _ListPrivateConnections(self):
    request = (
        datastream.DatastreamProjectsLocationsPrivateConnectionsListRequest(
            parent=self.datastream_parent))
    return self.client.projects_locations_privateConnections.List(request)

  def _CreateDatabaseConnectionProfile(self):
    if self.oracle_cp:
      return self._CreateOracleConnectionProfile(self.source_connection_name,
                                                 self.oracle_cp)
    elif self.mysql_cp:
      return self._CreateMysqlConnectionProfile(
          self.source_connection_name,
          self.getMysqlConnectionProfile())
    else:
      raise Exception("No Source Connection Profile Supplied")

  def getMysqlConnectionProfile(self):
    if not isinstance(self.mysql_cp, dict):
      self.mysql_cp = self.mysql_cp.getDatastreamCP()

    if not self.mysql_cp["sslConfig"]:
      self.mysql_cp["sslConfig"] = datastream.MysqlSslConfig()

    logging.info("Logging MySQL CP:")
    logging.info(self.mysql_cp)
    return self.mysql_cp

  def _CreateMysqlConnectionProfile(self, name, mysql_cp):
    logging.info(
        "Creating connection profile %r for MySQL database. Parent: %r", name,
        self.datastream_parent)
    logging.debug("Database properties: %r", mysql_cp)
    connection_profile = datastream.ConnectionProfile(
        displayName=name,
        mysqlProfile=datastream.MysqlProfile(**mysql_cp),
        noConnectivity=datastream.NoConnectivitySettings())
    request = (
        datastream.DatastreamProjectsLocationsConnectionProfilesCreateRequest(
            parent=self.datastream_parent,
            connectionProfileId=name,
            connectionProfile=connection_profile))
    response = self.client.projects_locations_connectionProfiles.Create(request)
    return self._WaitForCompletion(response)

  def _CreateOracleConnectionProfile(self, name, oracle_cp):
    logging.info(
        "Creating connection profile %r for Oracle database. Parent: %r", name,
        self.datastream_parent)
    logging.debug("Database properties: %r", oracle_cp)
    private_conn = self._get_private_connection()
    no_conn = datastream.NoConnectivitySettings() if not private_conn else None
    connection_profile = datastream.ConnectionProfile(
        displayName=name,
        oracleProfile=datastream.OracleProfile(**oracle_cp),
        noConnectivity=no_conn,
        privateConnectivity=private_conn)
    request = (
        datastream.DatastreamProjectsLocationsConnectionProfilesCreateRequest(
            parent=self.datastream_parent,
            connectionProfileId=name,
            connectionProfile=connection_profile))
    response = self.client.projects_locations_connectionProfiles.Create(request)
    return self._WaitForCompletion(response)

  def _CreateGcsConnectionProfile(self, name, bucket_name, root_path):
    connection_profile = datastream.ConnectionProfile(
        displayName=name,
        gcsProfile=datastream.GcsProfile(bucketName=bucket_name,
                                         rootPath=root_path),
        noConnectivity=datastream.NoConnectivitySettings())
    request = (
        datastream.DatastreamProjectsLocationsConnectionProfilesCreateRequest(
            parent=self.datastream_parent,
            connectionProfileId=name,
            connectionProfile=connection_profile,
        ))
    response = self.client.projects_locations_connectionProfiles.Create(request)
    return self._WaitForCompletion(response)

  def _get_source_config(self):
    if self.oracle_cp:
      return datastream.SourceConfig(
          sourceConnectionProfileName=self.full_source_connection_name,
          oracleSourceConfig=datastream.OracleSourceConfig(
              allowlist=self._get_oracle_rdbms(self.allowed_tables),
              rejectlist=datastream.OracleRdbms(),
          ),
      )
    elif self.mysql_cp:
      return datastream.SourceConfig(
          sourceConnectionProfileName=self.full_source_connection_name,
          mysqlSourceConfig=datastream.MysqlSourceConfig(
              allowlist=self._get_mysql_rdbms(self.allowed_tables),
              rejectlist=datastream.MysqlRdbms(),
          ),
      )

  def _get_private_connection(self):
    """Return PrivateConnection object if it is required in the CP."""
    if self.private_connection_name:
      return datastream.PrivateConnectivity(
          privateConnectionName=self.private_connection_name)

    return None

  def _get_oracle_rdbms(self, table_list: List[Tuple[str, str]]):
    """Return an Oracle Rdbms with the desired tables set.

    Args:
        table_list: A List of allowed schema and table tuples.
    Returns:
        An initialized OracleRdbms filtered against the supplied tables.
    """
    schema_tables = {}
    for table_obj in table_list:
      schema_name = table_obj[0]
      table_name = table_obj[1]
      if schema_name not in schema_tables:
        schema_tables[schema_name] = []

      if table_name:
        schema_tables[schema_name].append(
            datastream.OracleTable(tableName=table_name))

    oracle_schemas = [
        datastream.OracleSchema(schemaName=schema_name, oracleTables=tables)
        for schema_name, tables in schema_tables.items()]

    return datastream.OracleRdbms(oracleSchemas=oracle_schemas)

  def _get_mysql_rdbms(self, table_list: List[Tuple[str, str]]):
    """Return a Mysql Rdbms with the desired tables set.

    Args:
        table_list: A List of allowed schema and table tuples.
    Returns:
        An initialized MysqlRdbms filtered against the supplied tables.
    """
    db_tables = {}
    for table_obj in table_list:
      db_name = table_obj[0]
      table_name = table_obj[1]
      if db_name not in db_tables:
        db_tables[db_name] = []

      if table_name:
        db_tables[db_name].append(
            datastream.MysqlTable(tableName=table_name))

    mysql_dbs = [
        datastream.MysqlDatabase(databaseName=db_name, mysqlTables=tables)
        for db_name, tables in db_tables.items()]

    return datastream.MysqlRdbms(mysqlDatabases=mysql_dbs)

  def _getGcsDestinationConfig(self, export_file_format):
    if export_file_format == DATASTREAM_EXPORT_FILEFORMAT_JSON:
      return datastream.GcsDestinationConfig(
          jsonFileFormat=datastream.JsonFileFormat(
              compression=datastream.JsonFileFormat
              .CompressionValueValuesEnum.GZIP,
              schemaFileFormat=datastream.JsonFileFormat
              .SchemaFileFormatValueValuesEnum.NO_SCHEMA_FILE
              ),
          fileRotationInterval="10s",  # Rotate files every 10 seconds.
          fileRotationMb=4,  # Files of at-most 4mb.
          )
    else:
      return datastream.GcsDestinationConfig(
          gcsFileFormat=(datastream.GcsDestinationConfig
                         .GcsFileFormatValueValuesEnum.AVRO),
          fileRotationInterval="10s",  # Rotate files every 10 seconds.
          fileRotationMb=4,  # Files of at-most 4mb.
          )

  def _CreateStream(self,
                    name,
                    oracle_cp_name,
                    gcs_cp_name,
                    export_file_format):
    stream = datastream.Stream(
        displayName=name,
        destinationConfig=datastream.DestinationConfig(
            destinationConnectionProfileName=gcs_cp_name,
            gcsDestinationConfig=
            self._getGcsDestinationConfig(export_file_format),
        ),
        sourceConfig=self._get_source_config(),
        backfillAll=datastream.BackfillAllStrategy(),
    )

    request = (
        datastream.DatastreamProjectsLocationsStreamsCreateRequest(
            parent=self.datastream_parent, streamId=name, stream=stream))

    response = self.client.projects_locations_streams.Create(request)

    response = self._WaitForCompletion(response)

    logging.debug("Stream creation response: %r", response)
    if not response.error:
      logging.info("SUCCESS: Created stream %r", name)
    return response

  def _StartStream(self, stream_name):
    request = datastream.DatastreamProjectsLocationsStreamsStartRequest(
        name=stream_name)

    response = self.client.projects_locations_streams.Start(request)
    return self._WaitForCompletion(response)
