# layer.py
#
# by Shaun Astbury
#


# Import required modules.
try:
    from osgeo import ogr, osr
except:
    import ogr
    import osr
from collections import OrderedDict
from feature import Feature, format_geom, ogr_to_feature
from core import (Query, add_attribute, create_layer, create_ogr_feature,
                  export_sr, extent_to_polygon, geom_types, import_sr,
                  map_geom, open_ds, get_layer, spatial_queries, spatial_query,
                  update_feature, update_attributes)


def format_layer(datasource, layer=None):
    """
    Opens an OGR Layer from an input file path string, extracts an ogr_layer,
    or converts a OGR Geometry or Feature into an OGR Layer. Code is likely to
    change, but functionality and parameters should remain the same.

    Parameters:

        - datasource:
            The layer object or datasource path to process. Acceptable inputs
            are FeatureLayer, FeatureGenerator, Dataset, Feature, ogr.Layer,
            ogr.DataSource, ogr.Geometry and ogr.Feature (str/obj).

        - layer (optional):
            Name or index of the layer to open. Only applicable if datasource
            is a Dataset, OGR DataSource, or a file path/database string (str).

    Returns:

        - ds:
            If opening a new layer, or creating a memory layer, provide the
            OGR DataSource used. Otherwise, return None (ogr.DataSource).

        - layer:
            The OGR Layer derived from the input layer parameter (ogr.Layer).

    """

    # Get OGR Layer, if present.
    if not isinstance(datasource, ogr.Layer):
        try:
            if isinstance(datasource, FeatureLayer):
                layer = datasource.ogr_layer
                ds = None

            # Get layer for Dataset or DataSource instances.
            elif isinstance(datasource, Dataset):
                if layer is None:
                    layer = get_layer(datasource)
                layer = datasource._open_layer(layer)
                ds = datasource
            elif isinstance(datasource, ogr.DataSource):
                if layer is None:
                    layer = get_layer(datasource)
                layer = datasource.GetLayerByName(layer)
                ds = datasource

            # If a string, open as a datasource, and get layer.
            elif type(datasource) == 'str':
                _, datasource = open_ds(datasource)
                if layer is None:
                    layer = get_layer(datasource)
                layer = ds.GetLayerByName(layer)

            # Final attempt, creating a memory layer from a single geometry,
            # or an iterable of geometries. Keep count to try and avoid
            # duplicates.
            else:
                geom = format_geom(datasource)
                if not layer:
                    format_layer.mem_count += 1
                    layer = "Temp" + str(format_layer.mem_count)
                driver = ogr.GetDriverByName("MEMORY")
                format_layer.mem_count += 1
                ds = driver.CreateDataSource(layer)
                layer = ds.CreateLayer(layer, geom.GetSpatialReference(),
                                       geom.GetGeometryType())
                feature = create_ogr_feature(ogr.FeatureDefn(),
                                             geom, [], [])
                layer.CreateFeature(feature)
        except Exception as e:
            print '\nInput data source or layer invalid.'
            raise e
    else:
        ds = None
        layer = datasource
    return ds, layer
format_layer.mem_count = 0


def buffer(in_ds, buffer_dist, out_ds, fields='*', clause=None,
           intersects=None, in_layer=None, out_layer=None, out_driver=None,
           spatial_ref=None, sr_format='osr'):
    """
    Perform an buffer operation between two layers.

    Parameters:

        - in_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the focal layer (str).

        - buffer_dist:
            The buffer distance to apply to each Feature (float/int).

        - out_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the output layer (str).

        - fields (optional):
            Filter to select the fields to use from in_layer. The default
            value of "*" will include all fields. Single fields are passed as
            strings, or multiple fields with a collection (str/list/tuple).

        - clause (optional):
            Set a OGR-SQL clause to filter the layer features by field
            attributes. See http://www.gdal.org/ogr_sql.html (str).

        - intersects (optional):
            Filter results by bounding box, from an OGR Geometry, easyOGR
            Feature, or a bounding box tuple in the format (minx, miny, maxx,
            maxy) (tuple).

        - in_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - out_layer (optional):
            Name of the in_ds layer to create. Not required for single-layer
            data sources (e.g. Shapefile) (str).

        - out_driver (optional):
            Specify the OGR driver to use for the output, in OGR string format,
            or an OGR Driver instance. This is not necessarily required where
            out_ds has a standard file extension .e.g '.shp' (str/ogr.Driver).

        - spatial_ref (optional):
            Spatial reference to use for projecting the Features. Input must be
            valid for sr_format. Default uses the reference of in_layer
            (str/obj).

        - sr_format (optional):
            Format of spatial_ref. Valid formats are osr (default), wkt, proj4,
            url, esri, epsg, epsga, pci, usgs, xml, erm (str).

    """

    layer = FeatureLayer(in_ds, fields, clause, intersects, in_layer)
    layer.buffer(buffer_dist, out_ds, out_layer, out_driver, spatial_ref,
                 sr_format)
    layer.close()


def copy_layer(in_ds, out_ds, fields='*', clause=None, intersects=None,
               in_layer=None, out_layer=None, out_driver=None,
               spatial_ref=None, sr_format='osr'):
    """
    Copy a layer, optionally to another format, filtering features by spatial
    intersect or attributes, and transforming to another spatial reference.

    Parameters:

        - in_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the focal layer (str).

        - out_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the output layer (str).

        - fields (optional):
            Filter to select the fields to use from in_layer. The default
            value of "*" will include all fields. Single fields are passed as
            strings, or multiple fields with a collection (str/list/tuple).

        - clause (optional):
            Set a OGR-SQL clause to filter the layer features by field
            attributes. See http://www.gdal.org/ogr_sql.html (str).

        - intersects (optional):
            Filter results by bounding box, from an OGR Geometry, easyOGR
            Feature, or a bounding box tuple in the format (minx, miny, maxx,
            maxy) (tuple).

        - in_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - out_layer (optional):
            Name of the in_ds layer to create. Not required for single-layer
            data sources (e.g. Shapefile) (str).

        - out_driver (optional):
            Specify the OGR driver to use for the output, in OGR string format,
            or an OGR Driver instance. This is not necessarily required where
            out_ds has a standard file extension .e.g '.shp' (str/ogr.Driver).

        - spatial_ref (optional):
            Spatial reference to use for projecting the Features. Input must be
            valid for sr_format. Default uses the reference of in_layer
            (str/obj).

        - sr_format (optional):
            Format of spatial_ref. Valid formats are osr (default), wkt, proj4,
            url, esri, epsg, epsga, pci, usgs, xml, erm (str).

    """

    layer = FeatureLayer(in_ds, fields, clause, intersects, in_layer)
    if spatial_ref:
        layer.transform(spatial_ref, out_ds, sr_format, out_layer, out_driver)
    else:
        layer.export(out_ds, out_layer, out_driver)
    layer.close()


