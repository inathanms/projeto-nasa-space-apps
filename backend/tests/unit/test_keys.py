import pytest

from app.cache.keys import (
    canonical_hash,
    image_cache_params,
    image_key,
    sia_key,
    sidecar_key,
)
from app.cache.normalize import normalize_request, normalize_sia_args
from app.domain.models import Collection, Detector, ImageMode
from app.processing.rendering import Colormap, Stretch
from app.services.image_service import ImageRequest

Q = 6.15
OBS = "2026W20_2A_0464_3"


def make(**kw) -> ImageRequest:
    base = {
        "ra": 210.8015,
        "dec": 54.348917,
        "observation_id": OBS,
        "collection": Collection.QR3,
        "detector": Detector.D2,
    }
    return ImageRequest(**{**base, **kw})


def rgb(**kw) -> ImageRequest:
    return make(**{"mode": ImageMode.RGB, "detector": None, **kw})


def key_of(req: ImageRequest, prefix: str = "") -> str:
    return image_key(normalize_request(req, Q), prefix)


def test_canonical_hash_golden():
    # sha256("{}")[:32]
    assert canonical_hash({}) == "44136fa355b3678a1146ad16f7e8649e"
    # canonical form: sorted keys, compact separators, ASCII escapes
    assert canonical_hash({"b": "\u00e9", "a": 1}) == canonical_hash({"a": 1, "b": "\u00e9"})


def test_canonical_hash_order_independent_and_32_hex():
    h = canonical_hash({"a": 1, "b": 2})
    assert h == canonical_hash({"b": 2, "a": 1})
    assert len(h) == 32 and all(c in "0123456789abcdef" for c in h)
    assert h != canonical_hash({"a": 1, "b": 3})


def test_image_key_shape():
    key = image_key(make(), "dev/")
    prefix, _, rest = key.partition("images/")
    assert prefix == "dev/"
    version, collection, obs, name = rest.split("/")
    assert (version, collection, obs) == ("r1", "spherex_qr3", OBS)
    stem, _, ext = name.partition(".")
    assert ext == "png" and len(stem) == 32


def test_image_key_golden():
    # Pins the whole recipe (params selection, canonical JSON, hashing). Changing it
    # invalidates the whole image cache: bump RENDER_VERSION deliberately if intended.
    assert image_key(make(), "") == (
        "images/r1/spherex_qr3/2026W20_2A_0464_3/7ce62994cd388a9aaa4917c0efde50ba.png"
    )


def test_ac501_nearby_ra_share_key_far_ra_does_not():
    a = key_of(make(ra=210.80227))
    b = key_of(make(ra=210.80180))
    c = key_of(make(ra=210.80250))
    assert a == b
    assert a != c


def test_ac503_rgb_ignores_colormap():
    assert key_of(rgb(colormap=Colormap.GRAY)) == key_of(rgb(colormap=Colormap.VIRIDIS))


def test_single_depends_on_colormap():
    assert key_of(make(colormap=Colormap.GRAY)) != key_of(make(colormap=Colormap.VIRIDIS))


def test_explicit_scale_ignores_percentiles():
    a = key_of(make(scale_min=1.0, scale_max=2.0, percentile_low=1.0, percentile_high=99.5))
    b = key_of(make(scale_min=1.0, scale_max=2.0, percentile_low=5.0, percentile_high=90.0))
    assert a == b


def test_partial_explicit_scale_keeps_other_percentile():
    a = key_of(make(scale_min=1.0, percentile_low=1.0, percentile_high=99.5))
    assert a == key_of(make(scale_min=1.0, percentile_low=7.0, percentile_high=99.5))
    assert a != key_of(make(scale_min=1.0, percentile_low=1.0, percentile_high=90.0))


def test_rgb_explicit_scale_ignores_percentiles_and_scale_matters():
    base = {"scale_mins": (0.0, 0.0, 0.0), "scale_maxs": (1.0, 1.0, 1.0)}
    assert key_of(rgb(**base, percentile_low=1.0)) == key_of(rgb(**base, percentile_low=9.0))
    other = {"scale_mins": (0.0, 0.0, 0.0), "scale_maxs": (1.0, 1.0, 2.0)}
    assert key_of(rgb(**base)) != key_of(rgb(**other))


def test_without_explicit_scale_percentiles_matter():
    assert key_of(make(percentile_low=1.0)) != key_of(make(percentile_low=2.0))


def test_single_ignores_detectors():
    a = key_of(make(detectors=(Detector.D1, Detector.D2, Detector.D3)))
    assert a == key_of(make(detectors=None))
    assert "detectors" not in image_cache_params(make(detectors=(Detector.D1,)))


