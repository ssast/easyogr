# easyogr

EasyOGR, a Python vector geoprocessing library that makes working with OGR easier. Layers can be opened without needing to specify drivers, or pay too much attention to closing instances, and geoprocessing operations can accept a variety of input formats. Multiple geoprocessing tasks can be completed with single function calls e.g. selecting, intersecting and transforming a Layer.


## Requirements

Tested only with Python 2.7, likely not compatible with Python 3 (yet). Needs Python osgeo (GDAL/OGR), which is not included with this package.


## Classes

Feature:

A single spatial feature, containing an OGR Geometry, an OSR SpatialReference, and possible attributes. Methods perform spatial operations with other Features e.g. intersection, difference, union, and test spatial predicates e.g. contains, intersects, touches etc.

FeatureGenerator:

A generator on an OGR-readable DataSource Layer, yielding Features. Methods adjust the generator cursor, selecting or editing output Features with spatial operations and predicates. When the generator is completely yielded, or saved to an output file, the instance is closed, and cannot be used again.

FeatureLayer:

An OGR Layer view, also iterable for Features, but without affecting the status of the instance, Methods set selections for which Features are active in the instance, and perform geoprocessing operations on the current Feature selection, writing results to file.


## Functions:

A number of geoprocessing functions are also available, each of which have similar parameters, accepting an input layer, an output layer, and optional operation layers, where clasues, fields, intersect features, drivers, layer names, and spatial reference arguments. These functions include buffer, copy_layer, difference, erase, identity, intersection, union, and update.


## Examples:

Common file extensions do not need a driver specifying, and single-layer DataSources do not need a layer name. So to clip a Shapefile:

`intersection('in_layer.shp', 'op_layer.shp', 'out_layer.shp')`

Using multi-layer DataSources requires a layer parameter to be set, and outputs without file extensions do require a driver name. See the full list of driver names at http://www.gdal.org/ogr_formats.html:

`erase('in_layer.shp', 'op_layer.shp', 'post_gis_cnxn_string', out_layer='out_layer', out_driver='PostgreSQL')`

Many functions and methods producing output files accept optional arguments to filter the fields, features and change the spatial reference of the output. See the OGR SQL documentation for the clause parameter http://www.gdal.org/ogr_sql.html:

```copy_layer('in_layer.shp', 'out_layer.shp', fields=['field_a', 'field_b'], clause='field_a >= 10', intersects=[10.45, 4.67, 14.43, 11.32], spatial_ref=27700, sr_format='srid')```

A Feature can be instantiated from a variety of inputs, including ogr.Geometry, wkt, geojson etc:

`feat = Feature('POINT (0, 1)', attributes=[1, 2, 3], geom_format='wkt')`

Feature methods on other geometries accept the same inputs as Features:

`feat.distance('POINT (2, 2)', geom_format='wkt')`

Both FeatureLayer and FeatureGenerator are instantiated from an input datasource, and optional layer and driver arguments, with the opened Layer filtered by inputs to the clause, intersects, and fields parameters:

```layer = FeatureLayer('in_layer.shp', fields=['field_a', 'field_b'], clause='field_a >= 10', intersects=[10.45, 4.67, 14.43, 11.32])```


## To do:

- Finish this readme
- Expand the range of geoprocessing functions/methods
- Write a full API
- Enable Python 3 compatibility
- Functions to rename/Move/Delete spatial files
- Provide option to copy attributes from operation layers/features