def difference(in_ds, op_ds, out_ds, fields='*', clause=None, intersects=None,
               in_layer=None, op_layer=None, out_layer=None, out_driver=None,
               spatial_ref=None, sr_format='osr'):
    """
    Perform a difference operation between two layers.

    Parameters:

        - in_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the focal layer (str).

        - op_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the operation layer (str).

        - out_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the output layer (str).

        - fields (optional):
            Filter to select the fields to use from in_layer. The default
            value of "*" will include all fields. Single fields are passed as
            strings, or multiple fields with a collection (str/list/tuple).

        - clause (optional):
            Set a OGR-SQL clause to filter the layer features by field
            attributes. See http://www.gdal.org/ogr_sql.html (str).

        - intersects (optional):
            Filter results by bounding box, from an OGR Geometry, easyOGR
            Feature, or a bounding box tuple in the format (minx, miny, maxx,
            maxy) (tuple).

        - in_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - op_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - out_layer (optional):
            Name of the in_ds layer to create. Not required for single-layer
            data sources (e.g. Shapefile) (str).

        - out_driver (optional):
            Specify the OGR driver to use for the output, in OGR string format.
            or an OGR Driver instance. This is not necessarily required where
            out_ds has a standard file extension .e.g '.shp' (str/ogr.Driver).

        - spatial_ref (optional):
            Spatial reference to use for projecting the Features. Input must be
            valid for sr_format. Default uses the reference of in_layer
            (str/obj).

        - sr_format (optional):
            Format of spatial_ref. Valid formats are osr (default), wkt, proj4,
            url, esri, epsg, epsga, pci, usgs, xml, erm (str).

    """

    layer = FeatureLayer(in_ds, fields, clause, intersects, in_layer)
    layer.difference(op_ds, out_ds, op_layer, out_layer, out_driver,
                     spatial_ref, sr_format)
    layer.close()


def erase(in_ds, op_ds, out_ds, fields='*', clause=None, intersects=None,
          in_layer=None, op_layer=None, out_layer=None, out_driver=None,
          spatial_ref=None, sr_format='osr'):
    """
    Perform an erase operation between two layers.

    Parameters:

        - in_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the focal layer (str).

        - op_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the operation layer (str).

        - out_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the output layer (str).

        - fields (optional):
            Filter to select the fields to use from in_layer. The default
            value of "*" will include all fields. Single fields are passed as
            strings, or multiple fields with a collection (str/list/tuple).

        - clause (optional):
            Set a OGR-SQL clause to filter the layer features by field
            attributes. See http://www.gdal.org/ogr_sql.html (str).

        - intersects (optional):
            Filter results by bounding box, from an OGR Geometry, easyOGR
            Feature, or a bounding box tuple in the format (minx, miny, maxx,
            maxy) (tuple).

        - in_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - op_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - out_layer (optional):
            Name of the in_ds layer to create. Not required for single-layer
            data sources (e.g. Shapefile) (str).

        - out_driver (optional):
            Specify the OGR driver to use for the output, in OGR string format.
            or an OGR Driver instance. This is not necessarily required where
            out_ds has a standard file extension .e.g '.shp' (str/ogr.Driver).

        - spatial_ref (optional):
            Spatial reference to use for projecting the Features. Input must be
            valid for sr_format. Default uses the reference of in_layer
            (str/obj).

        - sr_format (optional):
            Format of spatial_ref. Valid formats are osr (default), wkt, proj4,
            url, esri, epsg, epsga, pci, usgs, xml, erm (str).

    """

    layer = FeatureLayer(in_ds, fields, clause, intersects, in_layer)
    layer.erase(op_ds, out_ds, op_layer, out_layer, out_driver,
                spatial_ref, sr_format)
    layer.close()


def identity(in_ds, op_ds, out_ds, fields='*', clause=None, intersects=None,
             in_layer=None, op_layer=None, out_layer=None, out_driver=None,
             spatial_ref=None, sr_format='osr'):
    """
    Perform an identity operation between two layers.

    Parameters:

        - in_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the focal layer (str).

        - op_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the operation layer (str).

        - out_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the output layer (str).

        - fields (optional):
            Filter to select the fields to use from in_layer. The default
            value of "*" will include all fields. Single fields are passed as
            strings, or multiple fields with a collection (str/list/tuple).

        - clause (optional):
            Set a OGR-SQL clause to filter the layer features by field
            attributes. See http://www.gdal.org/ogr_sql.html (str).

        - intersects (optional):
            Filter results by bounding box, from an OGR Geometry, easyOGR
            Feature, or a bounding box tuple in the format (minx, miny, maxx,
            maxy) (tuple).

        - in_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - op_layer (optional):
            Name of the op_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - out_layer (optional):
            Name of the in_ds layer to create. Not required for single-layer
            data sources (e.g. Shapefile) (str).

        - out_driver (optional):
            Specify the OGR driver to use for the output, in OGR string format,
            or an OGR Driver instance. This is not necessarily required where
            out_ds has a standard file extension .e.g '.shp' (str/ogr.Driver).

        - spatial_ref (optional):
            Spatial reference to use for projecting the Features. Input must be
            valid for sr_format. Default uses the reference of in_layer
            (str/obj).

        - sr_format (optional):
            Format of spatial_ref. Valid formats are osr (default), wkt, proj4,
            url, esri, epsg, epsga, pci, usgs, xml, erm (str).

    """

    layer = FeatureLayer(in_ds, fields, clause, intersects, in_layer)
    layer.identity(op_ds, out_ds, op_layer, out_layer, out_driver,
                   spatial_ref, sr_format)
    layer.close()


def intersection(in_ds, op_ds, out_ds, fields='*', clause=None,
                 intersects=None, in_layer=None, op_layer=None, out_layer=None,
                 out_driver=None, spatial_ref=None, sr_format='osr'):
    """
    Perform an intersection between two layers.

    Parameters:

        - in_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the focal layer (str).

        - op_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the operation layer (str).

        - out_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the output layer (str).

        - fields (optional):
            Filter to select the fields to use from in_layer. The default
            value of "*" will include all fields. Single fields are passed as
            strings, or multiple fields with a collection (str/list/tuple).

        - clause (optional):
            Set a OGR-SQL clause to filter the layer features by field
            attributes. See http://www.gdal.org/ogr_sql.html (str).

        - intersects (optional):
            Filter results by bounding box, from an OGR Geometry, easyOGR
            Feature, or a bounding box tuple in the format (minx, miny, maxx,
            maxy) (tuple).

        - in_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - op_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - out_layer (optional):
            Name of the in_ds layer to create. Not required for single-layer
            data sources (e.g. Shapefile) (str).

        - out_driver (optional):
            Specify the OGR driver to use for the output, in OGR string format.
            or an OGR Driver instance. This is not necessarily required where
            out_ds has a standard file extension .e.g '.shp' (str/ogr.Driver).

        - spatial_ref (optional):
            Spatial reference to use for projecting the Features. Input must be
            valid for sr_format. Default uses the reference of in_layer
            (str/obj).

        - sr_format (optional):
            Format of spatial_ref. Valid formats are osr (default), wkt, proj4,
            url, esri, epsg, epsga, pci, usgs, xml, erm (str).

    """

    layer = FeatureLayer(in_ds, fields, clause, intersects, in_layer)
    layer.intersection(op_ds, out_ds, op_layer, out_layer, out_driver,
                       spatial_ref, sr_format)
    layer.close()


