# core.py
#
# by Shaun Astbury
#


# Import required modules.
try:
    from osgeo import ogr, osr
except:
    import ogr
    import osr
import os

ogr.UseExceptions()

# Driver names matched to driver instances.
drivers = {ogr.GetDriver(i).GetName():  ogr.GetDriver(i) for i in
           range(ogr.GetDriverCount())}

# OGR Geometry methods for exporting geometries to other formats.
export_geometries = {'wkt': ogr.Geometry.ExportToWkt,
                     'wkb': ogr.Geometry.ExportToWkb,
                     'kml': ogr.Geometry.ExportToKML,
                     'json': ogr.Geometry.ExportToJson,
                     'gml': ogr.Geometry.ExportToGML}

# OSR SpatialReference methods for exporting to other formats.
export_sr = {'pwkt': osr.SpatialReference.ExportToPrettyWkt,
             'wkt': osr.SpatialReference.ExportToWkt,
             'proj4': osr.SpatialReference.ExportToProj4,
             'pci': osr.SpatialReference.ExportToPCI,
             'xml': osr.SpatialReference.ExportToXML,
             'epsg': osr.SpatialReference.GetAttrValue}

# Matches extensions to drivers.
extensions = {}
for driver in drivers:
    driver = drivers[driver]
    data = driver.GetMetadata()
    if "DMD_EXTENSIONS" in data:
        exts = data["DMD_EXTENSIONS"]
        exts = exts.split(" ")
        for ext in exts:
            extensions["." + ext] = driver

# Match single geometries to multi versions and vice versa.
geom_dict = {'POINT': 'MULTIPOINT',
             'LINESTRING': 'MULTILINESTRING',
             'POLYGON': 'MULTIPOLYGON',
             'MULTIPOINT': 'POINT',
             'MULTILINESTRING': 'LINESTRING',
             'MULTIPOLYGON': 'POLYGON'}

# OGR geometry type codes to names.
geom_types = {ogr.wkbUnknown: 'UNKNOWN',
              ogr.wkbPoint: 'POINT',
              ogr.wkbLineString: 'LINESTRING',
              ogr.wkbPolygon: 'POLYGON',
              ogr.wkbMultiPoint: 'MULTIPOINT',
              ogr.wkbMultiLineString: 'MULTILINESTRING',
              ogr.wkbMultiPolygon: 'MULTIPOLYGON',
              ogr.wkbGeometryCollection: 'GEOMETRYCOLLECTION',
              ogr.wkbNone: 'NONE',
              ogr.wkbLinearRing: 'LINEARRING'}

# OGR geometry creation functions.
import_geometries = {'wkt': ogr.CreateGeometryFromWkt,
                     'wkb': ogr.CreateGeometryFromWkb,
                     'json': ogr.CreateGeometryFromJson,
                     'gml': ogr.CreateGeometryFromGML,
                     'ogr': ogr.Geometry.Clone}

# OSR SpatialReference methods for importing from other formats.
import_sr = {'wkt': osr.SpatialReference.ImportFromWkt,
             'proj4': osr.SpatialReference.ImportFromProj4,
             'url': osr.SpatialReference.ImportFromUrl,
             'esri': osr.SpatialReference.ImportFromESRI,
             'epsg': osr.SpatialReference.ImportFromEPSG,
             'epsga': osr.SpatialReference.ImportFromEPSGA,
             'pci': osr.SpatialReference.ImportFromPCI,
             'usgs': osr.SpatialReference.ImportFromUSGS,
             'xml': osr.SpatialReference.ImportFromXML,
             'erm': osr.SpatialReference.ImportFromERM}

# OGR Geometry spatial predicate methods.
spatial_queries = {'CONTAINS': ogr.Geometry.Contains,
                   'CROSSES': ogr.Geometry.Crosses,
                   'DISJOINT': ogr.Geometry.Disjoint,
                   'EQUALS': ogr.Geometry.Equals,
                   'INTERSECTS': ogr.Geometry.Intersects,
                   'OVERLAPS': ogr.Geometry.Overlaps,
                   'TOUCHES': ogr.Geometry.Touches,
                   'WITHIN': ogr.Geometry.Within}


def add_attribute(iterable, value=None):
    """
    Add an attribute to Features in a generator.

    Parameters:

        - iterable:
            The features to iterate over (list/tuple/generator).

        - value (optional):
            Default value for attribute.

    Yields:

        - feature:
            The result of the tested record (Feature).

    """

    for feature in iterable:
        feature.attributes.append(value)
        yield feature


def cascaded_union(geoms):
    """
    Union multiple OGR Geometries into a single Geometry.

    Parameters:

        - geoms:
            The OGR Geometries to iterate over (list/tuple/generator).

    Returns:

        - geom:
            The resulting geometry (ogr.Geometry).

    """

    geometry = ogr.Geometry(ogr.wkbMultiPolygon)
    for geom in geoms:
        geometry.AddGeometry(geom)
    geom = geometry.UnionCascaded()
    del geometry
    return geom


