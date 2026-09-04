from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E

NS = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph'}
for path in (Path(__file__).resolve().parents[1] / 'storage/templates').glob('*.hwpx'):
    print('\nFILE', path.name)
    with ZipFile(path) as z:
        print('MEMBERS', z.namelist())
        for part in z.namelist():
            if not part.startswith('Contents/section') or not part.endswith('.xml'):
                continue
            root = E.fromstring(z.read(part))
            for i, table in enumerate(root.findall('.//hp:tbl', NS)):
                print('TABLE', i, dict(table.attrib), 'size', table.find('hp:sz', NS).attrib)
                for r, row in enumerate(table.findall('hp:tr', NS)):
                    print(' ROW', r, [(dict(cell.find('hp:cellAddr', NS).attrib), dict(cell.find('hp:cellSpan', NS).attrib), '|'.join(cell.xpath('./hp:subList/hp:p/hp:run/hp:t/text()', namespaces=NS))) for cell in row.findall('hp:tc', NS)])
            print('PARAGRAPHS', [p.xpath('string(.)') for p in root.findall('hp:p',NS) if p.find('.//hp:tbl',NS) is None])
