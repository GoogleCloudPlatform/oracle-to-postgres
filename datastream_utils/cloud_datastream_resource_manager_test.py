"""Tests for google3.cloud.dataflow.testing.integration.teleport.environment.cloud_datastream_resource_manager."""

import logging
import mock

from google3.experimental.dhercher.datastream_utils import cloud_datastream_resource_manager
from google3.google.cloud.datastream import datastream
from google3.testing.pybase import googletest

_EX_ORACLE_CP = {
    "hostname": "127.0.0.1",
    "username": "oracle",
    "databaseService": "XE",
    "password": "oracle",
    "port": 1521
}


class CloudDatastreamResourceManagerTest(googletest.TestCase):

  def test_default_property_names(self):
    client_mock = mock.MagicMock()
    rm = cloud_datastream_resource_manager.CloudDatastreamResourceManager(
        1234567890, "bucket-name",
        client=client_mock, oracle_cp=_EX_ORACLE_CP)

    self.assertEqual(rm.datastream_parent,
                     "projects/1234567890/locations/us-central1")
    self.assertIsNotNone(rm.suffix)
    self.assertIsNotNone(rm.path_suffix)
    self.assertIn("streams/datastream-test-", rm.full_stream_name)
    self.assertIn("connectionProfiles/oracle-cp-",
                  rm.full_source_connection_name)
    self.assertIn("connectionProfiles/gcs-cp-", rm.full_dest_connection_name)
    self.assertEqual(rm.gcs_bucket, "gs://bucket-name")
    self.assertStartsWith(rm.gcs_location,
                          "gs://bucket-name/rootprefix/")

  def test_create_cps(self):
    client_mock = mock.MagicMock()
    rm = cloud_datastream_resource_manager.CloudDatastreamResourceManager(
        1234567890, "bucket-name",
        client=client_mock, oracle_cp=_EX_ORACLE_CP)
    unused_oracle_result = rm._CreateDatabaseConnectionProfile()

    unused_gcs_result = rm._CreateGcsConnectionProfile(
        "test",
        bucket_name="anybucket",
        root_path="anyroot")

  def test_list_cps(self):
    client_mock = mock.MagicMock()
    rm = cloud_datastream_resource_manager.CloudDatastreamResourceManager(
        1234567890, "bucket-name",
        client=client_mock, oracle_cp=_EX_ORACLE_CP)
    logging.warning(rm._ListConnectionProfiles())

  def test_create_stream(self):
    client_mock = mock.create_autospec(datastream.DatastreamV1alpha1,
                                       instance=True)
    unused_rm = (
        cloud_datastream_resource_manager.CloudDatastreamResourceManager(
            1234567890, "bucket-name",
            client=client_mock, oracle_cp=_EX_ORACLE_CP))

  def test__get_oracle_rdbms(self):
    client_mock = mock.create_autospec(datastream.DatastreamV1alpha1,
                                       instance=True,
                                       spec_set=False)

    rm = cloud_datastream_resource_manager.CloudDatastreamResourceManager(
        1234567890, "bucket-name",
        client=client_mock, oracle_cp=_EX_ORACLE_CP)

    table_list = [("test", "table"), ("test2", None)]
    oracle_rdbms = rm._get_oracle_rdbms(table_list)

    expected_rdbms = datastream.OracleRdbms(oracleSchemas=[
        datastream.OracleSchema(
            schemaName="test",
            oracleTables=[datastream.OracleTable(tableName="table")]),
        datastream.OracleSchema(schemaName="test2", oracleTables=[])])
    self.assertEqual(oracle_rdbms, expected_rdbms)

  def test__get_mysql_rdbms(self):
    client_mock = mock.create_autospec(datastream.DatastreamV1alpha1,
                                       instance=True,
                                       spec_set=False)

    rm = cloud_datastream_resource_manager.CloudDatastreamResourceManager(
        1234567890, "bucket-name",
        client=client_mock, oracle_cp=_EX_ORACLE_CP)

    table_list = [("test", "table"), ("test2", None)]
    mysql_rdbms = rm._get_mysql_rdbms(table_list)

    expected_rdbms = datastream.MysqlRdbms(mysqlDatabases=[
        datastream.MysqlDatabase(
            databaseName="test",
            mysqlTables=[datastream.MysqlTable(tableName="table")]),
        datastream.MysqlDatabase(databaseName="test2", mysqlTables=[])])
    self.assertEqual(mysql_rdbms, expected_rdbms)

  def test_full_flow(self):
    client_mock = mock.create_autospec(datastream.DatastreamV1alpha1,
                                       instance=True,
                                       spec_set=False)

    rm = cloud_datastream_resource_manager.CloudDatastreamResourceManager(
        1234567890, "bucket-name",
        client=client_mock, oracle_cp=_EX_ORACLE_CP)

    class SuccessResult(object):

      def __init__(self, **kwargs):
        self.kwargs = kwargs

      def __getattr__(self, name):
        return self.kwargs.get(name)

    always_success = SuccessResult(done=True)

    client_mock.projects_locations_connectionProfiles = mock.Mock()
    client_mock.projects_locations_connectionProfiles.Create.return_value = always_success
    client_mock.projects_locations_connectionProfiles.Delete.return_value = always_success
    client_mock.projects_locations_streams = mock.Mock()
    client_mock.projects_locations_streams.Create.return_value = always_success
    client_mock.projects_locations_streams.Start.return_value = always_success
    client_mock.projects_locations_streams.Pause.return_value = always_success
    client_mock.projects_locations_streams.Delete.return_value = always_success
    client_mock.projects_locations_operations = mock.Mock()
    client_mock.projects_locations_operations.Get.return_value = always_success

    rm.SetUp()
    rm.TearDown()


if __name__ == "__main__":
  googletest.main()
