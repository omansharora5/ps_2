"""Preserve source chart/workbook provenance after artifact-tool round trips.

This performs package repair only. Slide authoring stays in artifact-tool.
The operation is idempotent and refuses changed chart data or formula ranges.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET
import posixpath
import re
import sys

C = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
R = 'http://schemas.openxmlformats.org/package/2006/relationships'
T = 'http://schemas.openxmlformats.org/package/2006/content-types'


def chart_signature(content):
    root = ET.fromstring(content)
    return [
        [(node.tag.rsplit('}', 1)[-1], node.text) for node in series.iter()
         if node.tag in {f"{{{C['c']}}}f", f"{{{C['c']}}}v"}]
        for series in root.findall('.//c:ser', C)
    ]


def restore(source, candidate):
    source, candidate = Path(source), Path(candidate)
    if source.resolve() == candidate.resolve():
        raise ValueError('Keep the source deck separate from the output')
    with ZipFile(source) as z:
        original = {name: z.read(name) for name in z.namelist()}
    with ZipFile(candidate) as z:
        output = {name: z.read(name) for name in z.namelist()}
    source_charts = {n for n in original if re.search(r'/charts/chart\d+\.xml$', n)}
    target_charts = {n for n in output if re.search(r'/charts/chart\d+\.xml$', n)}
    if source_charts != target_charts or not source_charts:
        raise ValueError('Chart identities differ, cannot preserve unchanged bundles')
    additions = set()
    for chart in source_charts:
        if chart_signature(original[chart]) != chart_signature(output[chart]):
            raise ValueError(f'Chart values or formula references changed: {chart}')
        rels = posixpath.join(posixpath.dirname(chart), '_rels', posixpath.basename(chart) + '.rels')
        if rels not in original:
            raise ValueError(f'Source chart has no workbook relationships: {chart}')
        output[chart] = original[chart]
        output[rels] = original[rels]
        for rel in ET.fromstring(original[rels]):
            if rel.attrib.get('TargetMode') == 'External':
                raise ValueError('External chart data cannot be embedded implicitly')
            target = posixpath.normpath(posixpath.join(posixpath.dirname(chart), rel.attrib['Target']))
            if target not in original:
                raise ValueError(f'Missing original chart dependency: {target}')
            output[target] = original[target]
            additions.add(target)
    source_types = ET.fromstring(original['[Content_Types].xml'])
    types = ET.fromstring(output['[Content_Types].xml'])
    present = {(e.tag, tuple(sorted(e.attrib.items()))) for e in types}
    for entry in source_types:
        relevant = entry.attrib.get('PartName', '').lstrip('/') in additions
        relevant |= entry.tag == f'{{{T}}}Default' and any(n.endswith('.' + entry.attrib.get('Extension', '')) for n in additions)
        key = (entry.tag, tuple(sorted(entry.attrib.items())))
        if relevant and key not in present:
            types.append(entry)
            present.add(key)
    ET.register_namespace('', T)
    output['[Content_Types].xml'] = ET.tostring(types, encoding='utf-8', xml_declaration=True)
    temp = candidate.with_name(candidate.stem + '.chart-repair.tmp.pptx')
    with ZipFile(temp, 'w', ZIP_DEFLATED) as z:
        for name, data in output.items():
            z.writestr(name, data)
    temp.replace(candidate)
    print(f'Preserved {len(source_charts)} unchanged chart and {len(additions)} original dependency')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: restore_unchanged_presentation_chart.py source.pptx candidate.pptx')
    restore(sys.argv[1], sys.argv[2])
