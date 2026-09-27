#!/usr/bin/env python3
"""Duplicate bronzewomanpart2.html -> bronzewomanpart3.html and point every
media asset at the Cloudflare R2 custom domain.

Design note: archive paths do TWO different jobs in this file -- (a) they are
real image URLs, and (b) they are lookup keys ('<folder>/<file>') into
window.TRANSLATIONS, ARCHIVE_CATEGORY_DATA and the index table. A blind
find-and-replace would corrupt (b), so this script rewrites only the places
where a path actually becomes a URL, and routes runtime path-building through
one assetURL()/thumbURL() pair.
"""
import re
import shutil
import sys
import pathlib

SRC = pathlib.Path('bronzewomanpart2.html')
DST = pathlib.Path('bronzewomanpart3.html')
BASE = 'https://assets.inhispresencearchive.com/'

# Directories that live in the R2 bucket (structure mirrors the project 1:1).
REMOTE_DIRS = [
    'Al-Kawakib', 'Al-Mawed', 'Al-Rissalah', 'Al-Thqafa', 'Al-alam',
    'Al-ethnayn wa Aldonya', 'Al-ethnayn wa aldonya 2', 'Al-ethnayn wa aldonya 3',
    'assest', 'thumbs', 'zawia', 'sreenshots', 'voice translation',
]

HELPERS = r"""<script>
  /* ───────── Remote asset host (Cloudflare R2) ─────────────────────────
     Every scan, thumbnail and photograph is served from the R2 bucket at
     ASSET_BASE, whose directory structure mirrors this project 1:1
     (Al-Mawed/…, thumbs/Al-Mawed/…, assest/…). Site code — archive_categories.js,
     kawakib_descriptions.js, Google Fonts — stays local/CDN and is NOT rewritten.

     Archive paths double as lookup keys ('<folder>/<file>' into
     window.TRANSLATIONS and the index table), so the *logical* path stays
     relative in the data and only becomes absolute at the moment it is
     assigned to an <img src>. assetURL() is idempotent, so handing it an
     already-absolute URL is safe. */
  const ASSET_BASE = 'https://assets.inhispresencearchive.com/';
  window.ASSET_BASE = ASSET_BASE;
  window.assetURL = function (p) {
    if (!p) return p;
    p = String(p);
    if (/^(?:https?:)?\/\//i.test(p) || /^data:/i.test(p) || /^blob:/i.test(p)) return p;
    return ASSET_BASE + p.replace(/^\.?\//, '');
  };
  // Same, but pointing at the 512px thumbnail mirror. `thumbs/` is inserted
  // *after* the host, so relative and already-absolute inputs both work.
  window.thumbURL = function (p) {
    if (!p) return p;
    var u = window.assetURL(p);
    if (/(^|\/)thumbs\//.test(u)) return u;
    return u.indexOf(ASSET_BASE) === 0
      ? ASSET_BASE + 'thumbs/' + u.slice(ASSET_BASE.length)
      : 'thumbs/' + u;
  };
  // ── Swap placeholder image paths"""

shutil.copyfile(SRC, DST)
s = DST.read_text(encoding='utf-8')
changes = []


def sub1(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit('FAILED [%s]: expected 1 occurrence, found %d' % (label, n))
    s = s.replace(old, new)
    changes.append('%s  (1 site)' % label)


# ── 1. Asset base + URL helpers, injected at the top of the main script ─────
sub1('<script>\n  // ── Swap placeholder image paths', HELPERS,
     'inject ASSET_BASE + assetURL()/thumbURL() helpers')

# ── 2. Every runtime <img src> assignment goes through the helpers ─────────
sub1("        if (cur && !/(^|\\/)thumbs\\//.test(cur)) img.src = THUMB_PREFIX + cur;",
     "        if (cur) img.src = window.thumbURL(cur);",
     'fixed-src story images -> thumbURL()')
sub1("      img.src = THUMB_PREFIX + paths[assignIdx % paths.length];",
     "      img.src = window.thumbURL(paths[assignIdx % paths.length]);",
     'canvas figure assignment -> thumbURL()')
sub1("        const src = THUMB_PREFIX + paths[used + i];",
     "        const src = window.thumbURL(paths[used + i]);",
     'generated extra figures -> thumbURL()')
sub1("      img.src = imagePool[Math.floor(Math.random() * imagePool.length)];",
     "      img.src = window.assetURL(imagePool[Math.floor(Math.random() * imagePool.length)]);",
     'intro cursor-trail docs -> assetURL()')

# ── 3. Static <img src="…"> attributes in the markup ───────────────────────
# Folder names contain spaces, which appear in this file both literally
# ("Al-ethnayn wa aldonya 3/…") and percent-encoded ("Al-ethnayn%20wa…"), so
# the directory pattern accepts either form.
dir_alt = '|'.join(
    re.escape(d).replace(r'\ ', '(?: |%20)') for d in REMOTE_DIRS
)

n_attr = [0]


def _attr(m):
    n_attr[0] += 1
    # Normalise to percent-encoded spaces so the emitted URL is valid as-is.
    return m.group(1) + BASE + m.group(2).replace(' ', '%20') + m.group(3)


s = re.sub(r'(\ssrc=")((?:%s)/[^"]+)(")' % dir_alt, _attr, s)
changes.append('static <img src="…"> attributes -> R2  (%d sites)' % n_attr[0])

# ── 4. CSS url(…) pointing at bucket media (inline data: URIs left alone) ──
n_css = [0]


def _css(m):
    n_css[0] += 1
    return m.group(1) + BASE + m.group(2).replace(' ', '%20')


s = re.sub(r"(url\(\s*['\"]?)((?:%s)/[^'\")]+)" % dir_alt, _css, s)
changes.append('CSS url(…) media references -> R2  (%d sites)' % n_css[0])

DST.write_text(s, encoding='utf-8')
print('Wrote %s\n' % DST)
for c in changes:
    print('  * ' + c)
