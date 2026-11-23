"""Recognize whether an uploaded TIFF is a suitable input for BioNuclei.

BioNuclei segments nuclei in 2-D fluorescence images: bright nuclei on a dark
background, one intensity channel. Real uploads are often something else: an
RGB export of a fluorescence image, a multi-channel or Z/T stack, a brightfield
or stained-histology image, or a thumbnail. This module reads the file's own
axes and metadata, selects a single 2-D plane where that is well defined, and
rejects inputs the released model was not built for, with a reason a user can
act on.

The checks are deterministic heuristics over the pixel data and metadata. They
are not a trained classifier and do not claim a probability of suitability.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import tifffile

from .fluorophores import describe_channels

MIN_SIDE_PX = 32
_AXIS_NAMES = {"C": "channel", "Z": "z", "T": "time", "S": "sample", "I": "plane", "Q": "plane", "P": "position", "R": "tile"}


class InputRejected(ValueError):
    """The input is readable but not suitable for the released model.

    The message is written for the end user and contains no paths or secrets.
    """


def _pixel_size(tif: tifffile.TiffFile) -> dict[str, Any] | None:
    try:
        if tif.is_ome and tif.ome_metadata:
            match_x = re.search(r'PhysicalSizeX="([0-9.eE+-]+)"', tif.ome_metadata)
            match_y = re.search(r'PhysicalSizeY="([0-9.eE+-]+)"', tif.ome_metadata)
            unit = re.search(r'PhysicalSizeXUnit="([^"]+)"', tif.ome_metadata)
            if match_x:
                return {"x": float(match_x.group(1)), "y": float(match_y.group(1)) if match_y else float(match_x.group(1)),
                        "unit": unit.group(1) if unit else "µm", "source": "OME-XML"}
        if tif.is_imagej and tif.imagej_metadata:
            page = tif.pages[0]
            res = page.tags.get("XResolution")
            unit = tif.imagej_metadata.get("unit")
            if res and unit and unit not in {"pixel", "pixels"}:
                num, den = res.value
                if num:
                    size = den / num
                    return {"x": size, "y": size, "unit": "µm" if unit in {"micron", "um", "\\u00B5m"} else unit, "source": "ImageJ"}
    except Exception:  # metadata is optional; never fail recognition on it
        return None
    return None


def _tiff_channels(tif: tifffile.TiffFile) -> list[dict[str, Any]]:
    """Channel names and wavelengths recorded by OME-XML or ImageJ, if any."""
    channels: list[dict[str, Any]] = []
    try:
        if tif.is_ome and tif.ome_metadata:
            for i, tag in enumerate(re.findall(r"<Channel\b[^>]*>", tif.ome_metadata)):
                attr = dict(re.findall(r'(\w+)="([^"]*)"', tag))
                def num(key: str) -> float | None:
                    try:
                        return float(attr[key]) if key in attr else None
                    except ValueError:
                        return None
                channels.append({"index": i, "name": attr.get("Fluor") or attr.get("Name") or "",
                                 "excitation_nm": num("ExcitationWavelength"), "emission_nm": num("EmissionWavelength"), "source": "OME-XML"})
        elif tif.is_imagej and tif.imagej_metadata:
            labels = tif.imagej_metadata.get("Labels") or []
            count = int(tif.imagej_metadata.get("channels", 0) or 0)
            for i, label in enumerate(labels[:count] if count else []):
                channels.append({"index": i, "name": str(label), "excitation_nm": None, "emission_nm": None, "source": "ImageJ labels"})
    except Exception:
        return []
    return channels


def _channel_notes(record: dict[str, Any], analyzed: int | None) -> None:
    info = record.get("channel_identification") or {}
    channels = info.get("channels") or []
    if not channels:
        return
    for ch in channels:
        label = ch.get("fluorophore") or (" or ".join(ch["candidates"]) if ch.get("candidates") else None)
        if label:
            peaks = f" (ex {ch['excitation_peak_nm']} / em {ch['emission_peak_nm']} nm)" if ch.get("excitation_peak_nm") else ""
            kind = "nuclear stain" if ch.get("nuclear_stain") else "not a nuclear stain" if ch.get("nuclear_stain") is False else "nuclear status unclear"
            record["notes"].append(f"Channel {ch['index']} identified as {label}{peaks}, {kind}, from {ch.get('source', 'metadata')}.")
    nuclear = info.get("nuclear_channel")
    if analyzed is not None and nuclear is not None and analyzed != nuclear:
        record["notes"].append(f"Warning: channel {analyzed} was analyzed, but the metadata identifies channel {nuclear} as the nuclear stain.")


def _contrast_profile(plane: np.ndarray) -> dict[str, float]:
    flat = plane.reshape(-1)
    step = max(1, flat.size // 250_000)
    sample = flat[::step].astype(np.float64)
    sample = sample[np.isfinite(sample)]
    if sample.size == 0:
        return {"p01": 0.0, "median": 0.0, "p995": 0.0, "relative_median": 0.0, "skew": 0.0, "std": 0.0}
    p01, median, p995 = np.percentile(sample, [1, 50, 99.5])
    std = float(sample.std())
    skew = float(np.mean(((sample - sample.mean()) / std) ** 3)) if std > 0 else 0.0
    span = float(p995 - p01)
    relative_median = float((median - p01) / span) if span > 0 else 0.0
    return {"p01": float(p01), "median": float(median), "p995": float(p995), "relative_median": relative_median, "skew": skew, "std": std}


def _looks_like_transmitted_light(profile: dict[str, float]) -> bool:
    """Bright background with darker objects: brightfield, phase or stained histology."""
    return profile["relative_median"] > 0.55 and profile["skew"] < -0.5


def _pick_rgb_channel(rgb: np.ndarray) -> tuple[int, str]:
    """Choose the color channel that carries the fluorescence signal."""
    channels = [rgb[..., i].astype(np.float64) for i in range(min(3, rgb.shape[-1]))]
    if all(np.array_equal(channels[0], c) for c in channels[1:]):
        return 0, "All color channels are identical, so the RGB file is a greyscale image; channel 0 was used."
    contrast = []
    for c in channels:
        step = max(1, c.size // 250_000)
        s = c.reshape(-1)[::step]
        contrast.append(float(np.percentile(s, 99.5) - np.median(s)))
    best = int(np.argmax(contrast))
    names = ["red", "green", "blue"]
    return best, f"RGB color image: the {names[best]} channel carries the strongest signal and was analyzed."


def recognize_tiff(source: Path, destination: Path, *, channel: int = 0, time: int = 0, z: int = 0, field: int = 0) -> dict[str, Any]:
    """Inspect a TIFF, write one analysable 2-D plane to ``destination`` and describe the decision.

    Returns a JSON-serialisable record. Raises :class:`InputRejected` when the
    file is not a suitable fluorescence nuclei image.
    """
    try:
        with tifffile.TiffFile(source) as tif:
            series = tif.series[0]
            axes = str(series.axes)
            shape = tuple(int(v) for v in series.shape)
            data = np.asarray(series.asarray())
            pixel_size = _pixel_size(tif)
            flavour = "OME-TIFF" if tif.is_ome else "ImageJ TIFF" if tif.is_imagej else "TIFF"
            pages = len(tif.pages)
            channel_meta = _tiff_channels(tif)
    except Exception as exc:
        raise InputRejected("The file could not be read as a TIFF image. It may be corrupt or not a TIFF.") from exc

    record: dict[str, Any] = {
        "input_format": flavour,
        "source_axes": axes,
        "source_shape": list(shape),
        "dtype": str(data.dtype),
        "pages": pages,
        "pixel_size": pixel_size,
        "selected_indices": {},
        "notes": [],
    }
    if channel_meta:
        record["channel_identification"] = describe_channels(channel_meta)

    if data.dtype == bool or not (np.issubdtype(data.dtype, np.integer) or np.issubdtype(data.dtype, np.floating)):
        raise InputRejected(f"Unsupported pixel type {data.dtype}. Use an integer or floating-point intensity image.")
    if "Y" not in axes or "X" not in axes:
        raise InputRejected(f"The TIFF has no Y/X image plane (axes '{axes}').")

    requested = {"C": channel, "Z": z, "T": time, "I": field, "Q": field, "P": field, "R": field}
    indexers: list[Any] = []
    selected: dict[str, int] = {}
    rgb_axis = None
    for position, axis in enumerate(axes):
        size = shape[position]
        if axis in {"Y", "X"}:
            indexers.append(slice(None))
        elif axis == "S":
            rgb_axis = True
            indexers.append(slice(None))
        else:
            value = int(requested.get(axis, 0))
            if size == 1:
                value = 0
            if value < 0 or value >= size:
                name = _AXIS_NAMES.get(axis, axis)
                raise InputRejected(f"The image has {size} {name} {'entries' if size != 1 else 'entry'} (0 to {size - 1}); index {value} is out of range.")
            indexers.append(value)
            if size > 1:
                selected[_AXIS_NAMES.get(axis, axis)] = value
    plane = data[tuple(indexers)]

    kinds: list[str] = []
    if any(a in axes and shape[axes.index(a)] > 1 for a in "C"):
        kinds.append(f"{shape[axes.index('C')]}-channel")
    if any(a in axes and shape[axes.index(a)] > 1 for a in "ZTIQ"):
        kinds.append("stack")

    if rgb_axis:
        samples = plane.shape[-1]
        if samples not in (3, 4):
            raise InputRejected(f"Unexpected {samples} samples per pixel. Use a single-channel or RGB image.")
        best, note = _pick_rgb_channel(plane)
        profile_rgb = _contrast_profile(plane[..., :3].mean(axis=-1))
        if _looks_like_transmitted_light(profile_rgb) and "identical" not in note:
            raise InputRejected(
                "This looks like a color brightfield or stained-histology image (bright background with darker objects). "
                "BioNuclei is built for fluorescence images where nuclei are bright on a dark background, such as DAPI or Hoechst."
            )
        plane = plane[..., best]
        selected["color channel"] = best
        record["notes"].append(note)
        kinds.append("RGB")

    plane = np.squeeze(plane)
    if plane.ndim != 2:
        raise InputRejected(f"Could not reduce the image to one 2-D plane (axes '{axes}', shape {list(shape)}).")
    height, width = plane.shape
    if min(height, width) < MIN_SIDE_PX:
        raise InputRejected(f"The image is {height} × {width} px. BioNuclei needs at least {MIN_SIDE_PX} px on each side.")
    finite = np.isfinite(plane) if np.issubdtype(plane.dtype, np.floating) else None
    if finite is not None and not finite.any():
        raise InputRejected("The image contains no finite pixel values.")

    profile = _contrast_profile(plane)
    if profile["std"] == 0 or profile["p995"] == profile["p01"]:
        raise InputRejected("The selected plane has no intensity variation; it appears blank.")
    if _looks_like_transmitted_light(profile):
        raise InputRejected(
            "Most pixels are bright and the objects are darker than the background. This looks like a brightfield, "
            "phase-contrast or stained image. BioNuclei is built for fluorescence images with bright nuclei on a dark background."
        )

    bits = int(plane.dtype.itemsize * 8)
    kind = " ".join(kinds) if kinds else "single-plane"
    record.update({
        "recognized_as": f"{bits}-bit {kind} fluorescence image" if kinds else f"{bits}-bit 2-D fluorescence image",
        "selected_indices": selected,
        "selected_plane_shape": [int(height), int(width)],
        "selected_plane_dtype": str(plane.dtype),
        "contrast": {"relative_median": round(profile["relative_median"], 4), "skew": round(profile["skew"], 4)},
        "decision": "ready" if not selected and not rgb_axis else "plane_extracted",
        "conversion": None if not selected and not rgb_axis else "One 2-D plane was extracted for the 2-D BioNuclei pipeline.",
    })
    if selected and not rgb_axis:
        described = ", ".join(f"{k} {v}" for k, v in selected.items())
        record["notes"].append(f"Multi-dimensional TIFF ({axes}); analyzed {described}.")
    _channel_notes(record, selected.get("channel", 0 if "C" in axes else None))
    tifffile.imwrite(destination, np.ascontiguousarray(plane))
    return record
