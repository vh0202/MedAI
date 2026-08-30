import docx
from docx.document import Document as Doc
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

d = docx.Document('original.docx')

def iter_block(parent):
    body = parent.element.body
    for child in body.iterchildren():
        if child.tag == qn('w:p'):
            yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield Table(child, parent)

out=[]
tcount=0
for b in iter_block(d):
    if isinstance(b, Paragraph):
        txt=b.text.strip()
        style=b.style.name if b.style else ''
        # detect images
        has_img = 'graphic' in b._p.xml
        if has_img:
            out.append('[[IMAGE]]')
        if txt:
            out.append(f'<{style}> {txt}')
    else:
        tcount+=1
        rows=len(b.rows); cols=len(b.columns)
        out.append(f'[[TABLE {tcount} rows={rows} cols={cols}]]')
        for r in b.rows[:60]:
            cells=[c.text.strip().replace("\n"," / ") for c in r.cells]
            out.append('  | ' + ' | '.join(cells))
        out.append('[[/TABLE]]')

open('extracted.txt','w').write('\n'.join(out))
print('paragraphs+tables blocks:', len(out), 'tables:', tcount)
words = sum(len(l.split()) for l in out)
print('approx words:', words)
