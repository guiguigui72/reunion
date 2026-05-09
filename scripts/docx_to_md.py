"""Convert competition entry docx to markdown."""
from docx import Document
import os

doc = Document(r'C:\Users\Legion\Desktop\重逢_TRAE_SOLO_参赛报名.docx')

lines = []
for p in doc.paragraphs:
    text = p.text.strip()
    if not text:
        lines.append('')
        continue

    style = p.style.name

    if style == 'Title':
        lines.append(f'# {text}')
        lines.append('')
    elif style == 'Subtitle':
        lines.append(f'*{text}*')
        lines.append('')
    elif style.startswith('Heading 1'):
        lines.append(f'## {text}')
        lines.append('')
    elif style.startswith('Heading 2'):
        lines.append(f'### {text}')
        lines.append('')
    elif style == 'List Bullet':
        lines.append(f'- {text}')
    else:
        lines.append(text)
        lines.append('')

md = '\n'.join(lines)

# Remove excessive blank lines
import re
md = re.sub(r'\n{3,}', '\n\n', md)

outpath = r'C:\Users\Legion\Desktop\重逢_TRAE_SOLO_参赛报名.md'
with open(outpath, 'w', encoding='utf-8') as f:
    f.write(md)
print(f'Saved: {outpath}')
