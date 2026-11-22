/* Identify an uploaded file by its contents, not its name.
 * Mirrors src/bionuclei/file_types.py (tests/test_file_types.py keeps the kinds in step).
 * Reads only the first 512 bytes. Nothing is uploaded or stored. */
(() => {
  'use strict';
  const EXPORT = 'Open it in Fiji (Bio-Formats) or your microscope software and export the nuclear channel as TIFF or OME-TIFF.';
  const PHOTO = 'Display images are usually 8-bit exports with lost intensity information. Upload the original TIFF, OME-TIFF or ND2 from the microscope.';
  const IMAGE_ITSELF = 'Upload the microscopy image itself as TIFF, OME-TIFF or ND2.';
  const K = (kind, label, accepted, advice) => ({ kind, label, accepted, advice: advice || '' });
  const eq = (h, off, sig) => sig.every((b, i) => h[off + i] === b);
  const str = s => Array.from(s, c => c.charCodeAt(0));

  function sniffBytes(h, filename) {
    const name = String(filename || '').toLowerCase();
    if (eq(h, 0, [0x49, 0x49, 0x2a, 0]) || eq(h, 0, [0x4d, 0x4d, 0, 0x2a])) return K('tiff', 'TIFF image', true);
    if (eq(h, 0, [0x49, 0x49, 0x2b, 0]) || eq(h, 0, [0x4d, 0x4d, 0, 0x2b])) return K('bigtiff', 'BigTIFF image', true);
    if (eq(h, 0, [0xda, 0xce, 0xbe, 0x0a])) return K('nd2', 'Nikon ND2 microscopy file', true);
    if (eq(h, 0, [0, 0, 0, 0x0c, 0x6a, 0x50, 0x20, 0x20, 0x0d, 0x0a, 0x87, 0x0a])) return name.endsWith('.nd2') ? K('nd2_legacy', 'Legacy Nikon ND2 file (JPEG 2000 based)', false, EXPORT) : K('jp2', 'This is a JPEG 2000 image', false, 'Upload the original TIFF, OME-TIFF or ND2 from the microscope.');
    if (eq(h, 0, str('ZISRAWFILE'))) return K('czi', 'This is a Zeiss CZI microscopy file, which BioNuclei cannot read yet', false, EXPORT);
    if (eq(h, 0, [0x70, 0, 0, 0]) && name.endsWith('.lif')) return K('lif', 'This is a Leica LIF microscopy project, which BioNuclei cannot read yet', false, EXPORT);
    if (h.length >= 132 && eq(h, 128, str('DICM'))) return K('dicom', 'This is a DICOM medical image, which BioNuclei does not analyse', false, 'BioNuclei is built for fluorescence microscopy, not clinical imaging.');
    if (eq(h, 0, [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) return K('png', 'This is a PNG image', false, PHOTO);
    if (eq(h, 0, [0xff, 0xd8, 0xff])) return K('jpeg', 'This is a JPEG photo', false, PHOTO);
    if (eq(h, 0, str('GIF87a')) || eq(h, 0, str('GIF89a'))) return K('gif', 'This is a GIF image', false, PHOTO);
    if (eq(h, 0, str('BM')) && h.length > 14) return K('bmp', 'This is a BMP image', false, PHOTO);
    if (eq(h, 0, str('RIFF')) && eq(h, 8, str('WEBP'))) return K('webp', 'This is a WebP image', false, PHOTO);
    if (eq(h, 4, str('ftyp')) && ['heic', 'heix', 'mif1', 'msf1', 'heim', 'hevc'].some(t => eq(h, 8, str(t)))) return K('heic', 'This is a HEIC photo (iPhone)', false, PHOTO);
    if (eq(h, 4, str('ftyp')) || (eq(h, 0, str('RIFF')) && eq(h, 8, str('AVI ')))) return K('video', 'This is a video file', false, 'Export a single frame as TIFF from the original acquisition, not from a video.');
    if (eq(h, 0, str('%PDF-'))) return K('pdf', 'This is a PDF document, not an image', false, IMAGE_ITSELF);
    if (eq(h, 0, [0x50, 0x4b, 0x03, 0x04])) return /\.(docx|xlsx|pptx)$/.test(name) ? K('office', 'This is a Microsoft Office document, not an image', false, IMAGE_ITSELF) : K('zip', 'This is a ZIP archive', false, 'Unzip it and upload the TIFF or ND2 images inside. The experiment tray accepts several at once.');
    if (eq(h, 0, [0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1])) return K('ole', 'This is an older Office or Zeiss ZVI container', false, EXPORT);
    if (eq(h, 0, [0x1f, 0x8b])) return K('gzip', 'This is a compressed .gz archive', false, 'Decompress it first and upload the TIFF or ND2 inside.');
    if (eq(h, 0, [0x37, 0x7a, 0xbc, 0xaf, 0x27, 0x1c]) || eq(h, 0, str('Rar!'))) return K('archive', 'This is a compressed archive (7z or RAR)', false, 'Extract it first and upload the TIFF or ND2 inside.');
    if (eq(h, 0, str('MZ')) || eq(h, 0, [0x7f, 0x45, 0x4c, 0x46]) || eq(h, 0, [0xcf, 0xfa, 0xed, 0xfe]) || eq(h, 0, [0xca, 0xfe, 0xba, 0xbe])) return K('executable', 'This is a program, not an image', false, 'Program files are never accepted.');
    if (eq(h, 0, str('SIMPLE  ='))) return K('fits', 'This is a FITS astronomy image', false, 'Convert it to TIFF first.');
    if (!h.length) return K('empty', 'This file is empty', false, 'Check the file and upload it again.');
    if (Array.from(h.slice(0, 256)).every(b => (b >= 32 && b < 127) || b === 9 || b === 10 || b === 13)) return K('text', 'This is a text file (for example CSV, notes or code), not an image', false, IMAGE_ITSELF);
    return K('unknown', 'This file type could not be recognised', false, 'BioNuclei accepts TIFF, OME-TIFF and Nikon ND2.');
  }

  function checkUpload(h, filename) {
    const kind = sniffBytes(h, filename);
    const name = String(filename || '');
    const lower = name.toLowerCase();
    const claimed = lower.endsWith('.nd2') ? 'nd2' : /\.tiff?$/.test(lower) ? 'tiff' : null;
    if (claimed && !['tiff', 'bigtiff', 'nd2'].includes(kind.kind) && !kind.kind.startsWith(claimed)) {
      const ext = name.split('.').pop();
      const label = kind.label.startsWith('This is ') ? `This file is named .${ext} but it is ${kind.label.slice(8)}` : `This file is named .${ext} but its contents are not a ${claimed === 'nd2' ? 'Nikon ND2' : 'TIFF'} file`;
      return { ...kind, label, accepted: false };
    }
    if (kind.accepted && !claimed) return { ...kind, accepted: false, label: `This is a ${kind.label} with the wrong file extension`, advice: `Rename it to end in ${kind.kind === 'nd2' ? '.nd2' : '.tif'} and add it again.` };
    if (kind.accepted && (kind.kind === 'nd2') !== (claimed === 'nd2')) return { ...kind, accepted: false, label: `The name ends in .${name.split('.').pop()} but the contents are a ${kind.label}`, advice: 'Rename it with the correct extension and add it again.' };
    return kind;
  }

  async function sniffFile(file) {
    const head = new Uint8Array(await file.slice(0, 512).arrayBuffer());
    const kind = checkUpload(head, file.name);
    return { ...kind, message: `${kind.label}${kind.advice ? '. ' + kind.advice : ''}` };
  }

  window.BioNucleiSniff = Object.freeze({ sniffBytes, checkUpload, sniffFile });
})();