def union(in_ds, op_ds, out_ds, fields='*', clause=None, intersects=None,
          in_layer=None, op_layer=None, out_layer=None, out_driver=None,
          spatial_ref=None, sr_format='osr'):
    """
    Perform a union operation between two layers.

    Parameters:

        - in_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the focal layer (str).

        - op_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the operation layer (str).

        - out_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the output layer (str).

        - fields (optional):
            Filter to select the fields to use from in_layer. The default
            value of "*" will include all fields. Single fields are passed as
            strings, or multiple fields with a collection (str/list/tuple).

        - clause (optional):
            Set a OGR-SQL clause to filter the layer features by field
            attributes. See http://www.gdal.org/ogr_sql.html (str).

        - intersects (optional):
            Filter results by bounding box, from an OGR Geometry, easyOGR
            Feature, or a bounding box tuple in the format (minx, miny, maxx,
            maxy) (tuple).

        - in_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - op_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - out_layer (optional):
            Name of the in_ds layer to create. Not required for single-layer
            data sources (e.g. Shapefile) (str).

        - out_driver (optional):
            Specify the OGR driver to use for the output, in OGR string format.
            or an OGR Driver instance. This is not necessarily required where
            out_ds has a standard file extension .e.g '.shp' (str/ogr.Driver).

        - spatial_ref (optional):
            Spatial reference to use for projecting the Features. Input must be
            valid for sr_format. Default uses the reference of in_layer
            (str/obj).

        - sr_format (optional):
            Format of spatial_ref. Valid formats are osr (default), wkt, proj4,
            url, esri, epsg, epsga, pci, usgs, xml, erm (str).

    """

    layer = FeatureLayer(in_ds, fields, clause, intersects, in_layer)
    layer.union(op_ds, out_ds, op_layer, out_layer, out_driver,
                spatial_ref, sr_format)
    layer.close()


def update(in_ds, op_ds, out_ds, fields='*', clause=None, intersects=None,
           in_layer=None, op_layer=None, out_layer=None, out_driver=None,
           spatial_ref=None, sr_format='osr'):
    """
    Perform an update operation between two layers.

    Parameters:

        - in_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the focal layer (str).

        - op_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the operation layer (str).

        - out_ds:
            File system path to an OGR-readable data source, or a database
            connection string, for the output layer (str).

        - fields (optional):
            Filter to select the fields to use from in_layer. The default
            value of "*" will include all fields. Single fields are passed as
            strings, or multiple fields with a collection (str/list/tuple).

        - clause (optional):
            Set a OGR-SQL clause to filter the layer features by field
            attributes. See http://www.gdal.org/ogr_sql.html (str).

        - intersects (optional):
            Filter results by bounding box, from an OGR Geometry, easyOGR
            Feature, or a bounding box tuple in the format (minx, miny, maxx,
            maxy) (tuple).

        - in_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - op_layer (optional):
            Name of the in_ds layer to open. Not required for single-layer data
            sources (e.g. Shapefile) (str).

        - out_layer (optional):
            Name of the in_ds layer to create. Not required for single-layer
            data sources (e.g. Shapefile) (str).

        - out_driver (optional):
            Specify the OGR driver to use for the output, in OGR string format.
            or an OGR Driver instance. This is not necessarily required where
            out_ds has a standard file extension .e.g '.shp' (str/ogr.Driver).

        - spatial_ref (optional):
            Spatial reference to use for projecting the Features. Input must be
            valid for sr_format. Default uses the reference of in_layer
            (str/obj).

        - sr_format (optional):
            Format of spatial_ref. Valid formats are osr (default), wkt, proj4,
            url, esri, epsg, epsga, pci, usgs, xml, erm (str).

    """

    layer = FeatureLayer(in_ds, fields, clause, intersects, in_layer)
    layer.update(op_ds, out_ds, op_layer, out_layer, out_driver,
                 spatial_ref, sr_format)
    layer.close()


