"""Identify fluorophores from channel metadata and file names.

A grey-level image cannot tell DAPI from Hoechst: dye identity is not in the
pixels. It is recorded in acquisition metadata (ND2 and OME-XML channel names
and excitation/emission wavelengths) and often in file names. This module
matches those records against a reference table of common fluorophores.

Peak wavelengths are approximate published maxima (nm) for the bound or
mature form, as listed by FPbase (fpbase.org) and Thermo Fisher's
Fluorescence SpectraViewer. They identify a channel; they are not a
substitute for the instrument's actual filter set.
"""
from __future__ import annotations

import re
from typing import Any

# name, aliases, excitation peak, emission peak, nuclear stain?, note
FLUOROPHORES: list[dict[str, Any]] = [
    {"name": "DAPI", "aliases": ["dapi"], "ex": 358, "em": 461, "nuclear": True, "note": "DNA stain, fixed cells"},
    {"name": "Hoechst 33342", "aliases": ["hoechst 33342", "hoechst33342", "hoechst", "h33342", "nucblue"], "ex": 350, "em": 461, "nuclear": True, "note": "DNA stain, live or fixed cells"},
    {"name": "Hoechst 33258", "aliases": ["hoechst 33258", "hoechst33258", "h33258"], "ex": 352, "em": 461, "nuclear": True, "note": "DNA stain"},
    {"name": "DRAQ5", "aliases": ["draq5"], "ex": 646, "em": 697, "nuclear": True, "note": "far-red DNA stain, live or fixed cells"},
    {"name": "DRAQ7", "aliases": ["draq7"], "ex": 599, "em": 697, "nuclear": True, "note": "far-red DNA stain, dead or permeabilised cells"},
    {"name": "Propidium iodide", "aliases": ["propidium iodide", "propidium", "pi"], "ex": 535, "em": 617, "nuclear": True, "note": "DNA stain, dead or fixed cells"},
    {"name": "SYTOX Green", "aliases": ["sytox green", "sytox"], "ex": 504, "em": 523, "nuclear": True, "note": "DNA stain, dead cells"},
    {"name": "RedDot1", "aliases": ["reddot1", "reddot"], "ex": 662, "em": 694, "nuclear": True, "note": "far-red DNA stain, live cells"},
    {"name": "NucRed Live 647", "aliases": ["nucred", "nucred live"], "ex": 638, "em": 686, "nuclear": True, "note": "far-red DNA stain, live cells"},
    {"name": "H2B-GFP", "aliases": ["h2b-gfp", "h2bgfp", "h2b gfp", "h2b"], "ex": 488, "em": 507, "nuclear": True, "note": "histone fusion, labels chromatin"},
    {"name": "H2B-mCherry", "aliases": ["h2b-mcherry", "h2bmcherry", "h2b mcherry"], "ex": 587, "em": 610, "nuclear": True, "note": "histone fusion, labels chromatin"},
    {"name": "EGFP", "aliases": ["egfp", "gfp"], "ex": 488, "em": 507, "nuclear": False, "note": "fluorescent protein"},
    {"name": "FITC", "aliases": ["fitc"], "ex": 495, "em": 519, "nuclear": False, "note": "green conjugate"},
    {"name": "Alexa Fluor 488", "aliases": ["alexa fluor 488", "alexa488", "af488", "a488"], "ex": 495, "em": 519, "nuclear": False, "note": "green conjugate"},
    {"name": "Alexa Fluor 555", "aliases": ["alexa fluor 555", "alexa555", "af555", "a555"], "ex": 555, "em": 565, "nuclear": False, "note": "orange conjugate"},
    {"name": "Cy3", "aliases": ["cy3"], "ex": 550, "em": 570, "nuclear": False, "note": "orange conjugate"},
    {"name": "TRITC", "aliases": ["tritc", "rhodamine"], "ex": 557, "em": 576, "nuclear": False, "note": "orange conjugate"},
    {"name": "tdTomato", "aliases": ["tdtomato"], "ex": 554, "em": 581, "nuclear": False, "note": "fluorescent protein"},
    {"name": "Alexa Fluor 568", "aliases": ["alexa fluor 568", "alexa568", "af568", "a568"], "ex": 578, "em": 603, "nuclear": False, "note": "red conjugate"},
    {"name": "mCherry", "aliases": ["mcherry"], "ex": 587, "em": 610, "nuclear": False, "note": "fluorescent protein"},
    {"name": "Alexa Fluor 594", "aliases": ["alexa fluor 594", "alexa594", "af594", "a594"], "ex": 590, "em": 617, "nuclear": False, "note": "red conjugate"},
    {"name": "Texas Red", "aliases": ["texas red", "texasred"], "ex": 595, "em": 615, "nuclear": False, "note": "red conjugate"},
    {"name": "Cy5", "aliases": ["cy5"], "ex": 649, "em": 670, "nuclear": False, "note": "far-red conjugate"},
    {"name": "Alexa Fluor 647", "aliases": ["alexa fluor 647", "alexa647", "af647", "a647"], "ex": 650, "em": 665, "nuclear": False, "note": "far-red conjugate"},
]

