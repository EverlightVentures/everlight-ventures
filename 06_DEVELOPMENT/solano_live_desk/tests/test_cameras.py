from sld.cameras import parse_cameras, nearest, fetch_cameras

SAMPLE = {
    "data": [
        {"cctv": {"index": "TV976", "location": {
            "locationName": "I80 at Suisun Valley Rd", "latitude": "38.22374",
            "longitude": "-122.12696", "county": "Solano", "route": "80"},
            "imageData": {"currentImageURL": "https://x/tv976.jpg",
                          "streamingVideoURL": "https://x/tv976.m3u8"}}},
        {"cctv": {"index": "TV812", "location": {
            "locationName": "I680 S of I80", "latitude": "38.20523",
            "longitude": "-122.13828", "county": "Solano", "route": "680"},
            "imageData": {"static": {"currentImageURL": "https://x/tv812.jpg"},
                          "streamingVideo": {"streamingVideoURL": "https://x/tv812.m3u8"}}}},
        {"cctv": {"location": {"latitude": "0", "longitude": "0"}, "imageData": {}}},  # dropped
    ]
}


def test_parse_handles_both_image_shapes_and_drops_zero():
    cams = parse_cameras(SAMPLE)
    assert len(cams) == 2  # the 0,0 camera is dropped
    by_id = {c["id"]: c for c in cams}
    assert by_id["TV976"]["image_url"] == "https://x/tv976.jpg"
    assert by_id["TV812"]["image_url"] == "https://x/tv812.jpg"       # nested static
    assert by_id["TV812"]["stream_url"] == "https://x/tv812.m3u8"     # nested stream


def test_nearest_sorts_by_distance():
    cams = parse_cameras(SAMPLE)
    near = nearest(cams, 38.224, -122.127, n=1)  # right at TV976
    assert near[0]["id"] == "TV976"
    assert near[0]["distance_mi"] < 0.2


def test_fetch_cameras_uses_injected_fetch():
    cams = fetch_cameras(fetch_fn=lambda: SAMPLE)
    assert len(cams) == 2