class Dataset(object):
    """
    Provides a read/write interface to the ogr DataSource and Layer classes.
    Inherited by the FeatureGenerator and FeatureLayer classes, and used for
    various functons to manipulate and access layers. Opening a layer will set
    it as the active layer, making it available for geoprocessing.

    Methods:

        - close:
            Closes both the active layer, and the OGR DataSource. Once called,
            the instance or any OGR objects belonging to it can no longer be
            used.

        - spatial_ref:
            Converts the active Layer spatial reference to another format.

    Attributes:

        - bbox:
            Bounding box extent coordinates for the active layer, interleaved
            as xmin, ymin, xmax, ymax (tuple).

        - driver:
            Name of the driver used to open the datasource (str).

        - features:
            The number of available features in the active layer (int).

        - fids:
            Flag for if the active layer has an FID column (bool).

        - field_definitions:
            OrderedDict containing field attributes for the active layer (obj).

        - fields:
            Names of the fields present in the active layer (tuple).

        - geometry_type:
            OGR name for the active layer geometry type (str).

        - layers:
            Names of all layers present in the current Dataset, ordered by
            index (tuple).

        - name:
            The name of the active layer (str).

        - ogr_ds:
            The OGR DataSource object used for the Dataset. Available for
            convenience and compatibility with OGR, but may break the Dataset
            object if edited directly (obj).

        - osr_sr:
            The OSR SpatialReference object for the active layer. Set to None
            if no valid spatial reference is present (obj).

        - proj4:
            Proj4 representation of the spatial reference for the active layer.
            Set to None if no valid spatial reference is present (str).

        - srid:
            EPSG SRID code for the spatial reference for the active layer. Set
            to None if no valid spatial reference is present, or if OSR cannot
            convert it to SRID (int).

        - status:
            Status of the Dataset active layer, Closed or Open (str).

        - units:
            Linear units for the spatial reference. Set to None if no valid
            spatial reference is present (str).

        - wkt:
            Well known text string representation of the spatial reference. Set
            to None if no valid spatial reference is present (str).

    """

    def __init__(self, datasource, driver=None, mode="r"):
        """
        Provides a read/write interface to the ogr DataSource and Layer
        classes. Inherited by the FeatureGenerator and FeatureLayer classes,
        and used for various functons to manipulate and access layers. Opening
        a layer will set it as the active layer, making it available for
        geoprocessing.

        Parameters:

            - datasource:
                File system path to an OGR-readable data source, or a database
                connection string (str).

            - driver (optional):
                Name of the driver to use, in OGR format (str). If not
                supplied, this will be determined from the file extension, or
                by attempting all drivers (str).

            - mode (optional):
                Set "r" for read only, or "rw" for read/write. OGR 0/1 is also
                accepted. Read only is default (int/str).

        """

        # Open the input datasource.
        self.status = "Closed"
        driver, self.ogr_ds = open_ds(datasource, driver, False, mode)
        self.driver = driver.GetName()
        layers = []
        for i in range(self.ogr_ds.GetLayerCount()):
            layers.append(self.ogr_ds.GetLayerByIndex(i).GetName())
        self.layers = tuple(layers)
        self.ogr_layer = None
        self._set_attributes()

    def __enter__(self):
        return self

    def __exit__(self, exc, value, traceback):
        self.close()

    def __iter__(self):
        return self._cursor()

    def __len__(self):
        return self.features

    def __getitem__(self, index):
        feature = self.ogr_layer.GetFeature(index)
        return ogr_to_feature(feature, self.fields)

    def _close_layer(self):
        """
        Closes the current active layer. Should not be called directly, used by
        class methods to control layer io. Once called, another layer can be
        set as the active layer with _open_layer.

        """

        if self.status == "Open":
            self.ogr_ds.ReleaseResultSet(self.ogr_layer)
            self.ogr_layer = None
            self._selection = None

    def _cursor(self):
        """
        Generator function yielding Features from the current active layer. If
        a selection is set, reads only the features matching those fids.
        Otherwise, reads from all layer features.

        """

        if self.status == "Open":
            if self._selection is not None:
                fids = self._selection
            else:
                fids = xrange(self.features)
            for fid in fids:
                feature = self.ogr_layer.GetFeature(fid)
                yield ogr_to_feature(feature, self.fields)

    def _open_layer(self, layer=0, fields="*", clause=None, intersects=None):
        """
        Sets an active layer. Should not be called directly, used by class
        methods to control layer io. The Arguments filter the resulting layer
        records, which cannot then be changed without closing the layer and
        opening a new instance.

        Parameters:

            - layer (optional):
                Name or index of the layer to open. Not required for single
                layer datasources e.g. Shapefile (int/str).

            - fields (optional):
                The fields to include in the opened layer. Set a string for a
                single field, or a collection for multiple fields. The default
                value of "*" includes all fields. Cannot be used to drop all
                fields at present (str/list/tuple).

            - clause (optional):
                Set a OGR-SQL where clause to filter the layer features by
                field attributes. See http://www.gdal.org/ogr_sql.html (str).

            - intersects (optional):
                Filter results by bounding box, from an OGR Geometry, easyOGR
                Feature, or a bounding box tuple in the format (minx, miny,
                maxx, maxy) (list/tuple/ogr.Geometry/Feature).

        """

        # Close any existing layer.
        if self.status == "Open":
            self._close_layer()

        # If a suitable fields parameter is passed, adjust for sql query.
        if type(fields) in (list, tuple, set):
            fields = ", ".join(fields)
        elif type(fields) not in (str, unicode):
            print "\nUnsuitable type given for fields parameter."
            raise TypeError()

        # Build basic select SQL query for layer and fields.
        if type(layer) == int:
            layer = self.layers[layer]
        sql = 'SELECT {0} FROM "{1}"'.format(fields, layer)

        # If a where clause is provided, add to SQL query.
        if clause is not None:
            try:
                sql += "\nWHERE {0}".format(clause)
            except:
                print "\nUnsuitable type given for clause parameter."
                raise TypeError()

        # If an intersection extent or Feature is given, adjust parameter.
        if intersects is not None and not isinstance(intersects,
                                                     ogr.Geometry):
            if type(intersects) in (list, tuple, set):
                intersects = extent_to_polygon(*intersects)
            elif isinstance(intersects, Feature):
                intersects = intersects.ogr_geom
            else:
                print "\nUnsuitable type given for intersects parameter."
                raise TypeError()

        # Open OGR layer with query.
        try:
            self.ogr_layer = self.ogr_ds.ExecuteSQL(sql, intersects)
        except:
            print ("\nLayer SQL failed, check fields, clause, and " +
                   "intersects arguments.")
            raise Exception()
        self.status = "Open"
        self._set_attributes()

    def _set_attributes(self):
        """
        Sets the object attributes from the active layer, if there is one.

        """

        if self.ogr_layer is None:

            # Set null layer attributes.
            self.field_definitions = OrderedDict()
            self.geometry_type = None
            self.features = 0
            self.fields = None
            self.bbox = None
            self.fids = False
            self.name = None

        else:

            # Get attributes of layer fields.
            self.field_definitions = OrderedDict()
            desc = self.ogr_layer.GetLayerDefn()
            for field in xrange(desc.GetFieldCount()):
                field = desc.GetFieldDefn(field)
                properties = (field.type, field.width, field.precision)
                self.field_definitions[field.name] = properties
            self.fields = tuple(self.field_definitions.keys())

            # Geometry type.
            self.geometry_type = geom_types[desc.GetGeomType()]

            # Count features.
            self.features = self.ogr_layer.GetFeatureCount()

            # Get input layer bounding box.
            minx, maxx, miny, maxy = self.ogr_layer.GetExtent()
            self.bbox = (minx, miny, maxx, maxy)

            # Set FIDs flag.
            if self.ogr_layer.GetFIDColumn():
                self.fids = True
            else:
                self.fids = False

            # Set name.
            self.name = self.ogr_layer.GetName()

        # Set spatial reference.
        self._set_sr()

        # FID selection for layer (used for FeatureLayer).
        self._selection = None

    def _set_sr(self, spatial_ref=None):
        """
        Sets the spatial reference attributes of the layer.

        Parameters:

            - spatial_ref (optional):
                The OSR spatial reference object to apply. If set to None, this
                is set from the active layer, should there be one. If no valid
                spatial reference is present, all attributes are set to None
                (osr.SpatialReference).

        """

        # If not specified, extract spatial reference from active layer.
        if spatial_ref is None and self.status == "Open":
            spatial_ref = self.ogr_layer.GetSpatialRef()

        # If still None, set all spatial reference attributes to None.
        if spatial_ref is None:
            self.units = None
            self.wkt = None
            self.proj4 = None
            self.srid = None

        # If a spatial reference instance is present, set attributes from that.
        else:
            self.units = spatial_ref.GetLinearUnitsName()
            self.wkt = spatial_ref.ExportToPrettyWkt()
            self.proj4 = spatial_ref.ExportToProj4()
            self.srid = spatial_ref.GetAttrValue("AUTHORITY", 1)

        # Set spatial reference for the dataset.
        self.osr_sr = spatial_ref

    def close(self):
        """
        Closes both the active layer, and the OGR DataSource. Once called, the
        instance or any OGR objects belonging to it can no longer be used.

        """

        self._close_layer()
        self.ogr_ds = None


