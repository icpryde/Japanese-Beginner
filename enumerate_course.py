#!/usr/bin/env python3
"""
Enumerate the Akamonkai course structure.
Uses persistent browser context to handle Cloudflare.
Outputs manifest.json with all lesson URLs and metadata.
"""
import asyncio
import json
import re
import time
from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

BASE = 'https://japaneseonline.gogonihon.com'
SLUG = 'akamonkai-japanese-12-week-beginner-course'
PROJECT = Path(__file__).parent
CONTENT = PROJECT / 'content'
BROWSER_DATA = PROJECT / '.browser_data'


async def wait_for_cf(page, timeout=120):
    """Wait for Cloudflare challenge to resolve."""
    for i in range(timeout // 3):
        title = await page.title()
        if 'just a moment' not in title.lower():
            return True
        await page.wait_for_timeout(3000)
        if i % 5 == 0:
            print(f'  CF wait... ({i*3}s)', flush=True)
    return False


async def main():
    CONTENT.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(BROWSER_DATA),
            headless=False,
            viewport={'width': 1280, 'height': 900},
            args=['--disable-blink-features=AutomationControlled'],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # Navigate to course
        print('Navigating to course...', flush=True)
        await page.goto(
            f'{BASE}/courses/take/{SLUG}',
            wait_until='domcontentloaded',
            timeout=60000,
        )
        await wait_for_cf(page)
        await page.wait_for_timeout(3000)

        title = await page.title()
        url = page.url
        print(f'URL: {url}', flush=True)
        print(f'Title: {title}', flush=True)

        # Check if redirected to login
        if 'sign_in' in url or 'login' in url:
            print('Need to login...', flush=True)
            # Try multiple selectors for email field
            email = None
            for sel in ['input[name="user[email]"]', 'input[type="email"]', 'input[placeholder*="Email" i]']:
                try:
                    email = await page.wait_for_selector(sel, timeout=5000)
                    if email:
                        break
                except Exception:
                    continue
            if email:
                await email.fill('ichoppryde@gmail.com')
            else:
                print('ERROR: Could not find email field', flush=True)

            pwd = None
            for sel in ['input[name="user[password]"]', 'input[type="password"]']:
                try:
                    pwd = await page.wait_for_selector(sel, timeout=5000)
                    if pwd:
                        break
                except Exception:
                    continue
            if pwd:
                await pwd.fill('dXXc6EM2mxib3W')

            # Click submit — could be button or input
            btn = None
            for sel in ['button:has-text("Sign in")', 'button:has-text("Log In")', 'input[type="submit"]', 'button[type="submit"]']:
                try:
                    btn = await page.wait_for_selector(sel, timeout=3000)
                    if btn:
                        break
                except Exception:
                    continue
            if btn:
                await btn.click()
                print('Login submitted, waiting...', flush=True)
            else:
                # Fallback: press Enter
                print('No submit button found, pressing Enter...', flush=True)
                await page.keyboard.press('Enter')

            await page.wait_for_timeout(5000)
            await wait_for_cf(page)

            # Navigate to course again
            await page.goto(
                f'{BASE}/courses/take/{SLUG}',
                wait_until='domcontentloaded',
                timeout=60000,
            )
            await wait_for_cf(page)
            await page.wait_for_timeout(3000)

        print(f'On course page: {page.url}', flush=True)
        await page.screenshot(path=str(PROJECT / 'debug_course.png'))

        # Scroll sidebar to load everything, then expand all sections
        print('Expanding all sidebar sections...', flush=True)
        expanded = await page.evaluate('''async () => {
            // Find the scrollable sidebar
            const sidebar = document.querySelector(
                '[class*="sidebar"], [class*="course-mainbar"], nav'
            );
            const scrollTarget = sidebar || document.documentElement;

            // Scroll sidebar to bottom to trigger lazy loading
            for (let i = 0; i < 100; i++) {
                scrollTarget.scrollTop = scrollTarget.scrollHeight;
                await new Promise(r => setTimeout(r, 150));
            }
            scrollTarget.scrollTop = 0;
            await new Promise(r => setTimeout(r, 1000));

            // Expand all collapsed sections
            const targets = document.querySelectorAll(
                '[aria-expanded="false"], ' +
                'details:not([open]), ' +
                'button[class*="section"], ' +
                '[class*="section-title"], ' +
                'summary'
            );
            let clicked = 0;
            for (const el of targets) {
                try {
                    el.click();
                    clicked++;
                    await new Promise(r => setTimeout(r, 100));
                } catch(e) {}
            }
            return clicked;
        }''')
        print(f'Expanded {expanded} sections', flush=True)
        await page.wait_for_timeout(2000)

        # Try a second pass — click any section headers that still aren't expanded
        expanded2 = await page.evaluate('''async () => {
            const targets = document.querySelectorAll(
                '[aria-expanded="false"]'
            );
            let clicked = 0;
            for (const el of targets) {
                try { el.click(); clicked++; await new Promise(r => setTimeout(r, 100)); } catch(e) {}
            }
            return clicked;
        }''')
        if expanded2 > 0:
            print(f'Expanded {expanded2} more sections (2nd pass)', flush=True)
            await page.wait_for_timeout(2000)

        # Extract all content
        print('Extracting lesson links...', flush=True)
        html = await page.content()
        soup = BeautifulSoup(html, 'html.parser')

        # Save full HTML
        with open(CONTENT / 'course_page.html', 'w') as f:
            f.write(html)

        # Extract links
        content_types = ['texts', 'multimedia', 'quizzes', 'downloads', 'lessons']
        links = []
        seen = set()

        for a in soup.select('a[href]'):
            href = a.get('href', '')
            if SLUG in href and any(ct in href for ct in content_types):
                full = href if href.startswith('http') else BASE + href
                if full not in seen:
                    seen.add(full)
                    ctype = next(
                        (t for t in content_types if f'/{t}/' in href), 'unknown'
                    )
                    id_match = re.search(r'/(\d+)-', href)
                    lesson_id = id_match.group(1) if id_match else ''

                    # Get parent section
                    section = ''
                    parent = a.find_parent(
                        class_=re.compile(r'section|chapter', re.I)
                    )
                    if parent:
                        header = parent.find(['h2', 'h3', 'h4'])
                        if header:
                            section = header.get_text(strip=True)

                    # Get lesson type label from subtitle
                    subtitle = ''
                    sub_el = a.select_one(
                        '[class*="subtitle"], [class*="type"], small, span'
                    )
                    if sub_el:
                        subtitle = sub_el.get_text(strip=True)

                    links.append({
                        'url': full,
                        'title': a.get_text(strip=True),
                        'type': ctype,
                        'section': section,
                        'id': lesson_id,
                        'subtitle': subtitle,
                    })

        # Sort by lesson ID (numeric) for ordering
        def sort_key(l):
            try:
                return int(l['id'])
            except ValueError:
                return 999999
        links.sort(key=sort_key)

        print(f'Found {len(links)} unique lesson links', flush=True)

        # Count by type
        type_counts = {}
        for l in links:
            type_counts[l['type']] = type_counts.get(l['type'], 0) + 1
        print(f'By type: {type_counts}', flush=True)

        # Extract section structure from headings
        sections = []
        for h in soup.select('h3, h4'):
            text = h.get_text(strip=True)
            if text and len(text) < 200:
                sections.append(text)

        # Deduplicate while preserving order
        seen_sections = set()
        unique_sections = []
        for s in sections:
            if s not in seen_sections:
                seen_sections.add(s)
                unique_sections.append(s)
        sections = unique_sections

        print(f'\nSections ({len(sections)}):', flush=True)
        for s in sections:
            print(f'  {s[:80]}', flush=True)

        # Print all links
        print(f'\nAll {len(links)} lesson links:', flush=True)
        for i, l in enumerate(links):
            print(
                f'  {i+1:4}. [{l["type"]:12}] {l["title"][:55]:55} id={l["id"]}',
                flush=True,
            )

        # Build and save manifest
        manifest = {
            'course_name': 'Akamonkai 12-Week Beginner Course',
            'total_lessons': len(links),
            'type_counts': type_counts,
            'sections': sections,
            'lessons': links,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

        with open(CONTENT / 'manifest.json', 'w') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        print(f'\nManifest saved: {len(links)} lessons, {len(sections)} sections', flush=True)

        await ctx.close()
        print('Done!', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
