#!/usr/bin/env python3
"""
Build a single HTML reader for Beyond the Veil.
Reads all chapter .md files, converts to HTML, and outputs a styled reading experience.
Run: python3 build_reader.py
Output: BEYOND_THE_VEIL_reader.html (in same directory)
"""
import os
import re
import html

BOOK_DIR = os.path.dirname(os.path.abspath(__file__))
CHAPTERS_DIR = os.path.join(BOOK_DIR, "chapters")
OUTPUT = os.path.join(BOOK_DIR, "BEYOND_THE_VEIL_reader.html")

CHAPTER_ORDER = [
    "00_prologue.md",
    "01_a_world_in_conflict.md",
    "02_deeper_into_the_dream.md",
    "03_the_town_falls_apart.md",
    "04_rising_tensions.md",
    "05_the_breaking_point.md",
    "06_the_coma.md",
    "07_preparing_for_battle.md",
    "08_the_astral_war.md",
    "09_resolution_and_rebirth.md",
    "10_a_new_timeline.md",
]

CHAPTER_TITLES = {
    "00_prologue.md": "Prologue: The Cost of Flight",
    "01_a_world_in_conflict.md": "Chapter 1: A World in Conflict",
    "02_deeper_into_the_dream.md": "Chapter 2: Deeper into the Dream",
    "03_the_town_falls_apart.md": "Chapter 3: The Town Falls Apart",
    "04_rising_tensions.md": "Chapter 4: Rising Tensions in Both Worlds",
    "05_the_breaking_point.md": "Chapter 5: The Breaking Point",
    "06_the_coma.md": "Chapter 6: The Coma",
    "07_preparing_for_battle.md": "Chapter 7: Preparing for the Final Battle",
    "08_the_astral_war.md": "Chapter 8: The Astral War",
    "09_resolution_and_rebirth.md": "Chapter 9: Resolution and Rebirth",
    "10_a_new_timeline.md": "Chapter 10: A New Timeline",
}

DEDICATION = (
    "<p><em>This book is dedicated to my brother,<br>\n"
    "who left this world on September 3, 2024.</em></p>\n"
    "<p><em>You always said the dead do not really leave.<br>\n"
    "They just go somewhere we cannot follow yet.</em></p>\n"
    "<p><em>I believe you now.</em></p>\n"
    "<p><em>This is me finding my way to where you are.</em></p>"
)

EMDASH = "\u2014"


def md_to_html(text):
    """Simple markdown to HTML conversion for novel prose."""
    lines = text.split('\n')
    result = []
    in_paragraph = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('# ') or stripped.startswith('## ') or stripped.startswith('### '):
            if in_paragraph:
                result.append('</p>')
                in_paragraph = False
            if stripped.startswith('## '):
                title = stripped.lstrip('#').strip()
                title = title.replace('\u201c', '').replace('\u201d', '').replace('"', '')
                result.append('<h3 class="part-title">{}</h3>'.format(html.escape(title)))
            continue

        if stripped == '---' or stripped == '***' or stripped == '* * *':
            if in_paragraph:
                result.append('</p>')
                in_paragraph = False
            result.append('<div class="scene-break">&#10045; &#10045; &#10045;</div>')
            continue

        if stripped.lower().startswith('*end of') or stripped.lower().startswith('end of'):
            continue

        if stripped == '**END OF BOOK 1**':
            if in_paragraph:
                result.append('</p>')
                in_paragraph = False
            result.append('<div class="book-end"><p>END OF BOOK 1</p></div>')
            continue

        if not stripped:
            if in_paragraph:
                result.append('</p>')
                in_paragraph = False
            continue

        processed = stripped
        processed = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', processed)
        processed = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', processed)
        processed = re.sub(r'\*(.*?)\*', r'<em>\1</em>', processed)
        processed = processed.replace(' -- ', ' {} '.format(EMDASH))
        processed = processed.replace('--', EMDASH)

        if not in_paragraph:
            result.append('<p>')
            in_paragraph = True
        else:
            result.append(' ')
        result.append(processed)

    if in_paragraph:
        result.append('</p>')

    return '\n'.join(result)


def build_css():
    return """
        :root {
            --bg: #faf8f5;
            --text: #2c2c2c;
            --accent: #8b6914;
            --accent-light: #d4a843;
            --chapter-bg: #ffffff;
            --sidebar-bg: #f0ece4;
            --sidebar-text: #4a4a4a;
            --border: #d4cfc5;
            --scene-break: #b8a88a;
        }
        [data-theme="dark"] {
            --bg: #1a1a2e;
            --text: #e0dcd4;
            --accent: #d4a843;
            --accent-light: #f0d080;
            --chapter-bg: #22223a;
            --sidebar-bg: #16162a;
            --sidebar-text: #b0a89c;
            --border: #3a3a52;
            --scene-break: #6a6080;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.85;
            transition: all 0.3s ease;
        }
        .sidebar {
            position: fixed;
            left: 0; top: 0; bottom: 0;
            width: 280px;
            background: var(--sidebar-bg);
            border-right: 1px solid var(--border);
            overflow-y: auto;
            padding: 2rem 1.5rem;
            z-index: 100;
            transform: translateX(0);
            transition: transform 0.3s ease;
        }
        .sidebar.hidden { transform: translateX(-280px); }
        .sidebar h1 {
            font-size: 1.1rem;
            color: var(--accent);
            margin-bottom: 0.3rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .sidebar .subtitle {
            font-size: 0.8rem;
            color: var(--sidebar-text);
            font-style: italic;
            margin-bottom: 0.5rem;
        }
        .sidebar .series {
            font-size: 0.7rem;
            color: var(--sidebar-text);
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        .sidebar .word-count {
            font-size: 0.7rem;
            color: var(--sidebar-text);
            margin-bottom: 1rem;
        }
        .sidebar ul { list-style: none; }
        .sidebar li { margin-bottom: 0.4rem; }
        .sidebar a {
            color: var(--sidebar-text);
            text-decoration: none;
            font-size: 0.85rem;
            transition: color 0.2s;
            display: block;
            padding: 0.3rem 0.5rem;
            border-radius: 4px;
        }
        .sidebar a:hover, .sidebar a.active {
            color: var(--accent);
            background: rgba(139, 105, 20, 0.08);
        }
        .controls {
            position: fixed;
            top: 1rem;
            right: 1rem;
            z-index: 200;
            display: flex;
            gap: 0.5rem;
        }
        .controls button {
            background: var(--sidebar-bg);
            border: 1px solid var(--border);
            color: var(--sidebar-text);
            padding: 0.5rem 0.8rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            font-family: inherit;
            transition: all 0.2s;
        }
        .controls button:hover {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }
        .menu-btn {
            position: fixed;
            top: 1rem;
            left: 1rem;
            z-index: 200;
            background: var(--sidebar-bg);
            border: 1px solid var(--border);
            color: var(--sidebar-text);
            padding: 0.5rem 0.8rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
            display: none;
        }
        .main {
            margin-left: 280px;
            transition: margin-left 0.3s ease;
        }
        .main.full { margin-left: 0; }
        .title-page {
            text-align: center;
            padding: 8rem 2rem 6rem;
            max-width: 700px;
            margin: 0 auto;
        }
        .title-page h1 {
            font-size: 3rem;
            color: var(--accent);
            letter-spacing: 0.15em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            font-weight: 400;
        }
        .title-page .subtitle {
            font-size: 1.1rem;
            color: var(--sidebar-text);
            font-style: italic;
            letter-spacing: 0.08em;
            margin-bottom: 3rem;
        }
        .title-page .series-name {
            font-size: 0.9rem;
            color: var(--sidebar-text);
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 4rem;
        }
        .title-page .divider {
            width: 60px;
            height: 1px;
            background: var(--accent);
            margin: 2rem auto;
        }
        .dedication {
            text-align: center;
            padding: 6rem 2rem;
            max-width: 500px;
            margin: 0 auto;
            font-style: italic;
            color: var(--sidebar-text);
            line-height: 2.2;
        }
        .dedication p { margin-bottom: 1.5rem; }
        .chapter {
            max-width: 700px;
            margin: 0 auto;
            padding: 4rem 2rem 6rem;
        }
        .chapter-title {
            font-size: 1.8rem;
            color: var(--accent);
            text-align: center;
            margin-bottom: 3rem;
            font-weight: 400;
            letter-spacing: 0.05em;
        }
        .chapter-body p {
            margin-bottom: 1.2rem;
            text-indent: 1.5em;
            text-align: justify;
            hyphens: auto;
        }
        .chapter-body p:first-child,
        .chapter-body .scene-break + p,
        .chapter-body .part-title + p {
            text-indent: 0;
        }
        .chapter-body p:first-child::first-letter {
            font-size: 3.2em;
            float: left;
            line-height: 0.8;
            margin-right: 0.08em;
            margin-top: 0.05em;
            color: var(--accent);
            font-weight: 400;
        }
        .part-title {
            font-size: 1.15rem;
            color: var(--accent);
            text-align: center;
            margin: 3rem 0 2rem;
            font-weight: 400;
            font-style: italic;
            letter-spacing: 0.03em;
        }
        .scene-break {
            text-align: center;
            color: var(--scene-break);
            margin: 2.5rem 0;
            font-size: 1.2rem;
            letter-spacing: 0.5em;
        }
        .book-end {
            text-align: center;
            margin: 4rem 0;
            padding: 2rem;
            font-size: 1.1rem;
            letter-spacing: 0.2em;
            color: var(--accent);
            font-weight: 600;
        }
        .progress-bar {
            position: fixed;
            top: 0;
            left: 0;
            height: 3px;
            background: var(--accent);
            z-index: 300;
            transition: width 0.1s;
        }
        @media (max-width: 768px) {
            .sidebar { transform: translateX(-280px); }
            .sidebar.visible { transform: translateX(0); }
            .main { margin-left: 0; }
            .menu-btn { display: block; }
            .chapter { padding: 3rem 1.2rem 4rem; }
            .title-page { padding: 5rem 1.5rem 4rem; }
            .title-page h1 { font-size: 2rem; }
        }
        body.font-sm { font-size: 15px; }
        body.font-md { font-size: 18px; }
        body.font-lg { font-size: 21px; }
        body.font-xl { font-size: 24px; }
        html { scroll-behavior: smooth; }
    """


def build_js():
    return """
        var sizes = ['font-sm', 'font-md', 'font-lg', 'font-xl'];
        var currentSize = 1;
        function changeFontSize(dir) {
            document.body.classList.remove(sizes[currentSize]);
            currentSize = Math.max(0, Math.min(sizes.length - 1, currentSize + dir));
            document.body.classList.add(sizes[currentSize]);
            localStorage.setItem('btv-fontsize', currentSize);
        }
        function toggleTheme() {
            var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            document.documentElement.setAttribute('data-theme', isDark ? '' : 'dark');
            document.getElementById('themeBtn').textContent = isDark ? '\\u263E' : '\\u2600';
            localStorage.setItem('btv-theme', isDark ? 'light' : 'dark');
        }
        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('visible');
        }
        document.querySelectorAll('.sidebar a').forEach(function(a) {
            a.addEventListener('click', function() {
                if (window.innerWidth <= 768) {
                    document.getElementById('sidebar').classList.remove('visible');
                }
            });
        });
        window.addEventListener('scroll', function() {
            var scrollTop = window.scrollY;
            var docHeight = document.documentElement.scrollHeight - window.innerHeight;
            var progress = (scrollTop / docHeight) * 100;
            document.getElementById('progressBar').style.width = progress + '%';
        });
        var chapters = document.querySelectorAll('.chapter');
        var tocLinks = document.querySelectorAll('.sidebar a');
        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    tocLinks.forEach(function(link) { link.classList.remove('active'); });
                    var id = entry.target.id;
                    var activeLink = document.querySelector('.sidebar a[href=\"#' + id + '\"]');
                    if (activeLink) activeLink.classList.add('active');
                }
            });
        }, { threshold: 0.1, rootMargin: '-20% 0px -70% 0px' });
        chapters.forEach(function(ch) { observer.observe(ch); });
        var savedSize = localStorage.getItem('btv-fontsize');
        if (savedSize !== null) {
            document.body.classList.remove(sizes[currentSize]);
            currentSize = parseInt(savedSize);
            document.body.classList.add(sizes[currentSize]);
        }
        var savedTheme = localStorage.getItem('btv-theme');
        if (savedTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            document.getElementById('themeBtn').textContent = '\\u2600';
        }
    """


