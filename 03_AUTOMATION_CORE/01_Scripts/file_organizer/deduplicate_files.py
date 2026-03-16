#!/usr/bin/env python3
"""
Enhanced File Deduplication Script
Finds and removes duplicate files based on content hash
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
import argparse

def get_file_hash(filepath, algorithm='md5'):
    """Calculate hash of file content"""
    hasher = hashlib.new(algorithm)

    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        print(f"  ⚠️  Error hashing {filepath}: {e}")
        return None

def find_duplicates(root_dir, min_size=0):
    """Find all duplicate files"""
    print(f"🔍 Scanning {root_dir} for duplicates...")

    # First pass: group by size (fast)
    size_map = defaultdict(list)
    file_count = 0

    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            filepath = Path(dirpath) / filename

            try:
                size = filepath.stat().st_size

                if size >= min_size:
                    size_map[size].append(filepath)
                    file_count += 1

                    if file_count % 1000 == 0:
                        print(f"  Scanned {file_count} files...", end='\r')
            except:
                pass

    print(f"  Scanned {file_count} files total.          ")

    # Second pass: hash files with same size
    print("🔐 Calculating hashes for potential duplicates...")

    hash_map = defaultdict(list)
    files_to_hash = [f for files in size_map.values() if len(files) > 1 for f in files]

    for i, filepath in enumerate(files_to_hash):
        file_hash = get_file_hash(filepath)

        if file_hash:
            hash_map[file_hash].append(filepath)

        if (i + 1) % 100 == 0:
            print(f"  Hashed {i + 1}/{len(files_to_hash)} files...", end='\r')

    print(f"  Hashed {len(files_to_hash)} files total.          ")

    # Filter to only duplicates
    duplicates = {h: files for h, files in hash_map.items() if len(files) > 1}

    return duplicates

def choose_file_to_keep(files):
    """Choose which file to keep (prefer shortest path, oldest file)"""
    # Sort by: path length (shorter first), then modification time (older first)
    sorted_files = sorted(files, key=lambda f: (len(str(f)), f.stat().st_mtime))
    return sorted_files[0]

def delete_duplicates(duplicates, dry_run=True):
    """Delete duplicate files, keeping one copy"""
    total_size_saved = 0
    total_deleted = 0

    for file_hash, files in duplicates.items():
        # Choose file to keep
        keep_file = choose_file_to_keep(files)
        delete_files = [f for f in files if f != keep_file]

        print(f"\n📄 {keep_file.name} ({len(files)} copies)")
        print(f"  ✓ Keep: {keep_file}")

        for delete_file in delete_files:
            size = delete_file.stat().st_size

            if dry_run:
                print(f"  [DRY RUN] Would delete: {delete_file} ({size / 1024:.1f} KB)")
            else:
                try:
                    delete_file.unlink()
                    print(f"  🗑️  Deleted: {delete_file} ({size / 1024:.1f} KB)")
                    total_size_saved += size
                    total_deleted += 1
                except Exception as e:
                    print(f"  ❌ Error deleting {delete_file}: {e}")

    return total_deleted, total_size_saved

def main():
    parser = argparse.ArgumentParser(description="Find and remove duplicate files")
    parser.add_argument('--root', type=str,
                       default='/mnt/sdcard/AA_MY_DRIVE/A_Rich',
                       help='Root directory to scan')
    parser.add_argument('--min-size', type=int, default=1024,
                       help='Minimum file size in bytes (default: 1KB)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually delete duplicates (default is dry run)')
    parser.add_argument('--yes', action='store_true',
                       help='Skip confirmation prompt')

    args = parser.parse_args()

    root_dir = Path(args.root)
    dry_run = not args.execute

    print("=" * 60)
    print("  FILE DEDUPLICATION")
    print("=" * 60)
    print(f"Root: {root_dir}")
    print(f"Min size: {args.min_size} bytes")
    print(f"Mode: {'DRY RUN (no deletions)' if dry_run else 'EXECUTE (will delete)'}")
    print()

    # Find duplicates
    duplicates = find_duplicates(root_dir, args.min_size)

    if not duplicates:
        print("\n✓ No duplicate files found!")
        return

    # Calculate statistics
    total_files = sum(len(files) for files in duplicates.values())
    total_duplicates = total_files - len(duplicates)

    print(f"\n📊 Found {len(duplicates)} unique files with duplicates")
    print(f"   Total duplicate copies: {total_duplicates}")

    # Confirm deletion
    if not dry_run and not args.yes:
        print("\n⚠️  WARNING: This will permanently delete files!")
        response = input("Continue? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Aborted.")
            return

    # Delete duplicates
    deleted_count, size_saved = delete_duplicates(duplicates, dry_run)

    print("\n" + "=" * 60)
    print(f"{'[DRY RUN] ' if dry_run else ''}SUMMARY")
    print("=" * 60)

    if dry_run:
        print(f"Would delete: {total_duplicates} duplicate files")
        # Estimate size
        estimated_size = sum(f.stat().st_size for files in duplicates.values()
                           for f in files[1:])
        print(f"Would save: {estimated_size / (1024**2):.1f} MB")
        print("\n⚠️  This was a DRY RUN. No files deleted.")
        print("Run with --execute to actually delete duplicates.")
    else:
        print(f"Deleted: {deleted_count} duplicate files")
        print(f"Space saved: {size_saved / (1024**2):.1f} MB")

if __name__ == "__main__":
    main()
