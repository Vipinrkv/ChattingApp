import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def find_markdown_files(root_dir):
    md_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Skip common dependency and cache directories in-place to optimize traversal
        dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git", "venv", ".pytest_cache", "__pycache__", ".gemini", "dist")]
        for f in filenames:
            if f.endswith(".md"):
                md_files.append(Path(dirpath) / f)
    return md_files

def check_file_links(file_path):
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Could not read file: {e}"]

    # Match standard links: [label](url)
    links = re.findall(r'\[[^\]]*\]\(([^)]+)\)', content)
    errors = []
    for link in links:
        # Strip anchor fragment
        clean_link = link.split('#')[0].strip()
        if not clean_link:
            continue
        
        # Absolute local file URL
        if clean_link.startswith("file:///"):
            path_str = clean_link.replace("file:///", "")
            # Handle Windows paths (replace forward slash with backward if needed, or use Path direct)
            target_path = Path(path_str)
            if not target_path.exists():
                errors.append(f"Broken absolute link: {link}")
        # External web links are skipped for performance in offline validation
        elif clean_link.startswith(("http://", "https://", "mailto:", "ws://", "wss://")):
            continue
        else:
            # Relative local link
            target_path = file_path.parent / clean_link
            # Check relative exists
            if not target_path.exists():
                errors.append(f"Broken relative link: {link}")
    return errors

def main():
    print(f"Scanning markdown files in project root: {ROOT}")
    md_files = find_markdown_files(ROOT)
    total_errors = 0
    for f in md_files:
        errors = check_file_links(f)
        if errors:
            relative_path = f.relative_to(ROOT) if f.is_relative_to(ROOT) else f
            print(f"\nErrors in {relative_path}:")
            for err in errors:
                print(f"  - {err}")
                total_errors += 1
                
    if total_errors > 0:
        print(f"\nValidation failed with {total_errors} broken links.")
        sys.exit(1)
    else:
        print(f"\nAll links in {len(md_files)} markdown files verified successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
