"""ROI (Region of Interest) polygon configuration and point-in-polygon checking."""

from typing import Any


class ROIConfig:
    """Loads ROI zone polygons from a config dict and checks point membership."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._enabled = config.get("enabled", True)
        self._zones: dict[str, dict[str, Any]] = config.get("zones", {})

    def is_inside_any(self, point: tuple[float, float]) -> bool:
        """Return True if point falls inside any configured zone polygon.

        If ROIConfig is disabled or has no zones, always returns True
        (meaning: no ROI filtering — all detections count).
        """
        if not self._enabled or not self._zones:
            return True
        for zone in self._zones.values():
            if _point_in_polygon(point, zone["polygon"]):
                return True
        return False

    def is_inside(self, zone_name: str, point: tuple[float, float]) -> bool:
        """Return True if point falls inside the named zone polygon.

        Returns False for unknown zone_name or if point is outside.
        """
        zone = self._zones.get(zone_name)
        if zone is None:
            return False
        return _point_in_polygon(point, zone["polygon"])

    def get_zone_labels(self) -> list[str]:
        """Return list of all zone label strings."""
        return [z["label"] for z in self._zones.values()]


def _point_in_polygon(
    point: tuple[float, float], polygon: list[list[float]]
) -> bool:
    """Ray-casting point-in-polygon test. Returns True if point is inside or on edge."""
    x, y = point
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][0], polygon[i][1]
        xj, yj = polygon[j][0], polygon[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside
