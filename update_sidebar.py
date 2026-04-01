import os
import re

frontend = r'C:\Users\samsung\dev\finance\frontend'

# Files to update
files = ['funds.html', 'accounts.html', 'categories.html']

for filename in files:
    filepath = os.path.join(frontend, filename)
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add categories link to sidebar-bottom if not present
    if 'onclick="location.href=\'categories.html\'"' not in content:
        # Find sidebar-bottom and add categories button before the first button
        old_pattern = r'(<div class="sidebar-bottom">\s*\n\s*<button class="nav-item" id="add-btn")'
        new_replacement = '''<div class="sidebar-bottom">
        <button class="nav-item" onclick="location.href='categories.html'">
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 14H8v-2h8v2zm0-4H8v-2h8v2zm0-4H8V6h8v2z"/>
            </svg>
            <span class="nav-tooltip">Справочники</span>
        </button>
        <button class="nav-item" id="add-btn'''
        
        content = re.sub(old_pattern, new_replacement, content)
    
    # Also check for logout-btn variant
    if 'onclick="location.href=\'categories.html\'"' not in content:
        old_pattern2 = r'(<div class="sidebar-bottom">\s*\n\s*<button class="nav-item" id="logout-btn")'
        new_replacement2 = '''<div class="sidebar-bottom">
        <button class="nav-item" onclick="location.href='categories.html'">
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 14H8v-2h8v2zm0-4H8v-2h8v2zm0-4H8V6h8v2z"/>
            </svg>
            <span class="nav-tooltip">Справочники</span>
        </button>
        <button class="nav-item" id="logout-btn'''
        
        content = re.sub(old_pattern2, new_replacement2, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f'Updated: {filename}')

print('Done!')
