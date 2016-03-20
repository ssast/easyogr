# feature.py
#
# by Shaun Astbury
#


# Import required modules.
try:
    from osgeo import ogr, osr
except:
    import ogr
    import osr
from core import (cascaded_union, create_ogr_feature, export_geometries,
                  export_sr, geom_dict, import_sr)


def format_geom(geom, geom_format='ogr'):
    """
    Extract an OGR geometry from a variety of inputs.
    
    Parameters:
    
        - geom:
            The input feature, geometry, or an iterable of either, including
            FeatureLayer and FeatureGenerator instances. If supplying a raw
            geometry e.g. wkt, this must match geom_format (obj/str).
    
        - geom_format (optional):
            The format of the input geom. Valid options are ogr (default), wkt,
            wkb, json, gml (str).
                
    Returns:
        
        - ogr_geom:
            The resultant OGR geometry (ogr.Geometry).
    
    """
    
    # If the input already contains an OGR geometry, extract this. If a Feature
    # instance is supplied, do not check validity, as this will already have
    # been checked.
    if isinstance(geom, Feature):
        ogr_geom = geom.ogr_geom
    else:
        if isinstance(geom, ogr.Feature):
            ogr_geom = geom.GetGeometryRef()
        elif isinstance(geom, ogr.Geometry):
            ogr_geom = geom

        # If a geom_format has been specified, convert to OGR.
        elif geom_format != 'ogr':
            ogr_geom = import_geometries[geom_format](geom)

        # If a list of geometries, or a FeatureLayer/Generator is supplied,
        # attempt a cascaded union of the geometries.
        elif hasattr(geom, '__iter__'):
            try:
                ogr_geom = cascaded_union(format_geom(i, geom_format)
                                          for i in geom)
            except:
                raise Exception('No suitable geometry provided for geom ' +
                                'parameter.')
        else:
            raise Exception('No suitable geometry provided for geom ' +
                            'parameter.')
            
        # If the geometry is invalid, attempt to fix it with a null buffer.
        if not ogr_geom.IsValid():
            ogr_geom = ogr_geom.Buffer(0)
    return ogr_geom


def ogr_to_feature(ogr_feat, fields='*'):
    """
    Create an EasyOGR Feature object from an OGR Feature.
    
    Parameters:
    
        - ogr_feat:
            The input OGR Feature instance to convert (ogr.Feature).
        
        - fields (optional):
            Fields to include in result Feature. Default of '*' returns all
            fields (str/list/tuple).
        
    Returns:
        
        - feature:
            The resultant Feature instance (Feature).
    
    """

    attributes = []
    if fields == '*':
        fields = range(ogr_feat.GetFieldCount())
    for field in fields:
        attributes.append(ogr_feat.GetField(field))
    geom = ogr_feat.GetGeomFieldRef(0)
    return Feature(geom, attributes)


def test_geom(func):
    """
    Decorator to test the output geometry of a Feature operation, checking it
    is not empty/null, and has a geometry type suitable for the input, matching
    the geometries of the input geometries to the result.

    Parameters:
    
        - self:
            The Feature instance (Feature).
    
        - op_geom:
            The input geometry used for the spatial operation.
        
        - geom_format (optional):
            The format of op_geom, OGR is default (str).
            
        - check_result (optinoal):
            Checks if the result is empty, or if the type doesn't match one of
            the inputs (e.g. producing a linestring from intersecting two
            polygons). Set to False to supress this (bool).
            
    """

    def inner(self, op_geom, geom_format='ogr', check_result=True):
        op_geom = format_geom(op_geom, geom_format)
        result = func(self, op_geom)
        if check_result and result is not None:
            if result.IsEmpty():
                result = None
            result_type = result.GetGeometryName()
            op_type = op_geom.GetGeometryName()
            if result_type != self.geometry_type and result_type != op_type:
                if self.geometry_type in geom_dict:
                    if all([geom_type != geom_dict[self.geometry_type],
                            geom_type != geom_dict[op_type]]):
                        result = None
        if result is not None:
            result = Feature(result, self.attributes)
        return result
    return inner


