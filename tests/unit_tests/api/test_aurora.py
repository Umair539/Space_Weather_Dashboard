"""OVATION parsing, filtering and cache semantics. No network - the raw
payload shape is pinned here as fixtures so a change at NOAA shows up as a
failing test rather than an empty globe."""

import asyncio

import pytest

from api.aurora import (
    MIN_ABS_LATITUDE,
    MIN_PROBABILITY,
    AuroraCache,
    parse_ovation,
    refresh_once,
)


def _raw(coordinates, **overrides):
    """NOAA's payload shape, verbatim keys included."""
    payload = {
        "Observation Time": "2026-08-14T19:41:00Z",
        "Forecast Time": "2026-08-14T20:57:00Z",
        "Data Format": "[Longitude, Latitude, Aurora]",
        "type": "MultiPoint",
        "coordinates": coordinates,
    }
    payload.update(overrides)
    return payload


class TestParseOvation:
    def test_keeps_points_at_or_above_the_display_floor(self):
        result = parse_ovation(
            _raw([[10, 60, MIN_PROBABILITY], [11, 60, MIN_PROBABILITY + 1]])
        )
        assert result["point_count"] == 2

    def test_drops_points_below_the_display_floor(self):
        result = parse_ovation(
            _raw([[10, 60, 0], [11, 60, MIN_PROBABILITY - 1], [12, 60, 50]])
        )
        assert result["points"] == [[12, 60, 50]]
        assert result["point_count"] == 1

    @pytest.mark.parametrize(
        "source_lon, expected_lon",
        [
            (0, 0),
            (90, 90),
            (180, 180),
            # NOAA serves 0-360; anything past the antimeridian has to wrap
            # negative or it plots on the wrong side of the globe.
            (181, -179),
            (270, -90),
            (359, -1),
        ],
    )
    def test_normalises_longitude_to_minus_180_180(self, source_lon, expected_lon):
        result = parse_ovation(_raw([[source_lon, 65, 40]]))
        assert result["points"][0][0] == expected_lon

    def test_latitude_and_probability_pass_through_untouched(self):
        result = parse_ovation(_raw([[300, -67, 43]]))
        assert result["points"][0][1:] == [-67, 43]

    def test_carries_noaa_timestamps(self):
        result = parse_ovation(_raw([[10, 60, 50]]))
        assert result["observation_time"] == "2026-08-14T19:41:00Z"
        assert result["forecast_time"] == "2026-08-14T20:57:00Z"

    def test_reports_peak_probability_of_kept_points(self):
        result = parse_ovation(_raw([[10, 60, 12], [11, 60, 87], [12, 60, 30]]))
        assert result["max_probability"] == 87

    def test_all_quiet_forecast_is_empty_not_an_error(self):
        """A genuinely quiet Earth is a valid forecast, not a failure - and
        max_probability must not blow up on an empty sequence."""
        result = parse_ovation(_raw([[10, 60, 0], [11, 61, 1]]))
        assert result["points"] == []
        assert result["point_count"] == 0
        assert result["max_probability"] == 0

    def test_missing_coordinates_key_does_not_raise(self):
        result = parse_ovation({"Observation Time": "t"})
        assert result["point_count"] == 0
        assert result["forecast_time"] is None


class TestEquatorialArtifact:
    """NOAA's grid carries a thin band of low nonzero values along the
    equator with nothing between roughly 12 and 28 degrees either side.
    Aurora cannot occur there, and on a globe it draws as a false ring."""

    def test_drops_the_equatorial_band(self):
        result = parse_ovation(
            _raw([[0, -2, 5], [0, -1, 3], [0, 0, 4], [1, 0, 2]])
        )
        assert result["points"] == []

    def test_keeps_real_aurora_latitudes(self):
        result = parse_ovation(_raw([[0, 67, 40], [0, -70, 35]]))
        assert result["point_count"] == 2

    @pytest.mark.parametrize("lat", [MIN_ABS_LATITUDE, -MIN_ABS_LATITUDE])
    def test_cutoff_is_inclusive(self, lat):
        """20 degrees is roughly the Carrington event's reach - the most
        extreme storm on record - so the boundary itself stays in."""
        assert parse_ovation(_raw([[0, lat, 30]]))["point_count"] == 1

    @pytest.mark.parametrize("lat", [MIN_ABS_LATITUDE - 1, -(MIN_ABS_LATITUDE - 1)])
    def test_just_inside_the_cutoff_is_dropped(self, lat):
        assert parse_ovation(_raw([[0, lat, 30]]))["point_count"] == 0

    def test_artifact_does_not_inflate_peak_probability(self):
        """max_probability drives the frontend's colour scale and the panel
        readout, so a dropped point must not still count toward it."""
        result = parse_ovation(_raw([[0, 0, 90], [0, 70, 25]]))
        assert result["max_probability"] == 25


class TestAuroraCache:
    def test_starts_empty(self):
        assert AuroraCache().get() is None

    def test_set_then_get_round_trips(self):
        cache = AuroraCache()
        cache.set({"point_count": 3})
        assert cache.get() == {"point_count": 3}

    def test_set_replaces_rather_than_merges(self):
        cache = AuroraCache()
        cache.set({"point_count": 3, "stale_key": True})
        cache.set({"point_count": 1})
        assert cache.get() == {"point_count": 1}


class TestRefreshOnce:
    def test_publishes_and_stamps_retrieved_at(self, monkeypatch):
        monkeypatch.setattr(
            "api.aurora.fetch_ovation",
            lambda: parse_ovation(_raw([[10, 60, 40], [200, -70, 55]])),
        )
        cache = AuroraCache()
        monkeypatch.setattr("api.aurora.cache", cache)

        assert asyncio.run(refresh_once()) is True
        assert cache.get()["point_count"] == 2
        assert "retrieved_at" in cache.get()

    def test_upstream_failure_leaves_the_previous_forecast_in_place(self, monkeypatch):
        """A failed refresh must not blank the globe - the last good nowcast
        is still the best answer available."""
        cache = AuroraCache()
        cache.set({"point_count": 99, "retrieved_at": "earlier"})
        monkeypatch.setattr("api.aurora.cache", cache)

        def boom():
            raise RuntimeError("NOAA is down")

        monkeypatch.setattr("api.aurora.fetch_ovation", boom)

        assert asyncio.run(refresh_once()) is False
        assert cache.get() == {"point_count": 99, "retrieved_at": "earlier"}
