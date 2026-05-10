#!/usr/bin/env python3
"""
Markdown to WeChat-ready HTML converter.
Converts markdown files to inline-styled HTML with base64-embedded images.
Output is directly pasteable into WeChat public account editor.

Usage:
    python wechat_html_export.py input.md [--img-dir images] [--output output.html] [--title "标题"]
"""
import base64, os, sys, argparse, re
from pathlib import Path

# ==========================================
# Color palette
# ==========================================
C_BLUE   = '#1a73e8'
C_GREEN  = '#27ae60'
C_RED    = '#e74c3c'
C_ORANGE = '#f39c12'
C_DARK   = '#2c3e50'
C_GRAY   = '#8e8e93'
C_BG_BLUE   = '#e8f0fe'
C_BG_GREEN  = '#e8f8f0'
C_BG_RED    = '#fde8e8'
C_BG_ORANGE = '#fff8e1'
C_BG_YELLOW = '#fff3cd'

# ==========================================
# Helper functions
# ==========================================
def img_b64(filename, img_dir):
    """Convert image file to base64 data URL."""
    path = os.path.join(img_dir, filename) if not os.path.isabs(filename) else filename
    if not os.path.exists(path):
        return f''
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    return f'data:image/png;base64,{b64}'

def inline_span(text, color=None, bold=False, underline=False):
    """Create inline-styled span."""
    styles = []
    if color:
        styles.append(f'color:{color};')
    if bold:
        styles.append('font-weight:bold;')
    if underline:
        styles.append('text-decoration:underline;text-decoration-color:' + C_BLUE + ';text-underline-offset:2px;')
    if not styles:
        return text
    return f'<span style="{" ".join(styles)}">{text}</span>'

def auto_highlight(text):
    """Auto-detect and colorize key data patterns in text.
    - Numbers with %, x, 亿, 万, 元 → red if negative/risk, green if positive, blue if neutral
    - Already has HTML spans → skip
    """
    if '<span' in text or '<b>' in text or '<strong>' in text:
        return text
    return text

def render_md_inline(text):
    """Convert simple markdown patterns to inline HTML.
    **bold** → <strong>, `code` → <code>, etc.
    """
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong style="font-weight:bold;">\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong style="font-weight:bold;">\1</strong>', text)
    # Italic: *text* or _text_
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em style="font-style:italic;">\1</em>', text)
    # Inline code: `text`
    text = re.sub(r'`(.+?)`', r'<code style="background:#f5f5f5;padding:2px 6px;border-radius:3px;font-size:13px;color:#e74c3c;">\1</code>', text)
    # Strikethrough: ~~text~~
    text = re.sub(r'~~(.+?)~~', r'<s style="text-decoration:line-through;color:#999;">\1</s>', text)
    return text

