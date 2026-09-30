"""Copy the existing icon-led slide canvas without changing the other slides."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as ET
import posixpath
import sys

REL = 'http://schemas.openxmlformats.org/package/2006/relationships'


def merge(base_path, template_path, output_path):
    with ZipFile(base_path) as z:
        base = {name: z.read(name) for name in z.namelist()}
    with ZipFile(template_path) as z:
        template = {name: z.read(name) for name in z.namelist()}
    slide = 'ppt/slides/slide3.xml'
    rels_name = 'ppt/slides/_rels/slide3.xml.rels'
    rels = ET.fromstring(template[rels_name])
    for rel in rels:
        kind = rel.attrib['Type'].rsplit('/', 1)[-1]
        if rel.attrib.get('TargetMode') == 'External':
            continue
        target = rel.attrib['Target'].lstrip('/')
        if not rel.attrib['Target'].startswith('/'):
            target = posixpath.normpath(posixpath.join('ppt/slides', target))
        if kind == 'image':
            new_target = 'ppt/media/icon-canvas-' + posixpath.basename(target)
            base[new_target] = template[target]
            rel.set('Target', '/' + new_target)
        elif kind == 'slideLayout':
            if base.get(target) != template[target]:
                raise ValueError('The source and base must share the same slide layout')
        elif kind == 'notesSlide':
            if target not in base:
                raise ValueError('Missing target notes part')
        else:
            raise ValueError(f'Unexpected slide dependency: {kind}')
    base[slide] = template[slide]
    ET.register_namespace('', REL)
    base[rels_name] = ET.tostring(rels, encoding='utf-8', xml_declaration=True)
    output = Path(output_path)
    if output.resolve() in {Path(base_path).resolve(), Path(template_path).resolve()}:
        raise ValueError('Use a separate output file')
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', ZIP_DEFLATED) as z:
        for name, data in base.items():
            z.writestr(name, data)
    print('Restored the icon-led slide 3 canvas; other slides and notes preserved')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('Usage: restore_icon_architecture_canvas.py base.pptx template.pptx output.pptx')
    merge(*sys.argv[1:])
