#!/usr/bin/env python3
"""
Merge Duplicate Folders Script
Finds folders with same names and merges them intelligently
"""

import os
import shutil
from pathlib import Path
from collections import defaultdict
import hashlib

BASE_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/A_Rich")

def get_file_hash(filepath):
    """Calculate MD5 hash of file"""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return None

def find_duplicate_folders(root_dir):
    """Find all folders with same names"""
    folder_names = defaultdict(list)

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for dirname in dirnames:
            full_path = Path(dirpath) / dirname
            folder_names[dirname].append(full_path)

    # Filter to only duplicates
    duplicates = {name: paths for name, paths in folder_names.items()
                  if len(paths) > 1}

    return duplicates

def get_folder_info(folder_path):
    """Get info about folder contents"""
    file_count = 0
    total_size = 0

    for root, dirs, files in os.walk(folder_path):
        file_count += len(files)
        for f in files:
            try:
                total_size += (Path(root) / f).stat().st_size
            except:
                pass

    return file_count, total_size

def merge_folders(source, destination, dry_run=True):
    """Merge source folder into destination"""
    merged_files = []
    skipped_files = []

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Merging:")
    print(f"  Source: {source}")
    print(f"  Destination: {destination}")

    for root, dirs, files in os.walk(source):
        for filename in files:
            src_file = Path(root) / filename

            # Calculate relative path
            rel_path = src_file.relative_to(source)
            dst_file = destination / rel_path

            # Create destination directory if needed
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            # Check if file already exists
            if dst_file.exists():
                # Compare hashes
                src_hash = get_file_hash(src_file)
                dst_hash = get_file_hash(dst_file)

                if src_hash == dst_hash:
                    print(f"  ⊘ Skip (duplicate): {rel_path}")
                    skipped_files.append(str(rel_path))
                else:
                    # Files differ - keep both with suffix
                    new_name = dst_file.stem + "_merged" + dst_file.suffix
                    dst_file = dst_file.parent / new_name

                    if not dry_run:
                        shutil.copy2(src_file, dst_file)

                    print(f"  ↪ Copy (different): {rel_path} → {new_name}")
                    merged_files.append(str(rel_path))
            else:
                if not dry_run:
                    shutil.copy2(src_file, dst_file)

                print(f"  ✓ Copy: {rel_path}")
                merged_files.append(str(rel_path))

    return merged_files, skipped_files

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Merge duplicate folders")
    parser.add_argument('--execute', action='store_true',
                       help='Actually merge folders (default is dry run)')
    parser.add_argument('--root', type=str, default=str(BASE_DIR),
                       help='Root directory to scan')

    args = parser.parse_args()

    root_dir = Path(args.root)
    dry_run = not args.execute

    print("=" * 60)
    print("  DUPLICATE FOLDER MERGER")
    print("=" * 60)
    print(f"Root: {root_dir}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'EXECUTE (will merge)'}")
    print()

    # Find duplicates
    print("🔍 Scanning for duplicate folder names...")
    duplicates = find_duplicate_folders(root_dir)

    if not duplicates:
        print("✓ No duplicate folder names found!")
        return

    print(f"\n📊 Found {len(duplicates)} folder names with duplicates:\n")

    # Show duplicates
    merge_plan = []

    for folder_name, paths in sorted(duplicates.items()):
        print(f"📁 {folder_name} ({len(paths)} locations):")

        # Get info about each
        folder_info = []
        for path in paths:
            file_count, size = get_folder_info(path)
            folder_info.append((path, file_count, size))
            print(f"  - {path}")
            print(f"    Files: {file_count}, Size: {size / 1024:.1f} KB")

        # Determine merge strategy: merge into largest folder
        folder_info.sort(key=lambda x: x[2], reverse=True)
        destination = folder_info[0][0]
        sources = [info[0] for info in folder_info[1:]]

        print(f"  → Merge into: {destination}")

        merge_plan.append((folder_name, sources, destination))
        print()

    # Confirm
    if not dry_run:
        print("⚠️  WARNING: This will merge folders!")
        response = input("Continue? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Aborted.")
            return

    # Execute merges
    total_merged = 0
    total_skipped = 0

    for folder_name, sources, destination in merge_plan:
        for source in sources:
            merged, skipped = merge_folders(source, destination, dry_run)
            total_merged += len(merged)
            total_skipped += len(skipped)

            # Remove source folder if empty after merge
            if not dry_run:
                try:
                    if not any(source.iterdir()):
                        source.rmdir()
                        print(f"  🗑️  Removed empty folder: {source}")
                except:
                    pass

    print("\n" + "=" * 60)
    print(f"{'[DRY RUN] ' if dry_run else ''}SUMMARY")
    print("=" * 60)
    print(f"Folders merged: {len(merge_plan)}")
    print(f"Files merged: {total_merged}")
    print(f"Files skipped (duplicates): {total_skipped}")

    if dry_run:
        print("\n⚠️  This was a DRY RUN. No changes made.")
        print("Run with --execute to actually merge folders.")

if __name__ == "__main__":
    main()