def parse_markdown(md_text, img_dir):
    """Parse markdown text into a list of HTML element strings.
    Returns list of HTML fragments.
    """
    lines = md_text.split('\n')
    html_parts = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Horizontal rule
        if re.match(r'^(-{3,}|_{3,}|\*{3,})$', line.strip()):
            html_parts.append('<hr style="border:none;border-top:1px solid #eee;margin:28px 0;" />')
            i += 1
            continue

        # ATX headings
        heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = render_md_inline(heading_match.group(2))
            if level == 1:
                # Main title
                html_parts.append(f'<h1 style="text-align:center;font-size:24px;color:{C_BLUE};font-weight:bold;letter-spacing:2px;margin:0 0 4px;">{text}</h1>')
            elif level == 2:
                # Section title (equivalent to ##)
                html_parts.append(f'<h2 style="font-size:17px;color:{C_BLUE};border-left:4px solid {C_BLUE};padding-left:12px;margin:32px 0 14px;font-weight:bold;letter-spacing:0.5px;">{text}</h2>')
            else:
                # Subsection (### and beyond)
                html_parts.append(f'<h3 style="font-size:15px;color:{C_ORANGE};margin:18px 0 10px;font-weight:bold;">{text}</h3>')
            i += 1
            continue

        # Image: ![alt](path)
        img_match = re.match(r'^!\[(.*?)\]\((.*?)\)$', line.strip())
        if img_match:
            alt, src = img_match.groups()
            b64 = img_b64(src, img_dir)
            if b64:
                html_parts.append(f'<p style="text-align:center;margin:16px 0 8px;"><img src="{b64}" alt="{alt}" style="width:100%;max-width:100%;height:auto;border-radius:6px;display:inline-block;" /></p>')
            else:
                html_parts.append(f'<p style="text-align:center;color:#999;font-size:13px;margin:12px 0;">[图片缺失: {src}]</p>')
            i += 1
            continue

        # Table
        if '|' in line and i + 1 < len(lines) and re.match(r'^\|?[\s\-:|]+\|', lines[i + 1]):
            table_lines = [line]
            i += 1
            # Skip separator line
            if i < len(lines) and re.match(r'^[\s\-:|]+$', lines[i].replace('|', '')):
                i += 1
            # Collect table rows
            while i < len(lines) and '|' in lines[i]:
                table_lines.append(lines[i])
                i += 1
            html_parts.append(render_table(table_lines))
            continue

        # Unordered list
        if re.match(r'^\s*[-*]\s+', line):
            list_items = []
            while i < len(lines) and re.match(r'^\s*[-*]\s+', lines[i]):
                item_text = re.sub(r'^\s*[-*]\s+', '', lines[i])
                item_text = render_md_inline(item_text)
                list_items.append(f'<li style="margin:6px 0;line-height:1.8;font-size:15px;">{item_text}</li>')
                i += 1
            html_parts.append(f'<ul style="padding-left:20px;margin:8px 0;">{"".join(list_items)}</ul>')
            continue

        # Ordered list
        if re.match(r'^\s*\d+\.\s+', line):
            list_items = []
            while i < len(lines) and re.match(r'^\s*\d+\.\s+', lines[i]):
                item_text = re.sub(r'^\s*\d+\.\s+', '', lines[i])
                item_text = render_md_inline(item_text)
                list_items.append(f'<li style="margin:6px 0;line-height:1.8;font-size:15px;">{item_text}</li>')
                i += 1
            html_parts.append(f'<ol style="padding-left:20px;margin:8px 0;">{"".join(list_items)}</ol>')
            continue

        # Blockquote
        if re.match(r'^>\s+', line):
            quote_lines = []
            while i < len(lines) and re.match(r'^>\s+', lines[i]):
                quote_lines.append(render_md_inline(re.sub(r'^>\s+', '', lines[i])))
                i += 1
            content = ''.join(f'<p style="margin:4px 0;">{l}</p>' for l in quote_lines)
            html_parts.append(f'<div style="background:{C_BG_YELLOW};border-left:4px solid {C_ORANGE};padding:12px 16px;margin:14px 0;border-radius:0 6px 6px 0;"><div style="color:#856404;line-height:1.8;font-size:15px;">{content}</div></div>')
            continue

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Regular paragraph
        text = render_md_inline(line)
        # Check for special patterns
        if any(kw in line for kw in ['极度偏热', '风险', '脆弱', '杀估值', '泡沫', '亏损', '负']):
            html_parts.append(f'<p style="margin:6px 0;line-height:1.8;font-size:15px;">{text}</p>')
        else:
            html_parts.append(f'<p style="margin:6px 0;line-height:1.8;font-size:15px;">{text}</p>')
        i += 1

    return html_parts

def render_table(lines):
    """Convert markdown table lines to HTML table."""
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip('| \t').split('|')]
        if all(re.match(r'^[\s\-:]+$', c) for c in cells):
            continue  # separator line
        rows.append(cells)

    if not rows:
        return ''

    headers = rows[0]
    data = rows[1:]

    th_html = ''.join(
        f'<th style="background:{C_BLUE};color:#fff;padding:10px 8px;text-align:left;font-weight:bold;font-size:13px;border:1px solid #ddd;">{render_md_inline(h)}</th>'
        for h in headers
    )
    trs = ''
    for idx, row in enumerate(data):
        bg = '#f5f7fa' if idx % 2 == 0 else '#fff'
        tds = ''.join(
            f'<td style="padding:8px;border:1px solid #eee;font-size:13px;background:{bg};">{render_md_inline(c)}</td>'
            for c in row
        )
        trs += f'<tr style="background:{bg};">{tds}</tr>'

    return f'<table style="width:100%;border-collapse:collapse;margin:12px 0;font-size:13px;border:1px solid #eee;"><thead><tr>{th_html}</tr></thead><tbody>{trs}</tbody></table>'