class Feature(object):
    """
    Will perform geometric tests and spatial operations with other Feature.
    All operations ignore spatial references and assume features exist in a
    flat, 2d plane. Working with Features from two different crs may produce
    unexpected results, although setting a spatial reference is not necessarily
    required if the coordinate values are correct.

    Methods:
            
        - buffer:
            Apply a geometric buffer to the Feature.

        - copy:
            Copy the Feature to a new object.
            
        - contains:
            Test the Feature by contains spatial query.
        
        - crosses:
            Test the Feature by crosses spatial query.
        
        - difference:
            Calculate the difference between the Feature and another geometry.
        
        - disjoint:
            Test the Feature by disjoint spatial query.
        
        - distance:
            Calculate the distance between the Feature and another.
        
        - equals:
            Test the Feature by equals spatial query.

        - export_geometry:
            Convert the Feature geometry to another format.

        - intersection:
            Apply an intersection between the Feature and another.
        
        - intersects:
            Test the Feature by intersects spatial query.
        
        - overlaps:
            Test the Feature by overlaps spatial query.
        
        - project:
            Project the Feature to a new coordinate system.
        
        - spatial_reference:
            Converts the Feature spatial reference to another format.
        
        - to_ogr_feature:
            Convert the Feature to an ogr.Feature object.
        
        - touches:
            Test the Feature by touches spatial query.
        
        - transform:
            Transform the Feature to another coordinate system.
        
        - union:
            Apply a geometric union of the Feature with another.
        
        - within:
            Test the Feature by within spatial query.

    Attributes:

        - area:
            Area of the Feature geometry, in spatial reference units (float).
    
        - attributes:
            Attributes assigned to the Feature (list).
    
        - bbox:
            Bounding box extent coordinates for the active layer, interleaved
            as xmin, ymin, xmax, ymax (tuple).

        - centroid:
            WKT-format Feature centroid coordinates (str).
            
        - geometry_type:
            OGR name for the active layer geometry type (str).

        - osr_sr:
            The OSR SpatialReference object for the active layer. Set to None
            if no valid spatial reference is present (obj).
            
        - proj4:
            Proj4 representation of the spatial reference for the active layer.
            Set to None if no valid spatial reference is present (str).

        - srid:
            EPSG SRID code for the spatial reference for the active layer. Set
            to None if no valid spatial reference is present (int).

        - units:
            Linear units for the spatial reference. Set to None if no valid
            spatial reference is present (str).

        - wkt:
            Well known text string representation of the spatial reference. Set
            to None if no valid spatial reference is present (str).

    """

    def __init__(self, geom, attributes=[], geom_format='ogr',
                 spatial_ref=None, ref_format='osr'):
        """
        Will perform geometric tests and spatial operations with other
        Feature. All operations ignore spatial references and assume features
        exist in a flat, 2d plane. Working with Features from two different crs
        may produce unexpected results, although setting a spatial reference
        is not necessarily required if the coordinate values are correct.

        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).

            - attributes:
                The attributes of the Feature (list).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                
            - spatial_ref (optional):
                Spatial reference for the Feature, which will transform the
                geometry, or project it if a spatial reference is not present.
                Input must be valid for sr_format. Alternatively, an
                osr.Transformation object can be used (str/obj).
                
            - sr_format (optional):
                Format of spatial_reference. Valid formats are osr (default),
                wkt, proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).
                
        """

        # Set instance attributes.
        self.ogr_geom = format_geom(geom, geom_format)
        self.attributes = list(attributes)
        self.geometry_type = self.ogr_geom.GetGeometryName()

        # Change spatial_ref, if required, and set spatial attributes.
        if spatial_ref:
            self.transform(spatial_ref, ref_format, True)
        else:
            self._set_sr()

    # Various special methods to make Feature similar to a container.
    def __contains__(self, value):
        return value in self.attributes

    def __delitem__(self, key):
        del self.attributes[key]

    def __getitem__(self, key):
        return self.attributes[key]

    def __len__(self):
        return len(self.attributes)

    def __setitem__(self, key, value):
        self.attributes[key] = value

    def __str__(self):
        return str(self.attributes)

    def _set_sr(self, spatial_ref=None):
        """
        Sets the spatial reference attributes of the Feature.

        Parameters:
            
            - spatial_ref (optional):
                The OSR spatial reference object to apply. If set to None, this
                is set from the active layer, should there be one. If no valid
                spatial reference is present, all attributes are set to None
                (osr.SpatialReference).

        """

        # If not specified, extract spatial reference from geometry.
        if spatial_ref is None:
            spatial_ref = self.ogr_geom.GetSpatialReference()
        
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

        # Set spatial reference.
        self.osr_sr = spatial_ref
        
        # Set other spatial attributes.
        minx, maxx, miny, maxy = self.ogr_geom.GetEnvelope()
        self.bbox = (minx, miny, maxx, maxy)
        self.centroid = export_geometries['wkt'](self.ogr_geom.Centroid())
        if self.geometry_type in ['POLYGON', 'MULTIPOLYGON']:
            self.area = self.ogr_geom.GetArea()
        else:
            self.area = 0

    def buffer(self, distance):
        """
        Apply a geometric buffer to the Feature.

        Parameters:
        
            - distance:
                Buffer distance to apply, measured in the units of the spatial
                reference (int/float).

        Returns:
        
            - feature:
                Resulting Feature object (obj).
                
        """
        
        return Feature(self.ogr_geom.Buffer(distance), self.attributes)

    def copy(self):
        """
        Copy the Feature to a new object.
        
        Returns:
        
            - feature:
                The copied Feature object (obj).
        
        """
        
        return Feature(self.ogr_geom.Clone(), self.attributes)

    def contains(self, geom, geom_format='ogr'):
        """
        Test the Feature by contains spatial query.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                
        Returns:
            
            - result:
                Result of the spatial query (bool).
        
        """

        geom = format_geom(geom, geom_format)
        return self.ogr_geom.Contains(geom)

    def crosses(self, geom, geom_format='ogr'):
        """
        Test the Feature by crosses spatial query.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                
        Returns:
            
            - result:
                Result of the spatial query (bool).

        """

        geom = format_geom(geom, geom_format)
        return self.ogr_geom.Crosses(geom)

    @test_geom
    def difference(self, geom, geom_format='ogr', check_result=True):
        """
        Calculate the difference between the Feature and another geometry.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).

            - check_result (optional):
                If True (default), use test_geom to check the result is of an
                appropriate geometry type. Otherwise, supress this and just
                return the result (bool).

        Returns:
        
            - feature:
                The resulting Feature object, or None if no geometry could be
                calculated (Feature).
                
        """
        
        return self.ogr_geom.Difference(geom)

    def disjoint(self, geom, geom_format='ogr'):
        """
        Test the Feature by disjoint spatial query.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                
        Returns:
            
            - result:
                Result of the spatial query (bool).

        """
        
        geom = format_geom(geom, geom_format)
        return self.ogr_geom.Disjoint(geom)

    def distance(self, geom, min=None, max=None, geom_format='ogr'):
        """
        Calculate the distance between the Feature and another.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - min (optional):
                The minimum distance to return (float/int).
            
            - max (optional):
                The maximum distance to return (float/int).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                   
        Returns:
            
            - result:
                The resulting distance (float/int)
        
        """
        
        geom = format_geom(geom, geom_format)
        result = self.ogr_geom.Distance(geom)
        if min is not None and result < min:
            result = None
        elif max is not None and result > min:
            result = None
        return result

    def equals(self, geom, geom_format='ogr'):
        """
        Test the Feature by equals spatial query.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                
        Returns:
            
            - result:
                Result of the spatial query (bool).

        """
        
        geom = format_geom(geom, geom_format)
        return self.ogr_geom.Equals(geom)

    def export_geometry(self, geom_format='ogr'):
        """
        Convert the Feature geometry to another format.
        
        Parameters:
        
            - geom_format (optional):
                The output format to create. Valid options are 'ogr' (default),
                'wkt', 'wkb', 'kml', 'json', 'gml' (str).
        
        Returns:
        
            - geom:
                The resulting geometry (str/obj).
        
        """
    
        if geom_format == 'ogr':
            return self.ogr_geom
        else:
            return export_geometries[geom_format.lower()](self.ogr_geom)

    @test_geom
    def intersection(self, geom, geom_format='ogr', check_result=True):
        """
        Apply an intersection between the Feature and another.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).

            - check_result (optional):
                If True (default), use test_geom to check the result is of an
                appropriate geometry type. Otherwise, supress this and just
                return the result (bool).

        Returns:
        
            - feature:
                The resulting Feature object, or None if no geometry could be
                calculated (Feature).
                
        """
        
        return self.ogr_geom.Intersection(geom)

    def intersects(self, geom, geom_format='ogr'):
        """
        Test the Feature by intersects spatial query.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                
        Returns:
            
            - result:
                Result of the spatial query (bool).

        """
        
        geom = format_geom(geom, geom_format)
        return self.ogr_geom.Intersects(geom)

    def overlaps(self, geom, geom_format='ogr'):
        """
        Test the Feature by overlaps spatial query.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                
        Returns:
            
            - result:
                Result of the spatial query (bool).

        """
        
        geom = format_geom(geom, geom_format)
        return self.ogr_geom.Overlaps(geom)

    def project(self, spatial_ref, sr_format='osr', inplace=True):
        """
        Project the Feature to a new coordinate system.
        
        Parameters:
            
            - spatial_ref:
                Spatial reference to use for projecting the Feature. Input
                must be valid for sr_format (obj/str).
                
            - sr_format (optional):
                Format of spatial_reference. Valid formats are osr (default),
                wkt, proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).
                
            - in_place (optional):
                If True, replace the projection of the current Feature
                (default), otherwise, return a copy (bool).
        
        Returns:
        
            - feature (optional):
                If in place is False, returns a projected copy of the input
                Feature (Feature).

        """
    
        if sr_format != 'osr':
            sr = osr.SpatialReference()
            import_sr[sr_format](sr, spatial_ref)
        else:
            sr = spatial_ref
        if inplace:
            self.ogr_geom.AssignSpatialReference(sr)
            self._set_sr(sr)
        else:
            feature = self.copy()
            feature.project(sr)
            return feature

    def spatial_reference(self, sr_format='osr'):
        """
        Converts the Feature spatial reference to another format.
        
        Parameters:
                
            - sr_format (optional):
                Format of spatial_reference. Valid formats are osr (default),
                wkt, proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).
        
        Returns:
        
            - spatial_ref:
                Converted spatial reference, or None if not present (obj/str).
        
        """
        
        spatial_ref = self.osr_sr
        if spatial_ref:
            if sr_format != 'osr':
                spatial_ref = export_sr[sr_format](sr)
            return spatial_ref
        else:
            return None

    def transform(self, spatial_ref, sr_format='osr', in_place=True):
        """
        Transform the Feature to another coordinate system.
        
        Parameters:
            
            - spatial_ref:
                Spatial reference to use for projecting the Feature. Input
                must be valid for sr_format. Alternatively, an
                osr.Transformation object can be used (str/obj).
                
            - sr_format (optional):
                Format of spatial_reference. Valid formats are osr (default),
                wkt, proj4, url, esri, epsg, epsga, pci, usgs, xml, erm (str).
                
            - in_place (optional):
                If True, replace the projection of the current Feature,
                otherwise, return a copy (bool).
        
        Returns:
        
            - feature (optional):
                If in place is False, returns a transformed copy of the input
                Feature (Feature).
        
        """
        
        if not isinstance(spatial_ref, osr.CoordinateTransformation):
            if sr_format != 'osr':
                sr = osr.SpatialReference()
                import_sr[sr_format](sr, spatial_ref)
            else:
                sr = spatial_ref
        
            if self.osr_sr:
                transform = osr.CoordinateTransformation(self.osr_sr, sr)
            else:
                transform = None
        else:
            transform = spatial_ref
        if transform is not None:
            if in_place:
                self.ogr_geom.Transform(transform)
                self._set_sr(self.ogr_geom.GetSpatialReference())
            else:
                feature = self.copy()
                feature.transform(transform)
                return feature
        else:
            return self.project(sr, 'osr', in_place)

    def to_ogr_feature(self, field_definitions):
        """
        Convert the Feature to an ogr.Feature object.
        
        Parameters:
        
            - field_definitions:
                Can be an ogr.FeatureDefn object, or a FeatureLayer
                field_definitions dict (ogr.FeatureDefn/dict).

        Returns:
        
            - feature:
                The resulting ogr.Feature object (Feature).
                
        """
        
        if not isinstance(field_definitions, ogr.FeatureDefn):
            fields = field_definitions.keys()
            definition = ogr.FeatureDefn()
            for field in field_definitions:
                field_type, precision, width = field_definitions[field]
                field_def = ogr.FieldDefn(field, field_type)
                if precision:
                    field_def.SetPrecision(precision)
                if width:
                    field_def.SetWidth(width)
                definition.AddFieldDefn(field_def)
        else:
            definition = field_definitions
            fields = None
        return create_ogr_feature(definition, self.ogr_geom, self.attributes,
                                  fields)

    def touches(self, geom, geom_format='ogr'):
        """
        Test the Feature by touches spatial query.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                
        Returns:
            
            - result:
                Result of the spatial query (bool).

        """

        geom = format_geom(geom, geom_format)
        return self.ogr_geom.Touches(geom)

    def within(self, geom, geom_format='ogr'):
        """
        Test the Feature by within spatial query.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).
                
        Returns:
            
            - result:
                Result of the spatial query (bool).

        """
        
        geom = format_geom(geom, geom_format)
        if geom.GetGeometryName() in ('Polygon', 'MultiPolygon', 'LinearRing'):
            return self.ogr_geom.Within(geom)
        else:
            return False

    @test_geom
    def union(self, geom, geom_format='ogr', check_result=True):
        """
        Apply a geometric union of the Feature with another.
        
        Parameters:
        
            - geom:
                The input feature, geometry, or an iterable of either,
                including FeatureLayer and FeatureGenerator instances. If
                supplying a raw geometry e.g. wkt, this must match geom_format
                (obj/str).
                
            - geom_format (optional):
                The format of the input geom. Valid options are ogr (default),
                wkt, wkb, json, gml (str).

            - check_result (optional):
                If True (default), use test_geom to check the result is of an
                appropriate geometry type. Otherwise, supress this and just
                return the result (bool).

        Returns:
        
            - feature:
                The resulting Feature object, or None if no geometry could be
                calculated (Feature).
                
        """

        return self.ogr_geom.Union(geom)
