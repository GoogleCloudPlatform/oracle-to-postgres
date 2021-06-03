# Datastream Manager Client

## Set Up

**Build the Datastream Proto Packages**

```
blaze build google/cloud/datastream:python_client_v1alpha1

cp -r blaze-genfiles/google/cloud/datastream/datastream experimental/dhercher/datastream_utils/
```

**Copy Dataflow Testing Utils**

This should eventually happen in reverse. This util should be imported by
Dataflow.

`g4 copy
cloud/dataflow/testing/integration/teleport/environment/cloud_datastream_resource_manager.py
experimental/dhercher/datastream_utils/`

`g4 copy
cloud/dataflow/testing/integration/teleport/environment/cloud_datastream_resource_manager_test.py
experimental/dhercher/datastream_utils/`

**[All changes required to make the util OSS](http://cl/368307780)**

## Run Tests

`blaze test
//experimental/dhercher/datastream_utils:cloud_datastream_resource_manager_test`
