import os
import json

repo = os.path.abspath(os.path.dirname(__file__))
comment_style = {
    '.py': ('#', ''),
    '.env': ('#', ''),
    '.ini': ('#', ''),
    '.toml': ('#', ''),
    '.txt': ('#', ''),
    '.cfg': ('#', ''),
    '.md': ('<!--', '-->'),
    '.yml': ('#', ''),
    '.yaml': ('#', ''),
    '.sh': ('#', ''),
    '.bash': ('#', ''),
    '.zsh': ('#', ''),
    '.js': ('//', ''),
    '.jsx': ('//', ''),
    '.ts': ('//', ''),
    '.tsx': ('//', ''),
    '.css': ('/*', '*/'),
    '.scss': ('/*', '*/'),
    '.html': ('<!--', '-->'),
    '.vue': ('<!--', '-->'),
}
exclude_dirs = {'node_modules', '.git', 'venv', '.venv', '.idea', '.pytest_cache', '.cache'}
updated = []
for root, dirs, files in os.walk(repo):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for name in files:
        path = os.path.join(root, name)
        rel = os.path.relpath(path, repo).replace('\\', '/')
        ext = os.path.splitext(name)[1].lower()
        style = comment_style.get(ext)
        if style is None:
            continue
        prefix, suffix = style
        try:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception:
            continue
        if not content:
            continue
        comment_line = f"{prefix}{rel}{suffix}"
        lines = content.splitlines(True)
        if lines and lines[0].rstrip('\n') == comment_line:
            continue
        if lines and lines[0].startswith('#!'):
            lines.insert(1, comment_line + '\n')
        else:
            lines.insert(0, comment_line + '\n')
        with open(path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        updated.append(rel)
print('UPDATED', len(updated), 'files')
for u in updated[:100]:
    print(u)
