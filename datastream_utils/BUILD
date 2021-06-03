load("//devtools/python/blaze:pytype.bzl", "pytype_strict_library")
load("//devtools/python/blaze:strict.bzl", "py_strict_test")

package(
    default_testonly = 1,
    # default_visibility = [
    #     "//*",
    # ],
)

################################################################################
# Definitions for the teleport pipeline resource manager utilities
################################################################################

pytype_strict_library(
    name = "cloud_datastream_resource_manager",
    srcs = ["cloud_datastream_resource_manager.py"],
    srcs_version = "PY3",
    deps = [
        "//cloud/dataflow/testing/creds:service_accounts",
        "//cloud/dataflow/testing/framework/environment:file_helper",
        "//cloud/dataflow/testing/framework/protos:resource_manager_result_py_pb2",
        "//cloud/dataflow/testing/framework/protos:shared_framework_enums_py_pb2",
        "//google/cloud/datastream:python_client_v1alpha1",
        "//pipeline/testing/uif/environment:resource_manager",
    ],
)

py_strict_test(
    name = "cloud_datastream_resource_manager_test",
    srcs = ["cloud_datastream_resource_manager_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":cloud_datastream_resource_manager",
        "//google/cloud/datastream:python_client_v1alpha1",
        "//net/proto2/python/public:use_pure_python",  # fixdeps: keep go/proto_python_default
        "//testing/pybase",
        "//third_party/py/mock",
    ],
)

# For runner we will use both g3 and reqs (maybe)?
# "//third_party/py/absl:app",
# "//third_party/py/absl/flags",
# "//third_party/py/absl/logging",