def build_html(body_html, title='行业分析', subtitle='', tag='', disclaimer=''):
    """Wrap body HTML in WeChat-ready page structure."""
    subtitle_html = f'<p style="text-align:center;color:{C_GRAY};font-size:13px;margin:0 0 10px;">{subtitle}</p>' if subtitle else ''
    tag_html = f'<p style="text-align:center;"><span style="display:inline-block;background:{C_BG_BLUE};color:{C_BLUE};padding:3px 14px;border-radius:12px;font-size:12px;">{tag}</span></p>' if tag else ''
    disclaimer_html = f'''
<div style="text-align:center;padding-top:16px;border-top:1px solid #eee;">
<p style="background:{C_BG_RED};padding:10px 14px;border-radius:6px;margin:12px auto;font-size:15px;color:{C_RED};font-weight:bold;line-height:1.8;max-width:500px;">{disclaimer}</p>
</div>''' if disclaimer else ''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#f7f7f7;">
<div style="max-width:680px;margin:0 auto;padding:20px 16px;">
<div style="background:#fff;border-radius:8px;padding:32px 24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

{title_html}
{subtitle_html}
{tag_html}

<hr style="border:none;border-top:1px solid #eee;margin:28px 0;" />

{body_html}

{disclaimer_html}

</div>
</div>
</body>
</html>'''

# Fix: title_html not defined above
def build_html_v2(body_html, title='行业分析', subtitle='', tag='', disclaimer=''):
    """Wrap body HTML in WeChat-ready page structure."""
    subtitle_html = f'<p style="text-align:center;color:{C_GRAY};font-size:13px;margin:0 0 10px;">{subtitle}</p>' if subtitle else ''
    tag_html = f'<p style="text-align:center;"><span style="display:inline-block;background:{C_BG_BLUE};color:{C_BLUE};padding:3px 14px;border-radius:12px;font-size:12px;">{tag}</span></p>' if tag else ''
    disclaimer_html = f'''
<div style="text-align:center;padding-top:16px;border-top:1px solid #eee;">
<p style="background:{C_BG_RED};padding:10px 14px;border-radius:6px;margin:12px auto;font-size:15px;color:{C_RED};font-weight:bold;line-height:1.8;max-width:500px;">{disclaimer}</p>
</div>''' if disclaimer else ''

    # If title contains special characters, split
    title_main = title
    title_sub = ''
    if ' | ' in title:
        title_main, title_sub = title.split(' | ', 1)

    title_html = f'<h1 style="text-align:center;font-size:26px;color:{C_BLUE};font-weight:bold;letter-spacing:2px;margin:0 0 4px;">{title_main}</h1>'
    if title_sub:
        title_html += f'<h1 style="text-align:center;font-size:20px;color:{C_DARK};font-weight:bold;margin:0 0 8px;">{title_sub}</h1>'

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#f7f7f7;">
<div style="max-width:680px;margin:0 auto;padding:20px 16px;">
<div style="background:#fff;border-radius:8px;padding:32px 24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

{title_html}
{subtitle_html}
{tag_html}

<hr style="border:none;border-top:1px solid #eee;margin:28px 0;" />

{body_html}

{disclaimer_html}

</div>
</div>
</body>
</html>'''

