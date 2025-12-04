from wof_explorer.processing.spatial import (
    point_in_geojson_geometry,
    places_containing_point,
)
from wof_explorer.models.places import WOFPlaceWithGeometry
from wof_explorer.types import PlaceType


def make_place(id: int, name: str, geom: dict | None, bbox=None):
    return WOFPlaceWithGeometry(
        id=id,
        name=name,
        placetype=PlaceType.NEIGHBOURHOOD,
        parent_id=None,
        is_current=True,
        bbox=bbox,
        geometry=geom,
    )


def test_point_in_polygon_basic():
    # Square around origin
    poly = {
        "type": "Polygon",
        "coordinates": [
            [(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)],
        ],
    }
    assert point_in_geojson_geometry(0.0, 0.0, poly) is True
    assert point_in_geojson_geometry(0.9, 0.9, poly) is True
    assert point_in_geojson_geometry(1.1, 0.0, poly) is False
    # Boundary considered inside
    assert point_in_geojson_geometry(1.0, 0.5, poly) is True


def test_point_in_multipolygon():
    mp = {
        "type": "MultiPolygon",
        "coordinates": [
            [[(10, 10), (12, 10), (12, 12), (10, 12), (10, 10)]],
            [[(-2, -2), (2, -2), (2, 2), (-2, 2), (-2, -2)]],
        ],
    }
    assert point_in_geojson_geometry(0.0, 0.0, mp) is True
    assert point_in_geojson_geometry(11.0, 11.0, mp) is True
    assert point_in_geojson_geometry(20.0, 20.0, mp) is False


def test_places_containing_point_prefers_geometry():
    # Two places: one with geometry, one with only bbox
    geom_place = make_place(
        1,
        "Geom",
        {
            "type": "Polygon",
            "coordinates": [[(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]],
        },
    )
    bbox_place = make_place(
        2,
        "BBox",
        geom=None,
        bbox=[-1, -1, 1, 1],
    )

    matches = places_containing_point([geom_place, bbox_place], lat=1.5, lon=1.5)
    # Only the geom_place matches at (1.5,1.5)
    assert [p.id for p in matches] == [1]