def create_layer(datasource, field_definitions, geometry_type, fields=None,
                 features=None, spatial_ref=None, layer=None, driver=None):
    """
    Create a data source and layer file, and populate with Features.

    Parameters:

        - datasource:
            Path to the output data source, potentially including the layer
            name (str).

        - field_definitions:
            Feature definitions object or Layer field_definitions dict
            (ogr.FeatureDefn/dict).

        - geometry_type:
            OGR geometry type for the output (int).

        - fields (optional):
            Field names for the output (list/tuple).

        - features (optional):
            The features to iterate over (list/tuple/generator).

        - spatial_ref (optional):
            OSR SpatialReference to set for the output (osr.SpatialReference).

        - layer (optional):
            Name for the output layer, if not given in datasource (str).

        - driver (optional):
            OGR name for the driver to use for the output (str).

    Returns:

        - ds:
            The opened data source (ogr.DataSource).

        - out_layer:
            The created layer (ogr.Layer).

    """

    _, ds = open_ds(datasource, driver, True, "rw")
    layers = ds.GetLayerCount()
    if layer is None:
        layer = get_layer(datasource)
    if layer.upper() in (ds.GetLayerByIndex(i).GetName().upper()
                         for i in xrange(layers)):
        ds.DeleteLayer(layer)
    out_layer = ds.CreateLayer(layer, spatial_ref, geometry_type)
    if isinstance(field_definitions, ogr.FeatureDefn):
        defn = field_definitions
    else:
        for field in field_definitions:
            field_type, precision, width = field_definitions[field]
            field_def = ogr.FieldDefn(field, field_type)
            if precision:
                field_def.SetPrecision(precision)
            if width:
                field_def.SetWidth(width)
            out_layer.CreateField(field_def)
        defn = out_layer.GetLayerDefn()
    if features:
        for feature in features:
            if spatial_ref:
                feature = feature.transform(spatial_ref, in_place=False)
            feat = create_ogr_feature(defn, feature.ogr_geom,
                                      feature.attributes, fields)
            out_layer.CreateFeature(feat)
    return ds, out_layer


def create_ogr_feature(definition, ogr_geom, attributes=[], fields=None):
    """
    Create an OGR Feature object from a OGR Geometry, OGR FeatureDefn, and a
    set of attributes.

    Parameters:

        - field_definitions:
            Feature definitions object or Layer field_definitions dict
            (ogr.FeatureDefn/dict).

        - ogr_geom:
            OGR geometry for the output (ogr.Geometry).

        - attributes (optional):
            The attributes to include in the output feature (list/tuple).

        - fields (optional):
            Field names for the output (list/tuple).

    Returns:

        - feature:
            The created Feature object (ogr.Feature).

    """

    feature = ogr.Feature(definition)
    if fields is None:
        fields = [definition.GetFieldDefn(i).GetName() for
                  i in xrange(definition.GetFieldCount())]
    feature.SetGeometry(ogr_geom)
    for field, attribute in zip(fields, attributes):
        feature.SetField(field, attribute)
    return feature


def extent_to_polygon(minx, miny, maxx, maxy):
    """
    Create an OGR Geometry from a bounding box extent.

    Parameters:

        - minx:
            Minimum x value for extent (int/float).

        - miny:
            Minimum y value for extent (int/float).

        - maxx:
            Maximum x value for extent (int/float).

        - maxy:
            Maxmum y value for extent (int/float).

    Returns:

        - ogr_geom:
            The resultant OGR Geometry (ogr.Geometry)

    """

    extent = "POLYGON (("
    extent += "{0} {1}, {2} {1}, {2} {3}, {0} {3}, {0} {1}".format(
               minx, miny, maxx, maxy)
    extent += "))"
    return import_geometries['wkt'](extent)


def get_layer(datasource):
    """
    Gets the layer name of single-layer data sources. If not possible (e.g.
    database connection strings), raises an exception.

    Parameters:

        - datasource:
            File path for the datasource, or an OGR DataSource instance
            (ogr.DataSource/str).

    Returns:

        - layer_name:
            The name of the layer, determined as the basename of the input
            data source, excluding any file extension (str).

    """

    try:
        if isinstance(datasource, ogr.DataSource):
            datasource = datasource.GetName()
        layer_name = os.path.basename(os.path.splitext(datasource)[0])
        return layer_name
    except:
        print "\nNo layer parameter supplied when required by data source."
        raise Exception()


def map_geom(func, iterable, *args, **kwargs):
    """
    Apply spatial operations to Features in an iterable.

    Parameters:

        - func:
            The function to use (func).

        - iterable:
            The features to iterate over (list/tuple/generator).

    Yields:

        - feature:
            The result of the spatial operation (Feature).

    """

    for i in iterable:
        feature = func(i, *args, **kwargs)
        if feature is not None:
            yield feature


