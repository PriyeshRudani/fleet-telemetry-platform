import math
import xml.etree.ElementTree as ElementTree


MAX_KML_BYTES = 1_000_000


def parse_kml_route(content: bytes) -> list[dict[str, float]]:
    if len(content) > MAX_KML_BYTES:
        raise ValueError("KML file is too large")
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("KML entities are not allowed")

    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ValueError("Malformed KML XML") from error

    points: list[dict[str, float]] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "LineString":
            continue
        coordinates = next(
            (
                child.text
                for child in element.iter()
                if child.tag.rsplit("}", 1)[-1] == "coordinates"
            ),
            None,
        )
        if not coordinates:
            continue
        for coordinate in coordinates.split():
            values = coordinate.split(",")
            if len(values) < 2:
                continue
            try:
                longitude = float(values[0])
                latitude = float(values[1])
            except ValueError:
                continue
            if (
                math.isfinite(latitude)
                and math.isfinite(longitude)
                and -90 <= latitude <= 90
                and -180 <= longitude <= 180
            ):
                points.append({"latitude": latitude, "longitude": longitude})

    if len(points) < 2:
        raise ValueError("KML must contain at least two valid route points")
    return points