class FeatureGenerator(Dataset):
    """
    Opens a read only layer view on an OGR data source. Yields Feature objects,
    and will remain open until all Features are generated, or the close method
    is called, unless set using the with context. Methods adjust the cursor to
    filter and modify generated outputs. The order methods are called is
    important to improve processing speed e.g. filtering records before
    applying geoprocessing operations.

    Methods:

        - add_field:
            Add a new field to the yielded Features. This does not affect the
            source layer.

        - attribute_filter:
            Filter the Features by field attributes.

        - buffer:
            Apply a geometric buffer to each Feature.

        - calculate_field:
            Set a value for a given field. Currently limited to a single value
            for all selected features.

        - close:
            Closes both the active layer, and the OGR DataSource. Once called,
            the instance or any OGR objects belonging to it can no longer be
            used.

        - contains:
            Filter the Features by contains spatial query.

        - crosses:
            Filter the Features by crosses spatial query.

        - difference:
            Filter the Features by difference spatial query.

        - disjoint:
            Filter the Features by disjoint spatial query.

        - drop_fields:
            Remove fields from the yielded Features. This does not affect the
            source layer.

        - equals:
            Filter the Features by equals spatial query.

        - export:
            Export the current cursor to file, emptying and closing the object.

        - intersection:
            Apply an intersection between the Features with another geometry.

        - intersects:
            Filter the Features by intersects spatial query.

        - next:
            Get next Feature.

        - overlaps:
            Filter the Features by overlaps spatial query.

        - project:
            Project the Features to a new coordinate system.

        - spatial_reference:
            Converts the active Layer spatial reference to another format.

        - touches:
            Filter the Features by touches spatial query.

        - transform:
            Transform the Features to another coordinate system.

        - union:
            Apply a geometric union of the Features with another geometry.

        - within:
            Filter the Features by within spatial query.

    Attributes:

        - bbox:
            Bounding box extent coordinates for the active layer, interleaved
            as xmin, ymin, xmax, ymax (tuple).

        - driver:
            Name of the driver used to open the datasource (str).

        - features:
            The number of available features in the active layer.  (int).

        - fids:
            Flag for if the active layer has an FID column (bool).

        - field_definitions:
            OrderedDict containing field attributes for the active layer (obj).

        - fields:
            Names of the fields present in the active layer (tuple).

        - geometry_type:
            OGR name for the active layer geometry type (str).

        - layers:
            Names of all layers present in the current Dataset, ordered by
            index (tuple).

        - name:
            The name of the active layer (str).

        - ogr_ds:
            The OGR DataSource object used for the Dataset. Available for
            convenience and compatibility with OGR, but may break the Dataset
            object if edited directly (obj).

        - osr_sr:
            The OSR SpatialReference object for the active layer. Set to None
            if no valid spatial reference is present (obj).

        - proj4:
            Proj4 representation of the spatial reference for the active layer.
            Set to None if no valid spatial reference is present (str).

        - srid:
            EPSG SRID code for the spatial reference for the active layer. Set
            to None if no valid spatial reference is present (int).

        - status:
            Status of the Dataset active layer, Closed or Open (str).

        - units:
            Linear units for the spatial reference. Set to None if no valid
            spatial reference is present (str).

        - wkt:
            Well known text string representation of the spatial reference. Set
            to None if no valid spatial reference is present (str).

    """

    def __init__(self, datasource, fields="*", clause=None, intersects=None,
                 layer=None, driver=None):
        """
        Opens a read only layer view on an OGR data source. Yields Feature
        objects, and will remain open until all Features are generated, or the
        close method is called, unless set using the with context. Methods
        adjust the cursor to filter and modify generated outputs. The order
        methods are called is important to improve processing speed e.g.
        filtering records before applying geoprocessing operations.

        Parameters:

            - datasource:
                File system path to an OGR-readable data source, or a database
                connection string (str).

            - fields (optional):
                Filter to select the fields to generate. The default value of
                "*" will include all fields. Single fields are passed as
                strings, or multiple fields with a collection (str/list/tuple).

            - clause (optional):
                Set a OGR-SQL clause to filter the layer features by field
                attributes. See http://www.gdal.org/ogr_sql.html (str).

            - intersects (optional):
                Filter results by bounding box, from an OGR Geometry, easyOGR
                Feature, or a bounding box tuple in the format (minx, miny,
                maxx, maxy) (tuple).

            - layer (optional):
                Specify the data source layer to open, by name or index. Not
                required for single-layer data sources (e.g. Shapefile), or
                where the full layer path is given by the datasource parameter
                (str/int).

            - driver (optional):
                Specify the OGR driver to use, in OGR string format. This is
                not necessarily required, as OGR can find the correct driver
                with ogr.Open, but may speed up opening layers a little (str).

        """

        # Open datasource and layer.
        if layer is None:
            layer = get_layer(datasource)
        super(FeatureGenerator, self).__init__(datasource, driver)
        self._open_layer(layer, fields, clause, intersects)

        # Open cursor.
        self.__cursor = self._cursor()

    def __iter__(self):
        return self

    def add_field(self, field_name, field_type, precision=None, width=None,
                  value=None):
        """
        Add a new field to the yielded Features. This does not affect the
        source layer.

        Parameters:

            - field_name:
                Name for the field to add (str).

            - field_type:
                OGR-type for field. Options are: Integer, IntegerList, Real,
                RealList, String, StringList, WideString, WideStringList,
                Binary, Date, Time, DateTime (str).

            - precision (optional):
                Precision value for field (int).

            - width (optional):
                Width value for field (int).

            - value (optional):
                Default value to set for field.

        """

        fields = list(self.fields)
        fields.append(field_name)
        self.fields = tuple(fields)
        self.field_definitions[field_name] = [field_type, precision, width]
        self.__cursor = add_attribute(self.__cursor, value)

    def attribute_filter(self, clause):
        """
        Filter the Features by field attributes.

        Parameters:

            - clause:
                Query string to apply to the Features. Input must be valid
                Python, using unquoted field names and field values as they
                would be defined in Python, e.g. field_1 >= 1 or field_2 == "A"
                (str).

        """

        query = Query(self.fields, clause)
        self.__cursor = (i for i in self.__cursor if query.test(i.attributes))

    def buffer(self, distance):
        """
        Apply a geometric buffer to each Feature.

        Parameters:

            - distance:
                Buffer distance to apply, measured in the units of the spatial
                reference (int/float).

        """

        self.__cursor = map_geom(Feature.buffer, self.__cursor, distance)

    def calculate_field(self, field, value=None, clause=None):
        """
        Set a value for a given field. Currently limited to a single value for
        all selected features.

        Parameters:

            - field:
                Field name to edit (str).

            - value (optional):
                Value to set for the field.

            - clause (optional):
                Query string to apply to the Features. Input must be valid
                Python, using unquoted field names and field values as they
                would be defined in Python, e.g. field_1 >= 1 or field_2 == "A"
                (str).

        """

        self.__cursor = update_attributes(self.__cursor, field, value,
                                          self.fields, clause)

    def contains(self, feature):
        """
        Filter the Features by contains spatial query.

        Parameters:

            - feature:
                Geometry to query. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        clause = Feature.contains
        self.__cursor = spatial_query(clause, self.__cursor, feature)

    def crosses(self, feature):
        """
        Filter the Features by crosses spatial query.

        Parameters:

            - feature:
                Geometry to query. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        clause = Feature.crosses
        self.__cursor = spatial_query(clause, self.__cursor, feature)

    def difference(self, feature):
        """
        Calculate the difference between the Features and another geometry.

        Parameters:

            - feature:
                Geometry to apply. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        self.__cursor = map_geom(Feature.difference, self.__cursor, feature)

    def disjoint(self, feature):
        """
        Filter the Features by disjoint spatial query.

        Parameters:

            - feature:
                Geometry to query. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        clause = Feature.disjoint
        self.__cursor = spatial_query(clause, self.__cursor, feature)

    def drop_fields(self, *drop_fields):
        """
        Remove fields from the yielded Features. This does not affect the
        source layer.

        Parameters:

            - drop_fields:
                The field names to remove (str).

        """

        filters = [f.lower() for f in self.fields]
        fields = list(self.fields)
        indicies = []
        for field in drop_fields:
            index = filters.index(field.lower())
            actual = self.fields[index]
            fields.remove(actual)
            indicies.append(index)
        self.fields = tuple(fields)
        del self.field_definitions[field]

    def equals(self, feature):
        """
        Filter the Features by equals spatial query.

        Parameters:

            - feature:
                Geometry to query. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        clause = Feature.equals
        self.__cursor = spatial_query(clause, self.__cursor, feature)

    def export(self, out_file, out_layer=None, driver=None):
        """
        Export the current cursor to file, emptying and closing the object.

        Parameters:

            - out_file:
                File path for the output layer (str).

            - out_layer (optional):
                Name to give the layer, if not already included in out_file.
                Not required for single-layer data sources (str).

            - driver (optional):
                Name of the driver to use for writing the file (str).

        """

        out_ds, out_layer = create_layer(out_file, self.field_definitions,
                                         self.ogr_layer.GetGeomType(),
                                         self.fields, self, self.osr_sr,
                                         out_layer, driver)
        out_layer = None
        out_ds = None

    def intersects(self, feature):
        """
        Filter the Features by intersects spatial query.

        Parameters:

            - feature:
                Geometry to query. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        clause = Feature.intersects
        self.__cursor = spatial_query(clause, self.__cursor, feature)

    def intersection(self, feature):
        """
        Apply an intersection between the Features with another geometry.

        Parameters:

            - feature:
                Geometry to apply. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        self.__cursor = map_geom(Feature.intersection, self.__cursor, feature)

    def next(self):
        """
        Get next Feature.

        """

        try:
            return self.__cursor.next()
        except StopIteration:
            self.close()
            raise StopIteration

    def overlaps(self, feature):
        """
        Filter the Features by overlaps spatial query.

        Parameters:

            - feature:
                Geometry to query. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        clause = Feature.overlaps
        self.__cursor = spatial_query(clause, self.__cursor, feature)

    def project(self, spatial_ref, sr_format='osr'):
        """
        Project the Features to a new coordinate system.

        Parameters:

            - spatial_ref:
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format.

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default),
                wkt, proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        """

        if not isinstance(spatial_ref, osr.SpatialReference):
            new_sr = osr.SpatialReference()
            import_sr[sr_format](new_sr, spatial_ref)
            spatial_ref = new_sr
        self._set_sr(spatial_ref)
        self.__cursor = update_feature(Feature.project, self.__cursor,
                                       spatial_ref)

    def spatial_reference(self, sr_format='osr'):
        """
        Converts the active Layer spatial reference to another format.

        Parameters:

            - sr_format (optional):
                Format of spatial_reference. Valid formats are osr (default),
                wkt, proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        Returns:

            - sr:
                Converted spatial reference, or None if not present (obj).

        """

        sr = self.osr_sr
        if sr:
            if sr_format != 'osr':
                sr = export_sr[sr_format](sr)
            return sr
        else:
            return None

    def transform(self, spatial_ref, sr_format='osr'):
        """
        Transform the Features to another coordinate system.

        Parameters:

            - spatial_ref:
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format.

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default),
                wkt, proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        """

        if not isinstance(spatial_ref, osr.SpatialReference):
            new_sr = osr.SpatialReference()
            import_sr[sr_format](new_sr, spatial_ref)
            spatial_ref = new_sr
        if self.osr_sr:
            transform = osr.CoordinateTransformation(self.osr_sr,
                                                     spatial_ref)
            self.__cursor = update_feature(Feature.transform, self.__cursor,
                                           transform)
            self._set_sr(spatial_ref)
        else:
            self.project(spatial_ref)

    def touches(self, feature):
        """
        Filter the Features by touches spatial query.

        Parameters:

            - feature:
                Geometry to query. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        clause = Feature.touches
        self.__cursor = spatial_query(clause, self.__cursor, feature)

    def within(self, feature):
        """
        Filter the Features by within spatial query.

        Parameters:

            - feature:
                Geometry to query. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        clause = Feature.within
        self.__cursor = spatial_query(clause, self.__cursor, feature)

    def union(self, feature):
        """
        Apply a geometric union of the Features with another geometry.

        Parameters:

            - feature:
                Geometry to apply. Valid inputs are Feature, FeatureLayer,
                FeatureGenerator, ogr.Feature, ogr.Geometry, or a list of
                Features (obj).

        """

        self.__cursor = map_geom(Feature.union, self.__cursor, feature)


