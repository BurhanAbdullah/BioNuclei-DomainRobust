"""Identify what an uploaded file really is from its first bytes.

Users upload anything: phone photos, PDFs, spreadsheets, zipped folders,
vendor microscopy formats, or a JPEG renamed to .tif. The file name is not
trusted. This module reads the signature ("magic bytes") and returns a
plain-language identification plus what the user should do.

docs/assets/file-sniff.js implements the same table for the browser, and
tests/test_file_types.py keeps the two in step.
"""
from __future__ import annotations

from dataclasses import dataclass

ACCEPTED = {"tiff", "bigtiff", "nd2"}


@dataclass(frozen=True)
class FileKind:
    kind: str          # machine id, e.g. "tiff", "jpeg", "pdf"
    label: str         # what it is, for people
    accepted: bool     # can BioNuclei analyse it directly?
    advice: str        # what to do next

    def message(self, filename: str = "") -> str:
        prefix = f"{filename}: " if filename else ""
        return f"{prefix}{self.label}. {self.advice}".strip()


_MICROSCOPY_EXPORT = "Open it in Fiji (Bio-Formats) or your microscope software and export the nuclear channel as TIFF or OME-TIFF."
def _photo(kind: str, what: str) -> FileKind:
    return FileKind(kind, f"This is a {what}", False, "Display images are usually 8-bit exports with lost intensity information. Upload the original TIFF, OME-TIFF or ND2 from the microscope.")


def sniff(head: bytes, filename: str = "") -> FileKind:
    """Identify a file from its first bytes (512 are enough)."""
    h = head[:512]
    name = filename.lower()
    if h[:4] in (b"II*\x00", b"MM\x00*"):
        return FileKind("tiff", "TIFF image", True, "")
    if h[:4] in (b"II+\x00", b"MM\x00+"):
        return FileKind("bigtiff", "BigTIFF image", True, "")
    if h[:4] == b"\xda\xce\xbe\x0a":
        return FileKind("nd2", "Nikon ND2 microscopy file", True, "")
    if h[:12] == b"\x00\x00\x00\x0cjP  \r\n\x87\n":
        if name.endswith(".nd2"):
            return FileKind("nd2_legacy", "Legacy Nikon ND2 file (JPEG 2000 based)", False, _MICROSCOPY_EXPORT)
        return FileKind("jp2", "This is a JPEG 2000 image", False, "Upload the original TIFF, OME-TIFF or ND2 from the microscope.")
    if h[:10] == b"ZISRAWFILE":
        return FileKind("czi", "This is a Zeiss CZI microscopy file, which BioNuclei cannot read yet", False, _MICROSCOPY_EXPORT)
    if h[:4] == b"\x70\x00\x00\x00" and name.endswith(".lif"):
        return FileKind("lif", "This is a Leica LIF microscopy project, which BioNuclei cannot read yet", False, _MICROSCOPY_EXPORT)
    if len(h) >= 132 and h[128:132] == b"DICM":
        return FileKind("dicom", "This is a DICOM medical image, which BioNuclei does not analyse", False, "BioNuclei is built for fluorescence microscopy, not clinical imaging.")
    if h[:8] == b"\x89PNG\r\n\x1a\n":
        return _photo("png", "PNG image")
    if h[:3] == b"\xff\xd8\xff":
        return _photo("jpeg", "JPEG photo")
    if h[:6] in (b"GIF87a", b"GIF89a"):
        return _photo("gif", "GIF image")
    if h[:2] == b"BM" and len(h) > 14:
        return _photo("bmp", "BMP image")
    if h[:4] == b"RIFF" and h[8:12] == b"WEBP":
        return _photo("webp", "WebP image")
    if h[4:8] == b"ftyp" and h[8:12] in (b"heic", b"heix", b"mif1", b"msf1", b"heim", b"hevc"):
        return _photo("heic", "HEIC photo (iPhone)")
    if h[4:8] == b"ftyp" or (h[:4] == b"RIFF" and h[8:12] == b"AVI "):
        return FileKind("video", "This is a video file", False, "Export a single frame as TIFF from the original acquisition, not from a video.")
    if h[:5] == b"%PDF-":
        return FileKind("pdf", "This is a PDF document, not an image", False, "Upload the microscopy image itself as TIFF, OME-TIFF or ND2.")
    if h[:4] == b"PK\x03\x04":
        if name.endswith((".docx", ".xlsx", ".pptx")):
            return FileKind("office", "This is a Microsoft Office document, not an image", False, "Upload the microscopy image itself as TIFF, OME-TIFF or ND2.")
        return FileKind("zip", "This is a ZIP archive", False, "Unzip it and upload the TIFF or ND2 images inside. The experiment tray accepts several at once.")
    if h[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return FileKind("ole", "This is an older Office or Zeiss ZVI container", False, _MICROSCOPY_EXPORT)
    if h[:2] == b"\x1f\x8b":
        return FileKind("gzip", "This is a compressed .gz archive", False, "Decompress it first and upload the TIFF or ND2 inside.")
    if h[:6] == b"7z\xbc\xaf\x27\x1c" or h[:4] == b"Rar!":
        return FileKind("archive", "This is a compressed archive (7z or RAR)", False, "Extract it first and upload the TIFF or ND2 inside.")
    if h[:2] == b"MZ" or h[:4] == b"\x7fELF" or h[:4] in (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe"):
        return FileKind("executable", "This is a program, not an image", False, "Program files are never accepted.")
    if h[:9] == b"SIMPLE  =":
        return FileKind("fits", "This is a FITS astronomy image", False, "Convert it to TIFF first.")
    if h and all(32 <= b < 127 or b in (9, 10, 13) for b in h[:256]):
        return FileKind("text", "This is a text file (for example CSV, notes or code), not an image", False, "Upload the microscopy image itself as TIFF, OME-TIFF or ND2.")
    if not h:
        return FileKind("empty", "This file is empty", False, "Check the file and upload it again.")
    return FileKind("unknown", "This file type could not be recognised", False, "BioNuclei accepts TIFF, OME-TIFF and Nikon ND2.")


def check_upload(head: bytes, filename: str) -> FileKind:
    """Identify an upload and explain a mismatch between name and content."""
    kind = sniff(head, filename)
    name = filename.lower()
    claimed = "nd2" if name.endswith(".nd2") else "tiff" if name.endswith((".tif", ".tiff")) else None
    if claimed and kind.kind not in ACCEPTED and not kind.kind.startswith(claimed):
        extension = filename.rsplit(".", 1)[-1]
        if kind.label.startswith("This is "):
            what = kind.label.removeprefix("This is ")
            label = f"This file is named .{extension} but it is {what}"
        else:
            label = f"This file is named .{extension} but its contents are not a {'Nikon ND2' if claimed == 'nd2' else 'TIFF'} file"
        return FileKind(kind.kind, label, False, kind.advice)
    return kind
