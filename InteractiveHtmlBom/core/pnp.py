"""PnP marking for the BOM table.

Matches BOM rows against a Ki-Qihe style component mapping file
(component_mapping.txt) so the web UI can show a "PnP" checkbox column.

Mapping line format (same as the ki_qihe plugin):
    <nozzle>, <feeder[:SIZE]>, <value[:alias1:alias2:...]>

Example:
    1,L20:0402,0u1:0.1u:100nF:0.1uF:0.1uf:100n

A BOM row is marked PnP when its value matches one of the aliases (with or
without the "/voltage" suffix) and, if the line has a size tag, the
component footprint resolves to that size (0402, 0603, 1005->0402, ...).
Lines starting with '#' or with an E/P prefix are ignored.
"""

import os
import re

SMD_SIZE_RE = re.compile(
    r'\b(01005|0201|0402|0603|0805|1206|1210|1812|2010|2512)\b',
    re.IGNORECASE)
METRIC_TO_IMPERIAL = {
    "1005": "0402",
    "1608": "0603",
    "2012": "0805",
    "3216": "1206",
    "3225": "1210",
    "4532": "1812",
    "5025": "2010",
    "6332": "2512",
}
VALID_IMPERIAL = {
    "01005", "0201", "0402", "0603", "0805", "1206", "1210", "1812",
    "2010", "2512",
}
METRIC_RE = re.compile(
    r'(?<!\d)(?:_|-)?(1005|1608|2012|3216|3225|4532|5025|6332)(?:Metric)?(?!\d)',
    re.IGNORECASE)


def _norm_size(s):
    if not s:
        return ""
    s = s.strip().upper()
    if s in VALID_IMPERIAL:
        return s
    m = re.fullmatch(r"\d{4}", s)
    if m:
        return METRIC_TO_IMPERIAL.get(s, "")
    return ""


def _detect_size(value, footprint):
    """Port of the ki_qihe size detection (value first, then footprint)."""
    m = SMD_SIZE_RE.search(value or '')
    if m:
        return m.group(1).upper()
    m = SMD_SIZE_RE.search(footprint or '')
    if m:
        return m.group(1).upper()
    m = METRIC_RE.search(footprint or '')
    if m:
        return METRIC_TO_IMPERIAL.get(m.group(1), "")
    return ""


def _strip_voltage(v):
    """'100nF/35' -> '100nF'"""
    return v.split('/')[0].strip()


def load_mapping(mapping_path):
    """Parse the mapping file into [(size_tag, [alias, ...]), ...]."""
    mapping = []
    if not mapping_path or not os.path.isfile(mapping_path):
        return mapping
    try:
        with open(mapping_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 3:
                    continue
                prefix = parts[0]
                if prefix in ('E', 'P'):
                    continue
                feeder = parts[1]
                size_tag = ''
                if ':' in feeder:
                    size_tag = _norm_size(feeder.split(':', 1)[1])
                aliases = [a.strip().lower() for a in parts[2].split(':') if a.strip()]
                if aliases:
                    mapping.append((size_tag, aliases))
    except Exception:
        return mapping
    return mapping


def get_pnp_footprints(components, mapping_path):
    """Return the list of component indexes that match the mapping file."""
    mapping = load_mapping(mapping_path)
    if not mapping:
        return []
    result = []
    for i, comp in enumerate(components):
        value = str(getattr(comp, 'val', '') or '')
        footprint = str(getattr(comp, 'footprint', '') or '')
        v = value.lower()
        v_novolt = _strip_voltage(v)
        size = _detect_size(value, footprint)
        for size_tag, aliases in mapping:
            if size_tag and size != size_tag:
                continue
            if any(v == a or v_novolt == _strip_voltage(a) for a in aliases):
                result.append(i)
                break
    return result
