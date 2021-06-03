"""Deploy and Manage Datastream Jobs.

Utilities to deploy and manage Datastream resources via CLI.
"""

from typing import Any, Sequence

from absl import app
from absl import flags

import cloud_datastream_resource_manager

flags.DEFINE_enum("action", "list", ["create", "tear-down", "list"],
                  "Datastream Action to Run.")
flags.DEFINE_string("project-number", None,
                    "The GCP Project Number to be used",
                    required=True, short_name="p")
flags.DEFINE_string("stream-prefix", None,
                    "Alphanumeric lowercase resource prefix",
                    required=True, short_name="sp")
flags.DEFINE_string("gcs-prefix", None,
                    "Alphanumeric lowercase resource prefix",
                    required=True, short_name="gp")
flags.DEFINE_string("source-prefix", None,
                    "Alphanumeric lowercase resource prefix",
                    required=True, short_name="op")
flags.DEFINE_string("gcs-bucket", None,
                    "GCS Bucket Name supplied with or w/o gs:// prefix",
                    required=True)
flags.DEFINE_string("gcs-root-path", "/data/",
                    "GCS root path for Datastream to insert data")

flags.DEFINE_string("oracle-host", None, "Host for Oracle DB", required=True)
flags.DEFINE_string("oracle-port", "1521",
                    "Port for Oracle DB (default 1521)")
flags.DEFINE_string("oracle-user", None, "User for Oracle DB connections",
                    required=True)
flags.DEFINE_string("oracle-password", None,
                    "Password for Oracle DB connections", required=True)
flags.DEFINE_string("oracle-database", None, "Database to connect to Oracle",
                    required=True)
flags.DEFINE_string("private-connection", None,
                    "The name of the private connection to use when required.")

flags.DEFINE_string("schema-names", None,
                    "Names of the schemas to include in Stream")
flags.DEFINE_string("table-names", None,
                    "Names of the tables to include in Stream")


def _get_flag(field: str) -> Any:
  """Returns the value of the request flag."""
  return flags.FLAGS.get_flag_value(field, None)


def main(unused_argv: Sequence[str] = None) -> None:
  action = _get_flag("action")
  project_number = _get_flag("project-number")

  stream_prefix = _get_flag("stream-prefix")
  cp_gcs_prefix = _get_flag("gcs-prefix")
  cp_source_prefix = _get_flag("source-prefix")

  gcs_bucket = _get_flag("gcs-bucket")
  gcs_root_path = _get_flag("gcs-root-path")

  schema_names = _get_flag("schema-names")
  table_names = _get_flag("table-names")

  oracle_cp = {
      "hostname": _get_flag("oracle-host"),
      "port": int(_get_flag("oracle-port")),
      "databaseService": _get_flag("oracle-database"),
      "username": _get_flag("oracle-user"),
      "password": _get_flag("oracle-password"),
  }
  if table_names:
    allowed_tables = [(schema_names, table) for table in table_names.split()]
  elif schema_names:
    allowed_tables = [(schema, None) for schema in schema_names.split()]
  else:
    allowed_tables = []

  manager = cloud_datastream_resource_manager.CloudDatastreamResourceManager(
      project_number=project_number,
      gcs_bucket_name=gcs_bucket,
      gcs_root_path=gcs_root_path,
      stream_name=stream_prefix,
      source_cp_name=cp_source_prefix,
      target_cp_name=cp_gcs_prefix,
      oracle_cp=oracle_cp,
      allowed_tables=allowed_tables,
      add_uid_suffix=False,
      private_connection_name=_get_flag("private-connection"),
  )
  print(manager.Describe())

  if action == "create":
    manager.SetUp()
  elif action == "tear-down":
    manager.TearDown()
  elif action == "list":
    manager.ListStreams()


if __name__ == "__main__":
  app.run(main)
