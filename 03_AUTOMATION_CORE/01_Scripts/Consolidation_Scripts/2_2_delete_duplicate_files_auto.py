import os
import hashlib
import argparse

parser = argparse.ArgumentParser(description="Find and delete duplicate files.")
parser.add_argument("directory", type=str, help="Directory to scan for duplicates")
parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
parser.add_argument("-a", "--auto-delete", action="store_true", help="Automatically delete duplicates without confirmation")
args = parser.parse_args()

def chunk_reader(f, chunk_size=4096):
    """Reads a file in chunks."""
    while True:
        chunk = f.read(chunk_size)
        if not chunk:
            break
        yield chunk

def find_duplicate_files(directory, verbose=False):
    """Finds duplicate files in the given directory based on file hash."""
    file_hashes = {}
    duplicates = []

    for root, directories, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)

            if verbose:
                print(f"Processing file: {filepath}")

            with open(filepath, 'rb') as f:
                hasher = hashlib.md5()
                for chunk in chunk_reader(f):
                    hasher.update(chunk)
                file_hash = hasher.hexdigest()

            if file_hash in file_hashes:
                duplicates.append((file_hashes[file_hash], filepath))
            else:
                file_hashes[file_hash] = filepath

    return duplicates

def delete_duplicates(duplicates):
    """Prompts for confirmation before deleting each duplicate file (or automatically deletes if -a flag is used)."""
    if args.auto_delete:
        for original, duplicate in duplicates:
            os.remove(duplicate)
            print(f"Duplicate file {duplicate} deleted.")
    else:
        for original, duplicate in duplicates:
            print(f"Original file: {original}")
            print(f"Duplicate file: {duplicate}")

            confirmation = input("Delete duplicate? (y/n): ")
            if confirmation.lower() == 'y':
                os.remove(duplicate)
                print(f"Duplicate file {duplicate} deleted.")
            else:
                print("Skipping deletion.")

if __name__ == '__main__':
    duplicates = find_duplicate_files(args.directory, verbose=args.verbose)

    if duplicates:
        print("Duplicate files found:")
        delete_duplicates(duplicates)
    else:
        print("No duplicate files found.")
