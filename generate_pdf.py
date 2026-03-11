"""
AURA Complete Project Notes — Professional PDF Generator
Converts the full COMPLETE_PROJECT_NOTES.md into a well-formatted PDF
using fpdf2 with proper tables, code blocks, headings, and page layout.
"""

import re, os, textwrap
from fpdf import FPDF

MD_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'COMPLETE_PROJECT_NOTES.md')
PDF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'AURA_Complete_Project_Notes.pdf')

# ──────────────────────────────────────────────────────────────────
#  COLORS
# ──────────────────────────────────────────────────────────────────
C_PRIMARY     = (26, 35, 126)     # deep indigo
C_SECONDARY   = (40, 53, 147)     # indigo
C_ACCENT      = (57, 73, 171)     # lighter indigo
C_ACCENT2     = (92, 107, 192)    # soft indigo
C_TEXT        = (30, 30, 30)      # near black
C_MUTED       = (100, 100, 100)   # gray
C_CODE_BG     = (38, 50, 56)      # dark code bg
C_CODE_FG     = (238, 255, 255)   # code text
C_TABLE_HEAD  = (232, 234, 246)   # light indigo bg
C_TABLE_BORDER = (159, 168, 218)  # indigo border
C_TABLE_STRIPE = (245, 245, 245)  # alt row
C_WHITE       = (255, 255, 255)
C_BLOCKQUOTE  = (121, 134, 203)   # quote border
C_HR          = (197, 202, 233)   # horizontal rule
C_BULLET      = (57, 73, 171)     # bullet color
C_LINK        = (21, 101, 192)    # link blue


def sanitize(text):
    """Replace Unicode chars unsupported by core fonts with ASCII."""
    reps = {
        '\u2014': '--', '\u2013': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u2022': '*',
        '\u2192': '->', '\u2190': '<-', '\u2265': '>=', '\u2264': '<=',
        '\u2260': '!=', '\u00d7': 'x', '\u2713': '[v]', '\u2717': '[x]',
        '\u00a0': ' ', '\u200b': '', '\u2502': '|', '\u2500': '-',
        '\u250c': '+', '\u2510': '+', '\u2514': '+', '\u2518': '+',
        '\u251c': '+', '\u2524': '+', '\u252c': '+', '\u2534': '+',
        '\u253c': '+', '\u25cf': '*', '\u25cb': 'o', '\u25a0': '#',
        '\u25a1': '[]', '\u2605': '*', '\u2606': '*', '\u00b7': '.',
        '\u2003': ' ', '\u2002': ' ', '\u2009': ' ', '\u200a': ' ',
    }
    for u, a in reps.items():
        text = text.replace(u, a)
    # Fallback: replace any remaining non-latin1 chars
    result = []
    for ch in text:
        try:
            ch.encode('latin-1')
            result.append(ch)
        except UnicodeEncodeError:
            result.append('?')
    return ''.join(result)


