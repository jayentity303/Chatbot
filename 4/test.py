import re
import sys
import os
import tempfile
import webbrowser
import subprocess

def run_code(code: str, cleanup: bool = True):
    """
    Detects whether `code` is HTML or Python, writes it to a temp file,
    and executes/opens it accordingly.
    """
    # 1. Determine type
    is_html = bool(re.search(r'<!DOCTYPE\s+html>|<html|<body', code, re.IGNORECASE))
    
    # 2. Choose file settings
    suffix = '.html' if is_html else '.py'
    mode = 'w'
    
    # 3. Create temporary file
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode=mode, encoding='utf-8')
    temp.write(code)
    temp.close()
    
    try:
        if is_html:
            # 4a. Open HTML in default browser
            webbrowser.open(temp.name)
        else:
            # 4b. Execute Python in a subprocess
            subprocess.run([sys.executable, temp.name], check=True)
    except Exception as e:
        print(f"Error during execution: {e}")
    finally:
        # 5. Optional cleanup
        if cleanup:
            os.remove(temp.name)

if __name__ == '__main__':
    # Example usage:
    Code = input("Enter your code (HTML or Python):\n")
    run_code(Code)