def test_rgb_ignores_detector_and_resolves_default_detectors():
    a = key_of(rgb(detector=Detector.D5))
    assert a == key_of(rgb())
    assert a == key_of(rgb(detectors=(Detector.D3, Detector.D2, Detector.D1)))
    assert a != key_of(rgb(detectors=(Detector.D1, Detector.D2, Detector.D3)))
    assert "detector" not in image_cache_params(rgb(detector=Detector.D5))


@pytest.mark.parametrize(
    "change",
    [
        {"detector": Detector.D3},
        {"size": 2.0},
        {"upscale": 2},
        {"align": False},
        {"stack": True},
        {"fill_holes": True},
        {"subtract_zodi": False},
        {"stretch": Stretch.LOG},
        {"collection": Collection.DR1},
        {"observation_id": "2026W20_2A_0464_1"},
        {"dec": 54.4},
    ],
)
def test_each_relevant_param_changes_key(change):
    assert key_of(make(**change)) != key_of(make())


def test_params_include_render_version_and_collection():
    params = image_cache_params(make())
    assert params["render_version"] == "r1"
    assert params["collection"] == "spherex_qr3"


def test_key_is_stable_across_calls():
    assert key_of(make()) == key_of(make())


def test_render_version_changes_image_key_not_sia_key(monkeypatch):
    req = make()
    args = normalize_sia_args(210.8, 54.3, 0.001, Collection.QR3, None, None, None, Q)
    image_before, sia_before = image_key(req, ""), sia_key(args, "")
    monkeypatch.setattr("app.processing.RENDER_VERSION", "r2")
    image_after, sia_after = image_key(req, ""), sia_key(args, "")
    assert "/r1/" in image_before and "/r2/" in image_after
    assert image_before.rsplit("/", 1)[1] != image_after.rsplit("/", 1)[1]
    assert sia_before == sia_after


def test_sidecar_key():
    key = image_key(make(), "dev/")
    side = sidecar_key(key)
    assert side == key[:-4] + ".json"
    with pytest.raises(ValueError):
        sidecar_key("images/x.json")


def test_sia_key_shape_and_sensitivity():
    args = normalize_sia_args(210.8, 54.3, 0.001, Collection.QR3, None, None, 100, Q)
    key = sia_key(args, "prod/")
    prefix, collection, name = key.split("/")[0], key.split("/")[2], key.split("/")[3]
    assert key.startswith("prod/sia/spherex_qr3/") and key.endswith(".json")
    assert (prefix, collection) == ("prod", "spherex_qr3")
    assert len(name) == 32 + len(".json")
    other = normalize_sia_args(210.8, 54.3, 0.001, Collection.QR3, 60000.0, None, 100, Q)
    assert sia_key(other, "prod/") != key
    ordered = dict(reversed(list(args.items())))
    assert sia_key(ordered, "prod/") == key


# Review Focus 2: never build an invalid key.


@pytest.mark.parametrize("obs", ["a/b", "../x", "id with space", "obsé", "", "a" * 65, "a.b"])
def test_invalid_observation_id_rejected(obs):
    with pytest.raises(ValueError):
        image_key(make(observation_id=obs), "")


@pytest.mark.parametrize("prefix", ["dev", "de v/", "dev/../", "/dev/", "dev//", "dév/", "a?b/"])
def test_invalid_prefix_rejected(prefix):
    with pytest.raises(ValueError):
        image_key(make(), prefix)
    args = normalize_sia_args(1.0, 1.0, 0.001, Collection.QR3, None, None, None, Q)
    with pytest.raises(ValueError):
        sia_key(args, prefix)


def test_key_length_limit():
    ok_prefix = "p" * 300 + "/"
    assert len(image_key(make(), ok_prefix).encode()) < 512
    with pytest.raises(ValueError):
        image_key(make(), "p" * 500 + "/")
    args = normalize_sia_args(1.0, 1.0, 0.001, Collection.QR3, None, None, None, Q)
    with pytest.raises(ValueError):
        sia_key(args, "p" * 500 + "/")


def test_sidecar_length_also_bounded():
    # Largest prefix whose PNG key is < 512 bytes: sidecar (.json) is 1 byte longer.
    base = len(image_key(make(), "").encode())
    prefix = "p" * (510 - base) + "/"
    png_len = base + len(prefix)
    assert png_len == 511
    with pytest.raises(ValueError):
        image_key(make(), prefix)
