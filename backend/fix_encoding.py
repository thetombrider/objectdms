#!/usr/bin/env python3
"""Script to fix file encodings by removing null bytes."""

import os
import sys
import codecs

def fix_file_encoding(file_path):
    """Fix file encoding by removing null bytes and ensuring UTF-8."""
    try:
        # Read the file in binary mode
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Remove BOM and null bytes
        if content.startswith(codecs.BOM_UTF8):
            content = content[len(codecs.BOM_UTF8):]
        content = content.replace(b'\x00', b'')
        content = content.replace(b'\xff\xfe', b'')  # UTF-16 BOM
        content = content.replace(b'\xfe\xff', b'')  # UTF-16 BOM (BE)
        
        # Try to decode and re-encode to ensure valid UTF-8
        try:
            decoded = content.decode('utf-8', errors='ignore')
        except UnicodeDecodeError:
            # If UTF-8 fails, try other encodings
            for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                try:
                    decoded = content.decode(encoding, errors='ignore')
                    break
                except UnicodeDecodeError:
                    continue
        
        # Write back with proper UTF-8 encoding
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(decoded)
        
        print(f"Fixed encoding for {file_path}")
        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}", file=sys.stderr)
        return False

def main():
    """Main function."""
    # Get all Python files
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                fix_file_encoding(file_path)

if __name__ == '__main__':
    main() 