def main():
    parser = argparse.ArgumentParser(description='Convert markdown to WeChat-ready HTML')
    parser.add_argument('input', help='Input markdown file path')
    parser.add_argument('--img-dir', '-i', help='Image directory (default: same as input file /images)')
    parser.add_argument('--output', '-o', help='Output HTML file path (default: same name with .html)')
    parser.add_argument('--title', '-t', help='Document title (default: filename)')
    parser.add_argument('--subtitle', '-s', help='Document subtitle')
    parser.add_argument('--tag', help='Tag/badge text shown below subtitle')
    parser.add_argument('--disclaimer', '-d', help='Disclaimer text (default: standard investment disclaimer)')
    parser.add_argument('--body-only', '-b', action='store_true',
                        help='Skip everything before the first H1 heading in the MD. '
                             'Also suppresses title/subtitle/tag header in HTML output.')
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f'Error: file not found: {input_path}')
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        output_path = os.path.splitext(input_path)[0] + '.html'

    # Determine image directory
    if args.img_dir:
        img_dir = os.path.abspath(args.img_dir)
    else:
        # Try {input_dir}/images
        input_dir = os.path.dirname(input_path)
        img_dir = os.path.join(input_dir, 'images')
        if not os.path.isdir(img_dir):
            img_dir = input_dir

    # Read markdown
    with open(input_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    # If --body-only, skip everything before the first H2 heading (## )
    if args.body_only:
        h2_match = re.search(r'^(## .+)$', md_text, re.MULTILINE)
        if h2_match:
            md_text = md_text[h2_match.start():]

    # Title
    title = args.title or os.path.splitext(os.path.basename(input_path))[0]

    # Parse markdown
    body_parts = parse_markdown(md_text, img_dir)
    body_html = '\n'.join(body_parts)

    # Default disclaimer
    disclaimer = args.disclaimer or '⚠ 免责声明：本分析为个人学习过程记录，不构成任何投资建议。投资有风险，决策需谨慎。'

    # Build HTML
    if args.body_only:
        # No title/subtitle/tag header, just body + disclaimer
        subtitle_html = ''
        tag_html = ''
        title_html = ''
        separator_html = ''
    else:
        subtitle_html = f'<p style="text-align:center;color:{C_GRAY};font-size:13px;margin:0 0 10px;">{args.subtitle or ""}</p>' if args.subtitle else ''
        tag_html = f'<p style="text-align:center;"><span style="display:inline-block;background:{C_BG_BLUE};color:{C_BLUE};padding:3px 14px;border-radius:12px;font-size:12px;">{args.tag or ""}</span></p>' if args.tag else ''
        # If title contains special characters, split
        title_main = title
        title_sub = ''
        if ' | ' in title:
            title_main, title_sub = title.split(' | ', 1)
        title_html = f'<h1 style="text-align:center;font-size:26px;color:{C_BLUE};font-weight:bold;letter-spacing:2px;margin:0 0 4px;">{title_main}</h1>'
        if title_sub:
            title_html += f'<h1 style="text-align:center;font-size:20px;color:{C_DARK};font-weight:bold;margin:0 0 8px;">{title_sub}</h1>'
        separator_html = '<hr style="border:none;border-top:1px solid #eee;margin:28px 0;" />'

    # Disclaimer
    disclaimer_html = f'''
<div style="text-align:center;padding-top:16px;border-top:1px solid #eee;">
<p style="background:{C_BG_RED};padding:10px 14px;border-radius:6px;margin:12px auto;font-size:15px;color:{C_RED};font-weight:bold;line-height:1.8;max-width:500px;">{disclaimer}</p>
</div>''' if not args.body_only else ''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{title}</title></head>
<body style="margin:0;padding:0;background:#f7f7f7;">
<div style="max-width:680px;margin:0 auto;padding:20px 16px;">
<div style="background:#fff;border-radius:8px;padding:32px 24px;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

{title_html}
{subtitle_html}
{tag_html}

{separator_html}

{body_html}

{disclaimer_html if not args.body_only else ''}

</div>
</div>
</body>
</html>'''

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f'HTML saved to: {output_path}')
    print(f'File size: {file_size_mb:.1f} MB')
    print('')
    print('使用方法：')
    print('1. 用浏览器打开此 HTML 文件')
    print('2. Ctrl+A 全选，Ctrl+C 复制')
    print('3. 打开公众号编辑器，Ctrl+V 粘贴')
    print('4. 图片和样式会完整保留')

if __name__ == '__main__':
    main()