class FeatureLayer(Dataset):
    """
    Opens a read only layer view on an OGR data source, and will remain open
    until the close method is called, unless set using the with context.
    Methods apply selections to the layer, and run geoprocessing operations.
    fields, clause and intertsects filters set on init cannot be cleared once
    set, but feature selections can.

    Methods:

        - attribute_filter:
            Select Layer features by attribute.

        - buffer:
            Apply a geometric buffer to the Layer.

        - clear_selection:
            Clear any active selection.

        - close:
            Closes both the active layer, and the OGR DataSource. Once called,
            the instance or any OGR objects belonging to it can no longer be
            used.

        - difference:
            Calculate the difference between the Layer and another.

        - erase:
            Execute an erase operation between the Layer and another.

        - export:
            Export the layer to an output file.

        - identity:
            Execute an identity operation between the Layer and another.

        - intersection:
            Execute an intersection operation between the Layer and another.

        - project:
            Projects the Layer to another spatial reference.

        - spatial_reference:
            Converts the active Layer spatial reference to another format.

        - transform:
            Transform the Layer to another spatial reference.

        - union:
            Execute a union operation between the Layer and another.

        - update:
            Execute an update operation between the Layer and another.

    Attributes:

        - bbox:
            Bounding box extent coordinates for the active layer, interleaved
            as xmin, ymin, xmax, ymax (tuple).

        - driver:
            Name of the driver used to open the datasource (str).

        - features:
            The number of available features in the active layer.  (int).

        - field_definitions:
            OrderedDict containing field attributes for the active layer (obj).

        - fields:
            Names of the fields present in the active layer (tuple).

        - fids:
            Flag for if the active layer has an FID column (bool).

        - geometry_type:
            OGR name for the active layer geometry type (str).

        - layers:
            Names of all layers present in the current Dataset, ordered by
            index (tuple).

        - name:
            The name of the active layer (str).

        - ogr_ds:
            The OGR DataSource object used for the Dataset. Available for
            convenience and compatibility with OGR, but may break the Dataset
            object if edited directly (obj).

        - osr_sr:
            The OSR SpatialReference object for the active layer. Set to None
            if no valid spatial reference is present (obj).

        - proj4:
            Proj4 representation of the spatial reference for the active layer.
            Set to None if no valid spatial reference is present (str).

        - srid:
            EPSG SRID code for the spatial reference for the active layer. Set
            to None if no valid spatial reference is present (int).

        - status:
            Status of the Dataset active layer, Closed or Open (str).

        - units:
            Linear units for the spatial reference. Set to None if no valid
            spatial reference is present (str).

        - wkt:
            Well known text string representation of the spatial reference. Set
            to None if no valid spatial reference is present (str).

    """

    def __init__(self, datasource, fields="*", clause=None, intersects=None,
                 layer=None, driver=None):
        """
        Opens a read only layer view on an OGR data source, and will remain
        open until the close method is called, unless set using the with
        context. Methods apply selections to the layer, and run geoprocessing
        operations. fields, clause and intertsects filters set on init cannot
        be cleared once set, but feature selections can.

        Parameters:

            - datasource:
                File system path to an OGR-readable data source, or a database
                connection string (str).

            - fields (optional):
                Filter to select the fields to generate. The default value of
                "*" will include all fields. Single fields are passed as
                strings, or multiple fields with a collection (str/list/tuple).

            - clause (optional):
                Set a OGR-SQL clause to filter the layer features by field
                attributes. See http://www.gdal.org/ogr_sql.html (str).

            - intersects (optional):
                Filter results by bounding box, from an OGR Geometry, easyOGR
                Feature, or a bounding box tuple in the format (minx, miny,
                maxx, maxy) (tuple).

            - layer (optional):
                Specify the data source layer to open, by name or index. Not
                required for single-layer data sources (e.g. Shapefile), or
                where the full layer path is given by the datasource parameter
                (str/int).

            - driver (optional):
                Specify the OGR driver to use, in OGR string format. This is
                not necessarily required, as OGR can find the correct driver
                with ogr.Open, but may speed up opening layers a little (str).

        """

        # Open datasource and layer.
        if layer is None:
            layer = get_layer(datasource)
        super(FeatureLayer, self).__init__(datasource, driver)
        self._open_layer(layer, fields, clause, intersects)

    def _spatial_op(self, operation, out_ds, op_ds=None, out_layer=None,
                    op_layer=None, out_driver=None, spatial_ref=None,
                    sr_format='osr', arguments=[], cursor=False):

        """
        Executes a spatial operation of the layer or its features, writing the
        output to file.

        Parameters:

            - operation:
                The ogr.Layer or Feature method to execute (func).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - op_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the operation layer (str).

            - op_layer (optional):
                Name of the in_ds layer to open. Not required for single-layer
                data sources (e.g. Shapefile) (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

            - spatial_ref (optional):
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

            - arguments (optional):
                Further arguments to pass to the spatial operation (list).

            - cursor (optional):
                If a Feature level operation is to be applied, open a cursor to
                generate Features (bool).

        """

        # Apply fid selection.
        if self._selection:
            self.ogr_layer.SetAttributeFilter("FID IN {0}".format(
                                              tuple(self._selection)))

        # Open op_layer, if required.
        if op_ds is not None:
            op_ds, op_layer = format_layer(op_ds, op_layer)

        # Get layer attributes for output.
        if spatial_ref is None:
            spatial_ref = self.osr_sr
        elif sr_format != 'osr':
            new_sr = osr.SpatialReference()
            import_sr[sr_format](new_sr, spatial_ref)
            spatial_ref = new_sr
        defn = self.ogr_layer.GetLayerDefn()
        geom = self.ogr_layer.GetGeomType()

        # Generate Features.
        if cursor:
            features = self._cursor()

            # Execute operation on Features.
            if op_layer is None:
                features = (operation(feature, *arguments) for
                            feature in features)
            else:
                features = (operation(feature, op_layer, *arguments) for
                            feature in features)

            # Write results to out_layer.
            if isinstance(out_layer, ogr.Layer):
                for feature in features:
                    feature = create_ogr_feature(defn, feature.ogr_geom,
                                                 feature.attributes,
                                                 self.fields)
                    out_layer.CreateFeature(feature)
            else:
                out_ds, out_layer = create_layer(out_ds, defn, geom,
                                                 self.fields, features,
                                                 spatial_ref=spatial_ref,
                                                 layer=out_layer,
                                                 driver=out_driver)

        # Use instance layer.
        else:
            in_layer = self.ogr_layer

            # Create a new empty layer.
            if not isinstance(out_layer, ogr.Layer):
                out_ds, out_layer = create_layer(out_ds, defn, geom,
                                                 self.fields,
                                                 spatial_ref=spatial_ref,
                                                 layer=out_layer,
                                                 driver=out_driver)

            # Execute operation on layer.
            if op_layer is None:
                operation(in_layer, out_layer, *arguments)
            else:
                operation(in_layer, op_layer, out_layer, *arguments)

        # Close layers.
        out_layer = None
        op_layer = None
        out_ds = None
        op_ds = None
        self.ogr_layer.SetAttributeFilter("")

    def attribute_filter(self, clause, selection="NEW"):
        """
        Select Layer features by attribute.

        Parameters:

            - clause:
                Query string to apply to the Features. Input must be valid
                Python, using unquoted field names and field values as they
                would be defined in Python, e.g. field_1 >= 1 or field_2 == "A"
                (str).

            - selection (optional):
                The selection method to apply. Options are "NEW" (default),
                "INTERSECTION", "UNION", "DIFFERENCE" (str).

        """

        # Initiate Query instance.
        query = Query(self.fields, clause)
        selection = selection.upper()

        # If using a new selection, clear and add all fids passing the test.
        if self._selection is None or selection == "NEW":
            self._selection = set()
            for fid in xrange(self.features):
                feature = self.ogr_layer.GetNextFeature()
                attributes = []
                for field in self.fields:
                    attributes.append(feature.GetField(field))
                if query.test(attributes):
                    if self.fids:
                        fid = feature.GetFID()
                    self._selection.add(fid)

        # Remove any previously selected fids that do not pass the test.
        elif selection == "INTERSECTION":
            for fid in self._selection:
                feature = self.ogr_layer.GetFeature(fid)
                attributes = []
                for field in self.fields:
                    attributes.append(feature.GetField(field))
                if not query.test(attributes):
                    self._selection.remove(fid)

        # Append fids passing the test to the selection.
        elif selection == "UNION":
            for fid in xrange(self.features):
                feature = self.ogr_layer.GetNextFeature()
                if self.fids:
                    fid = feature.GetFID()
                if fid not in self._selection:
                    attributes = []
                    for field in self.fields:
                        attributes.append(feature.GetField(field))
                    if query.test(attributes):
                        self._selection.add(fid)

        # Set fids different to the current selection.
        elif selection == "DIFFERENCE":
            for fid in self._selection:
                feature = self.ogr_layer.GetFeature(fid)
                attributes = []
                for field in self.fields:
                    attributes.append(feature.GetField(field))
                if query.test(attributes):
                    self._selection.remove(fid)

        # Recalculate feature count.
        self.features = len(self._selection)

    def buffer(self, buffer_dist, out_ds, out_layer=None, out_driver=None,
               spatial_ref=None, sr_format='osr'):
        """
        Apply a geometric buffer to the Layer.

        Parameters:

            - buffer_dist:
                The buffer distance to apply to each Feature (float/int).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

            - spatial_ref (optional):
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        """

        operation = Feature.buffer
        self._spatial_op(operation, out_ds, out_layer=out_layer,
                         spatial_ref=spatial_ref, sr_format=sr_format,
                         arguments=[buffer_dist], cursor=True)

    def clear_selection(self):
        """
        Clear selected features.

        """

        self._selection = set()
        self.features = self.ogr_layer.GetFeatureCount()

    def difference(self, op_ds, out_ds, op_layer=None, out_layer=None,
                   out_driver=None, spatial_ref=None, sr_format='osr'):
        """
        Calculate the difference between the Layer and another.

        Parameters:

            - op_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the operation layer (str).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - op_layer (optional):
                Name of the op_ds layer to open. Not required for single-layer
                data sources (e.g. Shapefile) (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

            - spatial_ref (optional):
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        """

        operation = ogr.Layer.SymDifference
        self._spatial_op(operation, out_ds, op_ds, out_layer, op_layer,
                         out_driver, spatial_ref, sr_format)

    def erase(self, op_ds, out_ds, op_layer=None, out_layer=None,
              out_driver=None, spatial_ref=None, sr_format='osr'):
        """
        Execute an erase operation between the Layer and another.

        Parameters:

            - op_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the operation layer (str).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - op_layer (optional):
                Name of the op_ds layer to open. Not required for single-layer
                data sources (e.g. Shapefile) (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

            - spatial_ref (optional):
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        """

        operation = ogr.Layer.Erase
        self._spatial_op(operation, out_ds, op_ds, out_layer, op_layer,
                         out_driver, spatial_ref, sr_format)

    def export(self, out_ds, out_layer=None, driver=None):
        """
        Export the layer to an output file.

        Parameters:

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string (str).

            - out_layer (optional):
                Name, or index for the layer to create, if not included in the
                out_file argument (str/int).

            - driver (optional):
                Name of the driver used to open the datasource (str).

        """

        out_ds, layer = create_layer(out_ds, self.field_definitions,
                                     self.ogr_layer.GetGeomType(), self.fields,
                                     self._cursor(), self.osr_sr, out_layer,
                                     driver)
        layer = None
        out_ds = None

    def identity(self, op_ds, out_ds, op_layer=None, out_layer=None,
                 out_driver=None, spatial_ref=None, sr_format='osr'):
        """
        Execute an identity operation between the Layer and another.

        Parameters:

            - op_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the operation layer (str).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - op_layer (optional):
                Name of the op_ds layer to open. Not required for single-layer
                data sources (e.g. Shapefile) (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

            - spatial_ref (optional):
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        """

        operation = ogr.Layer.Identity
        self._spatial_op(operation, out_ds, op_ds, out_layer, op_layer,
                         out_driver, spatial_ref, sr_format)

    def intersection(self, op_ds, out_ds, op_layer=None, out_layer=None,
                     out_driver=None, spatial_ref=None, sr_format='osr'):
        """
        Execute an intersection operation between the Layer and another.

        Parameters:

            - op_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the operation layer (str).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - op_layer (optional):
                Name of the op_ds layer to open. Not required for single-layer
                data sources (e.g. Shapefile) (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

            - spatial_ref (optional):
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        """

        operation = ogr.Layer.Intersection
        self._spatial_op(operation, out_ds, op_ds, out_layer, op_layer,
                         out_driver, spatial_ref, sr_format)

    def project(self, spatial_ref, out_ds, sr_format='osr',
                out_layer=None, out_driver=None):
        """
        Projects the Layer to another spatial reference.

        Parameters:

            - spatial_ref:
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

        """

        if not isinstance(spatial_ref, osr.SpatialReference):
            new_sr = osr.SpatialReference()
            import_sr[sr_format](new_sr, spatial_ref)
            spatial_ref = new_sr
        operation = Feature.project
        self._spatial_op(operation, out_ds, out_layer=out_layer,
                         out_driver=out_driver,
                         spatial_ref=spatial_ref,
                         arguments=[spatial_ref, 'osr', False],
                         cursor=True)

    def spatial_filter(self, feature, clause="INTERSECTS", selection="NEW"):
        """
        Select Layer features by spatial relationship with another feature.

        Parameters:

            - feature:
                The feature to use for the query (obj).

            - clause:
                Query string to apply to the Features. Input must be valid
                Python, using unquoted field names and field values as they
                would be defined in Python, e.g. field_1 >= 1 or field_2 == "A"
                (str).

            - selection (optional):
                The selection method to apply. Options are "NEW" (default),
                "INTERSECTION", "UNION", "DIFFERENCE" (str).

        """

        geom = format_geom(feature)
        selection = spatial_queries[clause.upper()]

        # If using a new selection, clear and add all fids passing the test.
        if self._selection is None or selection == "NEW":
            self._selection = set()
            for fid in xrange(self.features):
                feature = self.ogr_layer.GetNextFeature()
                if selection(feature.GetGeometryRef(), geom):
                    if self.fids:
                        fid = feature.GetFID()
                    self._selection.add(fid)

        # Remove any previously selected fids that do not pass the test.
        elif selection == "INTERSECTION":
            for fid in self._selection:
                feature = self.ogr_layer.GetFeature(fid)
                if not selection(feature.GetGeometryRef(), geom):
                    self._selection.remove(fid)

        # Append fids passing the test to the selection.
        elif selection == "UNION":
            for fid in xrange(self.features):
                feature = self.ogr_layer.GetFeature(fid)
                if self.fids:
                    fid = feature.GetFID()
                if fid not in self._selection:
                    if selection(feature.GetGeometryRef(), geom):
                        self._selection.add(fid)

        # Set fids different to the current selection.
        elif selection == "DIFFERENCE":
            for fid in self._selection:
                feature = self.ogr_layer.GetFeature(fid)
                if not selection(feature.GetGeometryRef(), geom):
                    self._selection.remove(fid)

        # Recalculate feature count.
        self.features = len(self._selection)

    def transform(self, spatial_ref, out_ds, sr_format='osr', out_layer=None,
                  out_driver=None):
        """
        Transform the Features to another coordinate system.

        Parameters:

            - spatial_ref:
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

        """

        if not isinstance(spatial_ref, osr.SpatialReference):
            new_sr = osr.SpatialReference()
            import_sr[sr_format](new_sr, spatial_ref)
            spatial_ref = new_sr
        if self.osr_sr:
            operation = Feature.transform
            transform = osr.CoordinateTransformation(self.osr_sr,
                                                     spatial_ref)
            self._spatial_op(operation, out_ds, out_layer=out_layer,
                             cursor=True, spatial_ref=spatial_ref,
                             arguments=[transform, 'osr', False])
        else:
            self.project(spatial_ref, out_ds, sr_format, out_layer, out_driver)

    def union(self, op_ds, out_ds, op_layer=None, out_layer=None,
              out_driver=None, spatial_ref=None, sr_format='osr'):
        """
        Execute a union operation between the Layer and another.

        Parameters:

            - op_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the operation layer (str).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - op_layer (optional):
                Name of the op_ds layer to open. Not required for single-layer
                data sources (e.g. Shapefile) (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

            - spatial_ref (optional):
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        """

        operation = ogr.Layer.Union
        self._spatial_op(operation, out_ds, op_ds, out_layer, op_layer,
                         out_driver, spatial_ref, sr_format)

    def update(self, op_ds, out_ds, op_layer=None, out_layer=None,
               out_driver=None, spatial_ref=None, sr_format='osr'):
        """
        Execute an update operation between the Layer and another.

        Parameters:

            - op_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the operation layer (str).

            - out_ds:
                File system path to an OGR-readable data source, or a database
                connection string, for the output layer (str).

            - op_layer (optional):
                Name of the op_ds layer to open. Not required for single-layer
                data sources (e.g. Shapefile) (str).

            - out_layer (optional):
                Name of the in_ds layer to create. Not required for
                single-layer data sources (e.g. Shapefile) (str).

            - out_driver (optional):
                Specify the OGR driver to use for the output, in OGR string
                format, or an OGR Driver instance. This is not necessarily
                required where out_ds has a standard file extension .e.g '.shp'
                (str/ogr.Driver).

            - spatial_ref (optional):
                Spatial reference to use for projecting the Features. Input
                must be valid for sr_format. Default uses the reference of
                ogr_layer (str/obj).

            - sr_format (optional):
                Format of spatial_ref. Valid formats are osr (default), wkt,
                proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).

        """

        operation = ogr.Layer.Update
        self._spatial_op(operation, out_ds, op_ds, out_layer, op_layer,
                         out_driver, spatial_ref, sr_format)