class AuraPDF(FPDF):
    """Custom PDF with headers, footers, and professional layout."""

    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)
        self.page_title = ''
        self.in_toc = False
        self.toc_entries = []

    def header(self):
        if self.page_no() <= 1:
            return  # no header on cover
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(*C_MUTED)
        self.cell(0, 6, 'AURA - Complete Project Documentation', align='L')
        self.cell(0, 6, f'Page {self.page_no()}', align='R', new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(*C_HR)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        if self.page_no() <= 1:
            return
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(*C_MUTED)
        self.cell(0, 8, 'AURA | AI-Based Student Mental Wellness & Academic Companion | Aditya College of Engineering & Technology', align='C')


def build_cover(pdf: AuraPDF):
    """Render professional cover page."""
    pdf.add_page()
    pdf.ln(45)

    # Main title
    pdf.set_font('Helvetica', 'B', 42)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 18, 'AURA', align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(3)
    pdf.set_font('Helvetica', '', 14)
    pdf.set_text_color(*C_SECONDARY)
    pdf.cell(0, 8, 'AI-Based Student Mental Wellness & Academic Companion', align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(8)
    pdf.set_draw_color(*C_PRIMARY)
    cx = pdf.w / 2
    pdf.line(cx - 40, pdf.get_y(), cx + 40, pdf.get_y())
    pdf.ln(10)

    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(*C_ACCENT)
    pdf.cell(0, 8, 'Complete Project Documentation', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 11)
    pdf.set_text_color(*C_MUTED)
    pdf.cell(0, 7, 'From Scratch to Full Implementation & Deployment', align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(20)

    # Info box
    box_x = 45
    box_w = pdf.w - 90
    box_y = pdf.get_y()
    pdf.set_fill_color(245, 245, 255)
    pdf.set_draw_color(*C_HR)
    pdf.rect(box_x, box_y, box_w, 55, style='DF')

    pdf.set_xy(box_x + 5, box_y + 5)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(*C_PRIMARY)

    info_lines = [
        ('Institution', 'Aditya College of Engineering and Technology'),
        ('Tech Stack', 'Flask + MongoDB + Google Gemini AI + Jinja2 + Vanilla JS'),
        ('Total API Routes', '137+'),
        ('HTML Templates', '16'),
        ('Database Models', '15'),
        ('MongoDB Collections', '20+'),
        ('JavaScript Modules', '9'),
        ('CSS Files', '10'),
        ('Version', '1.0 -- March 2026'),
    ]
    for label, value in info_lines:
        pdf.set_x(box_x + 8)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*C_PRIMARY)
        pdf.cell(38, 6, f'{label}:', align='R')
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(*C_TEXT)
        pdf.cell(0, 6, f'  {value}', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(25)
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(*C_MUTED)
    pdf.cell(0, 6, 'Generated from complete codebase analysis -- every file read and documented', align='C')


def parse_markdown(md_text):
    """Parse markdown into structured blocks for rendering."""
    lines = md_text.split('\n')
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if stripped in ('---', '***', '___'):
            blocks.append(('hr', ''))
            i += 1
            continue

        # Headings
        hm = re.match(r'^(#{1,4})\s+(.+)$', stripped)
        if hm:
            level = len(hm.group(1))
            title = hm.group(2).strip()
            blocks.append(('heading', (level, title)))
            i += 1
            continue

        # Fenced code block
        if stripped.startswith('```'):
            lang = stripped[3:].strip()
            code_lines = []
            i += 1
            while i < n and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            blocks.append(('code', '\n'.join(code_lines)))
            continue

        # Table
        if '|' in stripped and not stripped.startswith('```'):
            table_lines = []
            while i < n and '|' in lines[i].strip():
                row_text = lines[i].strip()
                # skip separator rows like |---|---|
                if re.match(r'^[\|\s\-:]+$', row_text):
                    i += 1
                    continue
                cells = [c.strip() for c in row_text.split('|')]
                # remove empty first/last from leading/trailing |
                if cells and cells[0] == '':
                    cells = cells[1:]
                if cells and cells[-1] == '':
                    cells = cells[:-1]
                if cells:
                    table_lines.append(cells)
                i += 1
            if table_lines:
                blocks.append(('table', table_lines))
            continue

        # Blockquote
        if stripped.startswith('>'):
            quote_lines = []
            while i < n and lines[i].strip().startswith('>'):
                quote_lines.append(re.sub(r'^>\s*', '', lines[i].strip()))
                i += 1
            blocks.append(('blockquote', '\n'.join(quote_lines)))
            continue

        # Bullet list
        bm = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', stripped)
        if bm:
            list_items = []
            while i < n:
                lm = re.match(r'^(\s*)([-*+]|\d+\.)\s+(.+)$', lines[i].strip())
                if not lm:
                    break
                indent = len(lines[i]) - len(lines[i].lstrip())
                list_items.append((indent, lm.group(3)))
                i += 1
            blocks.append(('list', list_items))
            continue

        # Regular paragraph
        para_lines = []
        while i < n:
            cl = lines[i].strip()
            if not cl or cl.startswith('#') or cl.startswith('```') or cl.startswith('>') or cl in ('---','***','___'):
                break
            if '|' in cl and i + 1 < n and re.match(r'^[\|\s\-:]+$', lines[i+1].strip()):
                break  # upcoming table
            lm = re.match(r'^([-*+]|\d+\.)\s+', cl)
            if lm:
                break
            para_lines.append(cl)
            i += 1
        if para_lines:
            blocks.append(('paragraph', ' '.join(para_lines)))
        continue

    return blocks


def clean_md_formatting(text):
    """Remove markdown inline formatting for plain text rendering."""
    # Bold + italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Links [text](url) → text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # HTML entities
    text = text.replace('&mdash;', '--').replace('&amp;', '&').replace('&gt;', '>').replace('&lt;', '<')
    return sanitize(text)


def render_blocks(pdf: AuraPDF, blocks):
    """Render parsed blocks onto PDF."""
    section_num = 0

    for btype, bdata in blocks:

        # Check if we need a new page (avoid orphaned headings)
        if btype == 'heading' and pdf.get_y() > 250:
            pdf.add_page()

        if btype == 'hr':
            y = pdf.get_y() + 2
            pdf.set_draw_color(*C_HR)
            pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
            pdf.ln(6)

        elif btype == 'heading':
            level, title = bdata
            title = clean_md_formatting(title)

            if level == 1:
                pdf.add_page()
                pdf.ln(5)
                pdf.set_font('Helvetica', 'B', 22)
                pdf.set_text_color(*C_PRIMARY)
                pdf.multi_cell(0, 10, title, new_x='LMARGIN', new_y='NEXT')
                # underline
                y = pdf.get_y() + 1
                pdf.set_draw_color(*C_PRIMARY)
                pdf.set_line_width(0.6)
                pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
                pdf.set_line_width(0.2)
                pdf.ln(6)

            elif level == 2:
                if pdf.get_y() > 240:
                    pdf.add_page()
                pdf.ln(6)
                pdf.set_font('Helvetica', 'B', 16)
                pdf.set_text_color(*C_SECONDARY)
                pdf.multi_cell(0, 8, title, new_x='LMARGIN', new_y='NEXT')
                y = pdf.get_y() + 1
                pdf.set_draw_color(*C_HR)
                pdf.set_line_width(0.3)
                pdf.line(pdf.l_margin, y, pdf.l_margin + 80, y)
                pdf.set_line_width(0.2)
                pdf.ln(4)

            elif level == 3:
                if pdf.get_y() > 255:
                    pdf.add_page()
                pdf.ln(4)
                pdf.set_font('Helvetica', 'B', 13)
                pdf.set_text_color(*C_ACCENT)
                pdf.multi_cell(0, 7, title, new_x='LMARGIN', new_y='NEXT')
                pdf.ln(2)

            elif level == 4:
                if pdf.get_y() > 260:
                    pdf.add_page()
                pdf.ln(3)
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(*C_ACCENT2)
                pdf.multi_cell(0, 6, title, new_x='LMARGIN', new_y='NEXT')
                pdf.ln(1)

        elif btype == 'paragraph':
            text = clean_md_formatting(bdata)
            pdf.set_font('Helvetica', '', 9.5)
            pdf.set_text_color(*C_TEXT)
            pdf.multi_cell(0, 5, text, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)

        elif btype == 'blockquote':
            text = clean_md_formatting(bdata)
            if pdf.get_y() > 260:
                pdf.add_page()
            x0 = pdf.l_margin
            y0 = pdf.get_y()
            # Draw left border
            pdf.set_font('Helvetica', 'I', 9)
            pdf.set_text_color(55, 71, 79)
            pdf.set_x(x0 + 6)
            pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin - 8, 5, text, new_x='LMARGIN', new_y='NEXT')
            y1 = pdf.get_y()
            pdf.set_draw_color(*C_BLOCKQUOTE)
            pdf.set_line_width(0.8)
            pdf.line(x0 + 2, y0, x0 + 2, y1)
            pdf.set_line_width(0.2)
            pdf.ln(3)

        elif btype == 'list':
            pdf.set_font('Helvetica', '', 9.5)
            pdf.set_text_color(*C_TEXT)
            for indent_level, item_text in bdata:
                item_text = clean_md_formatting(item_text)
                indent_px = 4 + (indent_level // 2) * 4
                bullet = '-' if indent_level >= 4 else '*'
                pdf.set_x(pdf.l_margin + indent_px)
                pdf.set_text_color(*C_BULLET)
                pdf.cell(4, 5, bullet)
                pdf.set_text_color(*C_TEXT)
                avail_w = pdf.w - pdf.l_margin - pdf.r_margin - indent_px - 5
                pdf.multi_cell(avail_w, 5, item_text, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)

        elif btype == 'code':
            code_text = sanitize(bdata.rstrip())
            if not code_text:
                continue

            if pdf.get_y() > 230:
                pdf.add_page()

            # Background box
            pdf.set_font('Courier', '', 7.5)
            code_lines = code_text.split('\n')
            line_h = 3.8
            block_h = len(code_lines) * line_h + 8
            avail_h = 280 - pdf.get_y()

            # If code block is too tall, truncate display
            max_display_lines = int((avail_h - 10) / line_h)
            if max_display_lines < 5:
                pdf.add_page()
                max_display_lines = int((260) / line_h)

            display_lines = code_lines[:max_display_lines]
            actual_h = len(display_lines) * line_h + 8

            x0 = pdf.l_margin
            y0 = pdf.get_y()
            code_w = pdf.w - pdf.l_margin - pdf.r_margin

            # Draw background
            pdf.set_fill_color(*C_CODE_BG)
            pdf.rect(x0, y0, code_w, actual_h, style='F')

            # Draw rounded corners effect (top/bottom lines)
            pdf.set_draw_color(50, 60, 70)
            pdf.rect(x0, y0, code_w, actual_h, style='D')

            # Render code text
            pdf.set_text_color(*C_CODE_FG)
            pdf.set_xy(x0 + 4, y0 + 4)
            for cline in display_lines:
                # Truncate long lines
                if len(cline) > 105:
                    cline = cline[:102] + '...'
                pdf.set_x(x0 + 4)
                pdf.cell(code_w - 8, line_h, cline, new_x='LMARGIN', new_y='NEXT')

            if len(code_lines) > max_display_lines:
                pdf.set_x(x0 + 4)
                pdf.set_text_color(150, 150, 150)
                pdf.cell(code_w - 8, line_h, f'  ... ({len(code_lines) - max_display_lines} more lines)', new_x='LMARGIN', new_y='NEXT')

            pdf.set_y(y0 + actual_h + 3)
            pdf.ln(2)

        elif btype == 'table':
            rows = bdata
            if not rows:
                continue

            if pdf.get_y() > 240:
                pdf.add_page()

            num_cols = max(len(r) for r in rows)
            # Ensure all rows have same column count
            for idx in range(len(rows)):
                while len(rows[idx]) < num_cols:
                    rows[idx].append('')

            # Calculate column widths based on content
            usable_w = pdf.w - pdf.l_margin - pdf.r_margin
            col_max_lens = []
            for c in range(num_cols):
                max_len = 0
                for r in rows:
                    cell_text = clean_md_formatting(r[c]) if c < len(r) else ''
                    max_len = max(max_len, len(cell_text))
                col_max_lens.append(max_len)

            total_chars = sum(col_max_lens) or 1
            col_widths = []
            for c in range(num_cols):
                w = max((col_max_lens[c] / total_chars) * usable_w, 14)
                col_widths.append(w)

            # Normalize to fit
            total_w = sum(col_widths)
            if total_w > usable_w:
                scale = usable_w / total_w
                col_widths = [w * scale for w in col_widths]

            row_h = 5.5

            for ri, row in enumerate(rows):
                # Check page break
                if pdf.get_y() + row_h > 275:
                    pdf.add_page()
                    # Re-render header row on new page
                    if ri > 0 and rows:
                        pdf.set_fill_color(*C_TABLE_HEAD)
                        pdf.set_draw_color(*C_TABLE_BORDER)
                        pdf.set_font('Helvetica', 'B', 8)
                        pdf.set_text_color(*C_PRIMARY)
                        for ci, cell in enumerate(rows[0]):
                            cell = clean_md_formatting(cell)
                            if ci < len(col_widths):
                                pdf.cell(col_widths[ci], row_h, cell[:35], border=1, fill=True)
                        pdf.ln()

                if ri == 0:
                    # Header row
                    pdf.set_fill_color(*C_TABLE_HEAD)
                    pdf.set_draw_color(*C_TABLE_BORDER)
                    pdf.set_font('Helvetica', 'B', 8)
                    pdf.set_text_color(*C_PRIMARY)
                    for ci, cell in enumerate(row):
                        cell = clean_md_formatting(cell)
                        if ci < len(col_widths):
                            pdf.cell(col_widths[ci], row_h, cell[:40], border=1, fill=True)
                    pdf.ln()
                else:
                    # Data row
                    if ri % 2 == 0:
                        pdf.set_fill_color(*C_TABLE_STRIPE)
                        fill = True
                    else:
                        pdf.set_fill_color(*C_WHITE)
                        fill = True

                    pdf.set_draw_color(*C_TABLE_BORDER)
                    pdf.set_font('Helvetica', '', 8)
                    pdf.set_text_color(*C_TEXT)

                    # Calculate row height based on longest cell
                    max_lines = 1
                    for ci, cell in enumerate(row):
                        cell = clean_md_formatting(cell)
                        if ci < len(col_widths):
                            cell_w = col_widths[ci] - 2
                            if cell_w > 0:
                                chars_per_line = max(int(cell_w / 1.8), 10)
                                needed_lines = max(1, (len(cell) + chars_per_line - 1) // chars_per_line)
                                max_lines = max(max_lines, needed_lines)

                    actual_row_h = row_h * min(max_lines, 3)  # cap at 3 lines

                    x_start = pdf.get_x()
                    y_start = pdf.get_y()

                    for ci, cell in enumerate(row):
                        cell = clean_md_formatting(cell)
                        if ci < len(col_widths):
                            cw = col_widths[ci]
                            # Draw cell border and fill
                            pdf.rect(x_start + sum(col_widths[:ci]), y_start, cw, actual_row_h, style='DF')
                            # Write text
                            pdf.set_xy(x_start + sum(col_widths[:ci]) + 1, y_start + 0.5)
                            # Truncate if too long
                            max_chars = int(cw / 1.7) * min(max_lines, 3)
                            display = cell[:max_chars]
                            if len(cell) > max_chars:
                                display = display[:max_chars-3] + '...'
                            pdf.multi_cell(cw - 2, row_h, display, border=0)

                    pdf.set_xy(x_start, y_start + actual_row_h)

            pdf.ln(4)


def build_toc(pdf: AuraPDF, blocks):
    """Build Table of Contents page."""
    pdf.add_page()
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 22)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(0, 10, 'Table of Contents', align='C', new_x='LMARGIN', new_y='NEXT')
    y = pdf.get_y() + 2
    pdf.set_draw_color(*C_PRIMARY)
    pdf.set_line_width(0.5)
    cx = pdf.w / 2
    pdf.line(cx - 30, y, cx + 30, y)
    pdf.set_line_width(0.2)
    pdf.ln(10)

    toc_num = 0
    for btype, bdata in blocks:
        if btype == 'heading':
            level, title = bdata
            title = clean_md_formatting(title)
            if level <= 2:
                if level == 1:
                    pdf.ln(2)
                indent = 0 if level == 1 else 8
                pdf.set_x(pdf.l_margin + indent)
                if level == 1:
                    pdf.set_font('Helvetica', 'B', 11)
                    pdf.set_text_color(*C_PRIMARY)
                else:
                    toc_num += 1
                    pdf.set_font('Helvetica', '', 10)
                    pdf.set_text_color(*C_ACCENT)
                # Draw dot leaders
                text_w = pdf.get_string_width(title)
                pdf.cell(text_w + 2, 6, title)
                pdf.ln()


def main():
    print('Reading COMPLETE_PROJECT_NOTES.md...')
    with open(MD_PATH, 'r', encoding='utf-8') as f:
        md_text = f.read()

    print('Parsing markdown structure...')
    blocks = parse_markdown(md_text)
    print(f'  Found {len(blocks)} content blocks')

    print('Building PDF...')
    pdf = AuraPDF()

    # Cover page
    build_cover(pdf)

    # Table of Contents
    build_toc(pdf, blocks)

    # Main content
    render_blocks(pdf, blocks)

    # Save
    print(f'Saving to {PDF_PATH}...')
    pdf.output(PDF_PATH)
    size_mb = os.path.getsize(PDF_PATH) / (1024 * 1024)
    pages = pdf.pages_count
    print(f'PDF generated successfully!')
    print(f'  File: {PDF_PATH}')
    print(f'  Pages: {pages}')
    print(f'  Size: {size_mb:.2f} MB')


if __name__ == '__main__':
    main()