def build_html():
    chapters_html = []
    toc_items = []

    for fname in CHAPTER_ORDER:
        path = os.path.join(CHAPTERS_DIR, fname)
        if not os.path.exists(path):
            continue

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        title = CHAPTER_TITLES.get(fname, fname)
        chapter_id = fname.replace('.md', '').replace(' ', '_')

        toc_items.append(
            '<li><a href="#{cid}">{t}</a></li>'.format(
                cid=chapter_id, t=html.escape(title)
            )
        )

        body_html = md_to_html(content)
        chapters_html.append(
            '<section class="chapter" id="{cid}">\n'
            '    <h2 class="chapter-title">{t}</h2>\n'
            '    <div class="chapter-body">\n'
            '        {body}\n'
            '    </div>\n'
            '</section>\n'.format(
                cid=chapter_id, t=html.escape(title), body=body_html
            )
        )

    toc_html = '\n'.join(toc_items)
    chapters_content = '\n'.join(chapters_html)

    total_words = 0
    for fname in CHAPTER_ORDER:
        path = os.path.join(CHAPTERS_DIR, fname)
        if os.path.exists(path):
            with open(path, 'r') as f:
                total_words += len(f.read().split())

    css = build_css()
    js = build_js()

    mdash = "&mdash;"

    full_html = (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '    <meta charset="UTF-8">\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '    <title>Beyond the Veil ' + mdash + ' A Quantum Western Thriller</title>\n'
        '    <style>' + css + '</style>\n'
        '</head>\n'
        '<body class="font-md">\n'
        '    <div class="progress-bar" id="progressBar"></div>\n'
        '    <button class="menu-btn" id="menuBtn" onclick="toggleSidebar()">&#9776;</button>\n'
        '    <nav class="sidebar" id="sidebar">\n'
        '        <h1>Beyond the Veil</h1>\n'
        '        <div class="subtitle">A Quantum Western Thriller</div>\n'
        '        <div class="series">The Hailey Pink Chronicles ' + mdash + ' Book 1</div>\n'
        '        <div class="word-count">' + '{:,}'.format(total_words) + ' words</div>\n'
        '        <ul>\n'
        '            <li><a href="#title-page">Title Page</a></li>\n'
        '            <li><a href="#dedication">Dedication</a></li>\n'
        '            ' + toc_html + '\n'
        '        </ul>\n'
        '    </nav>\n'
        '    <div class="controls">\n'
        '        <button onclick="changeFontSize(-1)" title="Smaller text">A-</button>\n'
        '        <button onclick="changeFontSize(1)" title="Larger text">A+</button>\n'
        '        <button onclick="toggleTheme()" id="themeBtn" title="Toggle dark mode">&#9790;</button>\n'
        '    </div>\n'
        '    <main class="main" id="main">\n'
        '        <div class="title-page" id="title-page">\n'
        '            <h1>Beyond the Veil</h1>\n'
        '            <div class="subtitle">A Quantum Western Thriller</div>\n'
        '            <div class="divider"></div>\n'
        '            <div class="series-name">The Hailey Pink Chronicles ' + mdash + ' Book 1</div>\n'
        '        </div>\n'
        '        <div class="dedication" id="dedication">\n'
        '            ' + DEDICATION + '\n'
        '        </div>\n'
        '        ' + chapters_content + '\n'
        '    </main>\n'
        '    <script>' + js + '</script>\n'
        '</body>\n'
        '</html>'
    )

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(full_html)

    print("Built: " + OUTPUT)
    print("Total words: {:,}".format(total_words))
    print("Chapters: {}".format(len(chapters_html)))


if __name__ == '__main__':
    build_html()