EMISSION_TOLERANCE_NM = 12


def _norm(text: str) -> str:
    return re.sub(r"[\s_\-]+", " ", str(text or "").lower()).strip()


def _by_name(text: str) -> dict[str, Any] | None:
    """Match a channel name or file name against aliases, longest alias first."""
    norm = f" {_norm(text)} "
    compact = norm.replace(" ", "")
    candidates = sorted(((alias, entry) for entry in FLUOROPHORES for alias in entry["aliases"]), key=lambda pair: -len(pair[0]))
    for alias, entry in candidates:
        a = _norm(alias)
        if len(a.replace(" ", "")) <= 3:
            if re.search(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", norm):
                return entry
        elif f" {a} " in norm or a.replace(" ", "") in compact:
            return entry
    return None


def identify(name: str | None = None, excitation_nm: float | None = None, emission_nm: float | None = None) -> dict[str, Any]:
    """Identify a channel's fluorophore. Name beats wavelength; wavelength gives candidates."""
    if name:
        entry = _by_name(name)
        if entry:
            return {"fluorophore": entry["name"], "excitation_peak_nm": entry["ex"], "emission_peak_nm": entry["em"],
                    "nuclear_stain": entry["nuclear"], "note": entry["note"], "matched_by": "name", "candidates": [entry["name"]]}
    if emission_nm:
        near = [e for e in FLUOROPHORES if abs(e["em"] - float(emission_nm)) <= EMISSION_TOLERANCE_NM]
        if excitation_nm:
            near = [e for e in near if abs(e["ex"] - float(excitation_nm)) <= 25] or near
        if near:
            nuclear = {e["nuclear"] for e in near}
            return {"fluorophore": near[0]["name"] if len(near) == 1 else None,
                    "excitation_peak_nm": near[0]["ex"] if len(near) == 1 else None,
                    "emission_peak_nm": near[0]["em"] if len(near) == 1 else None,
                    "nuclear_stain": nuclear.pop() if len(nuclear) == 1 else None,
                    "note": "matched by emission wavelength", "matched_by": "emission",
                    "candidates": [e["name"] for e in near]}
    return {"fluorophore": None, "excitation_peak_nm": None, "emission_peak_nm": None, "nuclear_stain": None,
            "note": "no match", "matched_by": None, "candidates": []}


def describe_channels(channels: list[dict[str, Any]]) -> dict[str, Any]:
    """Annotate channel records and pick the nuclear channel when the metadata is unambiguous."""
    annotated = []
    for ch in channels:
        info = identify(ch.get("name"), ch.get("excitation_nm"), ch.get("emission_nm"))
        annotated.append({**ch, **info})
    nuclear = [c["index"] for c in annotated if c.get("nuclear_stain") is True]
    return {"channels": annotated, "nuclear_channel": nuclear[0] if len(nuclear) == 1 else None,
            "nuclear_channel_candidates": nuclear}


def public_table() -> list[dict[str, Any]]:
    """The reference table as published to the browser (docs/assets/fluorophores.json)."""
    return [{k: e[k] for k in ("name", "aliases", "ex", "em", "nuclear", "note")} for e in FLUOROPHORES]
