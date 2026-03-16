#!/bin/bash

# Define the base directory and specific user directory for organizing files
BASE_DIR="$HOME/Documents"
RICHGEE_DIR="$BASE_DIR/richgee"

# Define file extensions and their respective directories
EXTENSIONS=("org" "html" "csv" "pdf" "txt" "py")
EXT_DIRS=("Org Files" "HTML Files" "CSV Files" "PDF Files" "Text Files" "Python Files")

# Create the `richgee` directory if it doesn't exist
mkdir -p "$RICHGEE_DIR"

# Move all files from the base Documents directory to the `richgee` directory
find "$BASE_DIR" -maxdepth 1 -type f -exec mv {} "$RICHGEE_DIR" \;

# Function to organize files by extension within the `richgee` directory
organize_files() {
    local ext="$1"
    local ext_dir="$2"

    # Make sure the extension-specific folder exists
    mkdir -p "$RICHGEE_DIR/$ext_dir"

    # Move files of the specific extension to the designated folder
    find "$RICHGEE_DIR" -maxdepth 1 -type f -name "*.$ext" -exec mv {} "$RICHGEE_DIR/$ext_dir/" \;
}

# Organize files by each extension within the `richgee` directory, except for shell scripts
for i in "${!EXTENSIONS[@]}"; do
    organize_files "${EXTENSIONS[$i]}" "${EXT_DIRS[$i]}"
done

echo "File organization completed for richgee at $RICHGEE_DIR"