def open_ds(datasource, driver=None, create=False, mode="r"):
    """
    Opens OGR DataSources.

    Parameters:

        - datasource:
            File system path to an OGR-readable data source, or a database
            connection string (str).

        - driver (optional):
            Name of the driver to use, in OGR format (str). If not
            supplied, this will be determined from the file extension, or
            by attempting all drivers (str).

        - create (optional):
            If True, create a new data source, otherwise if not found, raise an
            exception (default) (bool).

        - mode (optional):
            Set "r" for read only, or "rw" for read/write. OGR 0/1 is also
            accepted. Read only is default (int/str).

    Returns:

        - driver:
            The driver used to open the DataSource (ogr.Driver).

        - ds:
            The opened OGR DataSource (ogr.DataSource).

    """

    modes = {"r": 0, "rw": 1}
    if mode in modes:
        mode = modes[mode]
    elif mode not in modes.values:
        print "\nSupplied mode parameter value not valid."
        raise Exception()
    ext = os.path.splitext(datasource)[1]
    if driver is None:
        if ext in extensions:
            driver = extensions[ext]
        elif create:
            print "\nNo driver parameter supplied to create data source."
            raise Exception()
    elif not isinstance(driver, ogr.Driver):
        try:
            driver = ogr.GetDriverByName(driver)
        except:
            print ("\nSupplied driver parameter value not valid, or driver " +
                   "not available.")
            raise Exception()
    if os.path.exists(datasource):
        try:
            if driver is None:
                ds = ogr.Open(datasource, mode)
                driver = ds.GetDriver()
            else:
                ds = driver.Open(datasource, mode)
        except:
            print ("\nFailed to open data source, file " +
                   "format not supported.")
            raise Exception()
    else:
        if create:
            try:
                if not os.path.exists(os.path.dirname(datasource)):
                    os.makedirs(os.path.dirname(datasource))
                ds = driver.CreateDataSource(datasource)
            except:
                print "\nCould not create Data Source {0}.".format(datasource)
                raise Exception()
        else:
            print "\nData Source {0} does not exist.".format(datasource)
            raise Exception()
    return driver, ds


def spatial_query(query, iterable, feature):
    """
    Filter Features in an iterable by spatial predicate.

    Parameters:

        - query:
            The spatial predicate function to use (func).

        - iterable:
            The features to iterate over (list/tuple/generator).

        - feature:
            The operation feature to apply (Feature)

    Yields:

        - feature:
            The result of the spatial operation (Feature).

    """

    for i in iterable:
        result = query(i, feature)
        if result:
            yield i


def update_attributes(iterable, field, value, fields, clause=None):
    """
    Alter the value of an Feature attribute in an iterable.

    Parameters:

        - iterable:
            The features to iterate over (list/tuple/generator).

        - field:
            The field to adjust (str).

        - fields:
            The fields present in the clause (list/tuple).

        - clause:
            The input query string (str).

    Yields:

        - feature:
            The result of the spatial operation (Feature).

    """

    idx = fields.index(field)
    if clause:
        query = Query(fields, clause)
        for feature in iterable:
            if query.test(feature.attributes):
                feature.attributes[idx] = value
            yield feature
    else:
        for feature in iterable:
            feature.attributes[idx] = value
            yield feature


def update_feature(func, iterable, *args):
    """
    Apply spatial operations to Features in an iterable.

    Parameters:

        - func:
            The function to use (func).

        - iterable:
            The features to iterate over (list/tuple/generator).

    Yields:

        - feature:
            The result of the spatial operation (Feature).

    """

    for feature in iterable:
        func(feature, *args)
        yield feature


class Query(object):
    """
    Basic query evaluator. Will test any input to the query - no validation or
    parsing, just replaces fields with test values and calls eval.

    Methods:

        - test:
            Tests the attributes of a records against the acceptable input
            clause.

    Attributes:

        - clause:
            The input query string (str).

        - fields:
            The fields present in the clause (list/tuple).

    """

    def __init__(self, fields, clause):
        """
        Basic query evaluator. Will test any input to the query - no validation
        or parsing, just replaces fields with test values and calls eval.
        
        Parameters:
            
            - fields:
                Names of all fields present in the tested records, which should
                match the clause (list/tuple).
                
            - clause:
                Query string to apply to the inputs. Input must be valid
                Python, using unquoted field names and field values as they
                would be defined in Python, e.g. field_1 >= 1 or field_2 == "A"
                (str).
        
        """

        self.fields = fields
        self.clause = clause

    def test(self, record):
        """
        Test a record against the clause, extracting its values based on field
        indicies.
        
        Parameters:
        
            - record:
                The values to test. Attributes must be set in the order of the
                instance fields attribute (list/tuple).
                
        Returns:
        
            - result:
                The result of the tested record (bool).
        
        """
        
        test = self.clause[:]
        for field in self.fields:
            test_value = record[self.fields.index(field)]
            if type(test_value) in (str, unicode):
                test = test.replace(field + ' ',   + test_value + '" ')
            else:
                test = test.replace(field + ' ', str(test_value) + ' ')
        test = test.replace(" = ", " == ")
        return eval(test)
