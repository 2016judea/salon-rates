"""Twin Cities metro = the seven counties (Hennepin, Ramsey, Anoka, Dakota, Washington,
Scott, Carver). A bounding box on those counties plus addressRegion MN is the filter."""
import math

BBOX = (44.47, 45.42, -94.02, -92.73)  # lat_min, lat_max, lng_min, lng_max
CENTER = (44.9778, -93.2650)


def in_metro(lat, lng, region=None):
    if lat is None or lng is None:
        return False
    if region and region.strip().upper() not in ("MN", "MINNESOTA"):
        return False
    return BBOX[0] <= lat <= BBOX[1] and BBOX[2] <= lng <= BBOX[3]


def miles(a_lat, a_lng, b_lat, b_lng):
    r = 3958.8
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lng - a_lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
