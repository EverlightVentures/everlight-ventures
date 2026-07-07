from sld.geo import decode_latlon, in_solano_bbox, SOLANO_CENTROID


def test_decode_latlon_valid_negates_longitude():
    assert decode_latlon('"38223740:122126960"') == (38.22374, -122.12696)


def test_decode_latlon_zero_is_none():
    assert decode_latlon('"0:0"') == (None, None)


def test_decode_latlon_garbage_is_none():
    assert decode_latlon("") == (None, None)
    assert decode_latlon("nope") == (None, None)


def test_in_solano_bbox():
    assert in_solano_bbox(38.25, -122.0) is True
    assert in_solano_bbox(34.05, -118.24) is False
    assert in_solano_bbox(None, None) is False


def test_centroid_is_inside_bbox():
    assert in_solano_bbox(*SOLANO_CENTROID) is True
