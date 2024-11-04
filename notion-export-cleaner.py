import os
import re
import sys
import shutil
import tempfile
import zipfile
from urllib.parse import unquote, quote

def strip_notion_id(name):
    # Remove Notion IDs from filenames and folder names
    pattern = r'^(.*?)(\s[0-9a-f]{32})(\..+)?$'
    match = re.match(pattern, name)
    if match:
        name_without_id = match.group(1)
        extension = match.group(3) if match.group(3) else ''
        return f"{name_without_id}{extension}"
    return name

def path_depth(path):
    return path.count(os.sep)

def update_links_in_file(file_path, path_mapping):
    # Update links in files to reflect new filenames
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    updated = False

    for old_path, new_path in path_mapping.items():
        old_name = os.path.basename(old_path)
        new_name = os.path.basename(new_path)

        # Prepare patterns for different link formats
        patterns = [
            re.escape(quote(old_name)),
            re.escape(old_name),
        ]

        for pattern in patterns:
            # Replace all occurrences of the old filename with the new filename
            if re.search(pattern, content):
                content = re.sub(pattern, new_name, content)
                updated = True

    if updated:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)

def process_directory(root_directory):
    path_mapping = {}  # Map old full paths to new full paths

    # Step 1: Build mapping of old and new paths
    for root, dirs, files in os.walk(root_directory, topdown=False):
        # Process files
        for name in files:
            old_path = os.path.join(root, name)
            new_name = strip_notion_id(name)
            if new_name != name:
                new_path = os.path.join(root, new_name)
                path_mapping[old_path] = new_path
        # Process directories
        for name in dirs:
            old_path = os.path.join(root, name)
            new_name = strip_notion_id(name)
            if new_name != name:
                new_path = os.path.join(root, new_name)
                path_mapping[old_path] = new_path

    # Step 2: Sort and rename files and directories
    # Sorting ensures we rename the deepest paths first to avoid conflicts
    for old_path, new_path in sorted(path_mapping.items(), key=lambda x: path_depth(x[0]), reverse=True):
        try:
            os.rename(old_path, new_path)
        except OSError as e:
            print(f"Error renaming {old_path} to {new_path}: {e}")

    # Step 3: Update links in all text-based files
    # Define file extensions to process
    text_extensions = {'.md', '.html', '.txt'}

    for root, _, files in os.walk(root_directory):
        for name in files:
            _, ext = os.path.splitext(name)
            if ext.lower() in text_extensions:
                file_path = os.path.join(root, name)
                update_links_in_file(file_path, path_mapping)

def main():
    print("=== Notion Export Cleanup Tool ===\n")
    zip_file_path = input("Please enter the full path to your Notion-exported zip file:\n> ").strip().strip('"').strip("'")

    # Convert to absolute path
    zip_file_path = os.path.abspath(os.path.expanduser(zip_file_path))

    print(f"\nProcessing file: {zip_file_path}")

    if not os.path.isfile(zip_file_path):
        print("\nError: The file does not exist. Please check the path and try again.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    elif not zip_file_path.lower().endswith('.zip'):
        print("\nError: The provided file does not have a .zip extension.")
        input("\nPress Enter to exit...")
        sys.exit(1)

    # Create a temporary directory to work in
    with tempfile.TemporaryDirectory() as temp_dir:
        print("\nExtracting zip file...")
        # Extract the zip file
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
        except zipfile.BadZipFile:
            print("\nError: The zip file is corrupted or not a zip file.")
            input("\nPress Enter to exit...")
            sys.exit(1)
        except Exception as e:
            print(f"\nAn error occurred while extracting the zip file: {e}")
            input("\nPress Enter to exit...")
            sys.exit(1)

        print("Processing files...")
        # Process the extracted directory
        process_directory(temp_dir)

        # Create a new zip file without Notion IDs
        output_zip_path = os.path.splitext(zip_file_path)[0] + '_cleaned.zip'
        shutil.make_archive(os.path.splitext(output_zip_path)[0], 'zip', temp_dir)

        print(f"\nCleaned zip file created at:\n{output_zip_path}")
        input("\nProcessing complete. Press Enter to exit...")

if __name__ == "__main__":
    main()