import subprocess
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent
python = backend / 'venv' / 'Scripts' / 'python.exe'

for test in ['translate', 'device_sync']:
    print('RUNNING', test)
    result = subprocess.run(
        [str(python), '-m', 'pytest', 'tests/test_chat_advancement.py', '-q', '-k', test],
        cwd=str(backend),
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    print('---ERR---')
    print(result.stderr)
    print('---RET---', result.returncode)
    print('===============================')
    if result.returncode != 0:
        sys.exit(result.returncode)
