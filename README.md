# easyogr

EasyOGR, a Python vector geoprocessing library that makes working with OGR easier. Layers can be opened without needing to specify drivers, or pay too much attention to closing instances, and geoprocessing operations can accept a variety of input formats.


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

Common file extensions do not need a driver specifying, and single-layer 


## To do:

