#!/usr/bin/env python3
"""Fix TypeScript build errors automatically."""
import re
import sys

def fix_file(filepath):
    """Fix TypeScript errors in a file."""
    with open(filepath, 'r') as f:
        content = f.read()

    original = content

    # Fix FormEvent imports - change to type-only imports
    content = re.sub(
        r"import \{ (.*?)FormEvent(.*?) \} from 'react';",
        lambda m: f"import {{ {m.group(1).strip()}}} from 'react';\nimport type {{ FormEvent }} from 'react';" if m.group(1).strip() or m.group(2).strip().replace(',', '').strip() else "import type { FormEvent } from 'react';",
        content
    )

    # Remove unused imports/variables
    lines = content.split('\n')
    new_lines = []

    for line in lines:
        # Skip lines with unused imports
        if ('Maximize2' in line and "import" in line) or \
           ('React' in line and "import React" in line and 'React,' not in line):
            # Check if it's only importing unused things
            continue

        # Remove unused variable declarations
        if 'const maskKey' in line:
            continue
        if 'const data =' in line and 'PhotoFeedbackCard' in filepath:
            continue
        if 'const issue' in line and 'Issues.tsx' in filepath:
            continue
        if 'const newSeverity' in line and 'Issues.tsx' in filepath:
            continue
        if 'const isAdmin' in line and 'SiteDetail.tsx' in filepath:
            continue
        if 'handleSaveAndClose' in line and 'SiteDetail.tsx' in filepath:
            continue
        if 'handleDiscardAndClose' in line and 'SiteDetail.tsx' in filepath:
            continue
        if 'adminToursApi' in line and "import" in line and 'TourDetail.tsx' in filepath:
            continue

        new_lines.append(line)

    content = '\n'.join(new_lines)

    # Only write if changed
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False

# Files to fix
files = [
    'src/pages/Login.tsx',
    'src/pages/SiteDetail.tsx',
    'src/pages/TourDetail.tsx',
    'src/pages/UserDetail.tsx',
    'src/components/improvements/PhotoFeedbackCard.tsx',
    'src/pages/ApiKeys.tsx',
    'src/pages/Issues.tsx',
    'src/pages/Improvements.tsx',
    'src/pages/TopTours.tsx',
    'src/pages/TourRatings.tsx',
    'src/pages/Tours.tsx',
]

import os
os.chdir('/Users/craigboyce/Developer/Voyana/server-dev/tours-server/admin-dashboard')

for filepath in files:
    if os.path.exists(filepath):
        if fix_file(filepath):
            print(f"Fixed: {filepath}")
    else:
        print(f"Not found: {filepath}")
