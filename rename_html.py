import os
import shutil

frontend = r'C:\Users\samsung\dev\finance\frontend'

files = ['index', 'dashboard', 'operations', 'funds', 'accounts', 'categories']

for f in files:
    old_path = os.path.join(frontend, f'{f}.html')
    backup_path = os.path.join(frontend, f'{f}-old.html')
    new_path = os.path.join(frontend, f'{f}-new.html')
    
    # Backup old if exists
    if os.path.exists(old_path):
        shutil.move(old_path, backup_path)
        print(f'Backed up: {f}.html -> {f}-old.html')
    
    # Rename new to main
    if os.path.exists(new_path):
        shutil.move(new_path, old_path)
        print(f'Activated: {f}-new.html -> {f}.html')

print('\nDone!')
print('\nCurrent files:')
for f in sorted(os.listdir(frontend)):
    if f.endswith('.html'):
        size = os.path.getsize(os.path.join(frontend, f))
        print(f'  {f}: {size:,} bytes')
