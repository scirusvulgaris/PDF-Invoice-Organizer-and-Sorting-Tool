#!/usr/bin/env python3.9
"""
PDF Invoice Organizer
=====================
Automatically sorts PDF invoices by date into organized folder structures.
Supports OCR for scanned documents and handles multiple languages.

Version: 2.0.0
Author: Enhanced by ChatLLM Teams
"""

import os
import re
import shutil
from datetime import datetime
import sys
import random
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile
import fitz
import easyocr
import io
from PIL import Image
import numpy as np
import traceback
import time
import argparse
from collections import defaultdict

# ANSI escape codes for colors
BLACK = '\033[30m'
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
WHITE = '\033[37m'
BOLD_BLACK = '\033[1;30m'
BOLD_RED = '\033[1;31m'
BOLD_GREEN = '\033[1;32m'
BOLD_YELLOW = '\033[1;33m'
BOLD_BLUE = '\033[1;34m'
BOLD_MAGENTA = '\033[1;35m'
BOLD_CYAN = '\033[1;36m'
BOLD_WHITE = '\033[1;37m'
UNDERLINE_BLACK = '\033[4;30m'
UNDERLINE_RED = '\033[4;31m'
UNDERLINE_GREEN = '\033[4;32m'
UNDERLINE_YELLOW = '\033[4;33m'
RESET = '\033[0m'  # Reset to default color

# Global configuration
VERSION = "2.0.0"
VERBOSE = False
DRY_RUN = False
STATS = {
    'total_files': 0,
    'sorted_files': 0,
    'unsorted_files': 0,
    'ocr_processed': 0,
    'commande_files': 0,
    'errors': 0,
    'zip_extracted': 0,
    'start_time': None,
    'end_time': None
}


def print_banner():
    banner = f"""
{BOLD_CYAN}╔═══════════════════════════════════════════════════════════╗
║           PDF Invoice Organizer v{VERSION}                ║
║     Automatic invoice sorting with OCR support           ║
╚═══════════════════════════════════════════════════════════╝{RESET}
"""
    print(banner)


def print_help():
    """Display comprehensive help information."""
    help_text = f"""
{BOLD_WHITE}USAGE:{RESET}
    python script.py [OPTIONS] [YEAR] [KEYWORDS...]

{BOLD_WHITE}DESCRIPTION:{RESET}
    Automatically organizes PDF invoices by extracting dates and keywords.
    Supports OCR for scanned documents and handles multiple languages.

    The script will:
    1. Extract ZIP files in the current directory
    2. Scan for PDF files (up to 2 levels deep)
    3. Extract text or perform OCR on images
    4. Identify invoices by keywords
    5. Sort by date into: YYYY/Facture fournisseur/MM/
    6. Move non-invoices to 'commande' folder

{BOLD_WHITE}OPTIONS:{RESET}
    -h, --help          Show this help message and exit
    -v, --verbose       Enable verbose output with detailed processing info
    -d, --dry-run       Preview actions without moving files
    --version           Show version information
    --stats             Show detailed statistics at the end

{BOLD_WHITE}ARGUMENTS:{RESET}
    YEAR                Optional: Filter by specific year (e.g., 2023)
    KEYWORDS            Additional keywords to search for in PDFs
                        Default: facture, invoice, rechnung

{BOLD_WHITE}EXAMPLES:{RESET}
    {GREEN}# Basic usage - process all invoices{RESET}
    python script.py

    {GREEN}# Verbose mode with statistics{RESET}
    python script.py -v --stats

    {GREEN}# Filter by year 2023 with custom keywords{RESET}
    python script.py 2023 bill receipt

    {GREEN}# Dry run to preview without moving files{RESET}
    python script.py --dry-run -v

    {GREEN}# Add custom keywords{RESET}
    python script.py bill receipt nota

{BOLD_WHITE}SUPPORTED DATE FORMATS:{RESET}
    • dd/mm/yyyy, dd.mm.yyyy, dd-mm-yyyy
    • dd/mm/yy, dd.mm.yy
    • yyyy-mm-dd
    • dd Mon yyyy (e.g., 13 Jul 2023)
    • French months (janvier, février, etc.)

{BOLD_WHITE}DEFAULT KEYWORDS:{RESET}
    • facture, invoice, rechnung (German)
    • facturation, repas

{BOLD_WHITE}FOLDER STRUCTURE:{RESET}
    Current Directory/
    ├── 2023/
    │   └── Facture fournisseur/
    │       ├── 01/  (January invoices)
    │       ├── 02/  (February invoices)
    │       └── ...
    ├── 2024/
    │   └── Facture fournisseur/
    │       └── ...
    └── commande/  (Non-invoice documents)

{BOLD_WHITE}REQUIREMENTS:{RESET}
    • Python 3.7+
    • PyMuPDF (fitz)
    • easyocr
    • Pillow (PIL)
    • numpy

{BOLD_WHITE}NOTES:{RESET}
    • OCR is automatically triggered for image-based PDFs
    • Duplicate filenames get a random suffix
    • Empty folders are cleaned up automatically
    • Multi-threaded processing for better performance
"""
    print(help_text)


def verbose_print(message, color=""):

    if VERBOSE:
        print(f"{color}{message}{RESET}")


def extract_month_from_french(text):

    months_french = {
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
    }
    for month, number in months_french.items():
        if month in text.lower():
            words = text.split()
            year = next((int(word) for word in words if word.isdigit() and len(word) == 4), None)
            if year:
                verbose_print(f"  → Found French date: {month} {year}", CYAN)
                return f"01/{number:02d}/{year}"
    return None


def extract_date_from_text(text):

    current_year = datetime.now().year
    min_year = 1900
    max_year = current_year + 1

    date_formats = [
        # Four-digit year formats (YYYY)
        r'(0[1-9]|[1-2][0-9]|3[01])/(0[1-9]|1[0-2])/(20[0-9]{2})',
        r'(0[1-9]|[1-2][0-9]|3[01])\.(0[1-9]|1[0-2])\.(20[0-9]{2})',
        r'(0[1-9]|[1-2][0-9]|3[01])[\s](0[1-9]|1[0-2])[\s](20[0-9]{2})',
        r'(0[1-9]|[1-2][0-9]|3[01])-(0[1-9]|1[0-2])-(20[0-9]{2})',
        r'(20[0-9]{2})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])',
        # Two-digit year formats (YY)
        r'(0[1-9]|[1-2][0-9]|3[01])/(0[1-9]|1[0-2])/([0-9]{2})(?=[\s\-:]|$)',
        r'(0[1-9]|[1-2][0-9]|3[01])\.(0[1-9]|1[0-2])\.([0-9]{2})(?=[\s\-:]|$)',
        r'(0[1-9]|[1-2][0-9]|3[01])[\s](0[1-9]|1[0-2])[\s]([0-9]{2})(?=[\s\-:]|$)',
        r'(0[1-9]|[1-2][0-9]|3[01])-(0[1-9]|1[0-2])-([0-9]{2})(?=[\s\-:]|$)',
        # Month name formats
        r'(0[1-9]|[1-2][0-9]|3[01])\s[A-Za-z]{3}\.?\s(20[0-9]{2})',
        r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s(0[1-9]|1[0-2]),\s(20[0-9]{2})'
    ]

    for date_format in date_formats:
        date_match = re.search(date_format, text)
        if date_match:
            matched_text = date_match.group(0).strip()
            # Clean up the matched text - remove trailing characters after time separator
            if '-' in matched_text and ':' in matched_text:
                # Handle format like "25/04/25-14:14:28" - extract just the date part
                matched_text = matched_text.split('-')[0].strip()
            
            # Try all possible date formats
            for fmt in ('%d/%m/%Y', '%d.%m.%Y', '%d-%m-%Y', '%d/%m/%y', '%d.%m.%y', '%d-%m-%y', 
                        '%d %m %Y', '%d %m %y', '%d %b %Y', '%Y-%m-%d'):
                try:
                    date_obj = datetime.strptime(matched_text, fmt)
                    if fmt.endswith('%y'):
                        year = 2000 + (date_obj.year % 100)
                    else:
                        year = date_obj.year

                    if min_year <= year <= max_year:
                        verbose_print(f"  → Extracted date: {date_obj.month:02d}/{year} (from: {matched_text})", CYAN)
                        return date_obj.month, year
                    else:
                        continue
                except ValueError:
                    continue

    french_date = extract_month_from_french(text)
    if french_date:
        try:
            date_obj = datetime.strptime(french_date, "%d/%m/%Y")
            return date_obj.month, date_obj.year
        except ValueError:
            pass
    return None, None


def generate_random_suffix(size=3, chars=string.ascii_letters + string.digits):

    return ''.join(random.choice(chars) for _ in range(size))


def contains_undesired_keywords(text, specific_keywords=["ceci n'est pas une facture"]):

    return any(keyword.lower() in text for keyword in specific_keywords)


def contains_desired_keywords(text, specific_keywords=["facture", "invoice", "rechnung", "facturation", "repas"]):

    found = any(keyword.lower() in text for keyword in specific_keywords)
    if found and VERBOSE:
        matched = [kw for kw in specific_keywords if kw.lower() in text]
        verbose_print(f"  → Found keywords: {', '.join(matched)}", GREEN)
    return found


def process_pdf_file(filepath, year, keywords, unsorted_files, stats_lock):

    verbose_print(f"\n{BOLD_WHITE}Processing:{RESET} {os.path.basename(filepath)}", BOLD_WHITE)

    reader = easyocr.Reader(['en'])
    text = ""
    ocr_used = False

    try:
        with fitz.open(filepath) as pdf:
            verbose_print(f"  → Pages: {len(pdf)}", BLUE)

            for page_number, page in enumerate(pdf):
                page_text = page.get_text()
                if page_text:
                    text += page_text.replace('\n', ' ').lower()
                    verbose_print(f"  → Page {page_number + 1}: Extracted {len(page_text)} characters", BLUE)
                else:
                    verbose_print(f"  → Page {page_number + 1}: No text found, initiating OCR...", YELLOW)
                    image_list = page.get_images(full=True)

                    for image_index, img in enumerate(image_list):
                        verbose_print(f"    → OCR processing image {image_index + 1}/{len(image_list)}", CYAN)
                        xref = img[0]
                        base_image = pdf.extract_image(xref)
                        image_bytes = base_image["image"]
                        image = Image.open(io.BytesIO(image_bytes))
                        image = image.resize((image.width // 2, image.height // 2), Image.Resampling.LANCZOS)
                        image_np = np.array(image)
                        ocr_result = reader.readtext(image_np, detail=0, paragraph=True)
                        text += ' '.join(ocr_result).replace('\n', ' ').lower()
                        ocr_used = True

                        month, year_check = extract_date_from_text(text)
                        if month and (any(keyword.lower() in text for keyword in keywords) or contains_desired_keywords(text)):
                            break

            if ocr_used:
                with stats_lock:
                    STATS['ocr_processed'] += 1

            month, year_extracted = extract_date_from_text(text)

            if contains_undesired_keywords(text):
                target_folder_path = os.path.join(os.getcwd(), "commande")
                if not DRY_RUN:
                    os.makedirs(target_folder_path, exist_ok=True)
                    target_file_path = construct_target_file_path(target_folder_path, filepath)
                    shutil.move(filepath, target_file_path)
                print(f"  {YELLOW}→ Moved to 'commande' (non-invoice){RESET}: {os.path.basename(filepath)}")
                with stats_lock:
                    STATS['commande_files'] += 1
                    STATS['sorted_files'] += 1

            elif any(keyword.lower() in text for keyword in keywords) or contains_desired_keywords(text):
                if not month:
                    verbose_print(f"  {RED}✗ No date found{RESET}", RED)
                    unsorted_files.append(filepath)
                    with stats_lock:
                        STATS['unsorted_files'] += 1
                    return

                target_folder_path = os.path.join(os.getcwd(), str(year_extracted), "Facture fournisseur", f"{month:02d}")

                if not DRY_RUN:
                    os.makedirs(target_folder_path, exist_ok=True)
                    target_file_path = construct_target_file_path(target_folder_path, filepath)
                    shutil.move(filepath, target_file_path)
                    action = "Moved"
                else:
                    action = "Would move"

                print(f"  {GREEN}✓ {action}{RESET}: {os.path.basename(filepath)} → {BLUE}{month:02d}/{year_extracted}{RESET}")
                with stats_lock:
                    STATS['sorted_files'] += 1
            else:
                verbose_print(f"  {YELLOW}⚠ No invoice keywords found{RESET}", YELLOW)
                unsorted_files.append(filepath)
                with stats_lock:
                    STATS['unsorted_files'] += 1

    except Exception as e:
        print(f"  {RED}✗ Error:{RESET} {str(e)}")
        if VERBOSE:
            traceback.print_exc()
        unsorted_files.append(filepath)
        with stats_lock:
            STATS['errors'] += 1
            STATS['unsorted_files'] += 1


def construct_target_file_path(target_folder_path, filepath):

    target_file_path = os.path.join(target_folder_path, os.path.basename(filepath))
    if os.path.exists(target_file_path):
        base, extension = os.path.splitext(os.path.basename(filepath))
        new_filename = f"{base}_{generate_random_suffix()}{extension}"
        target_file_path = os.path.join(target_folder_path, new_filename)
        verbose_print(f"  → Duplicate detected, renamed to: {new_filename}", YELLOW)
    return target_file_path


def find_pdf_files(directory, max_depth=2):

    print(f"\n{BOLD_WHITE}Scanning for PDF files...{RESET}")
    pdf_files = []
    year_pattern = re.compile(r'^20\d{2}$')

    for root, dirs, files in os.walk(directory):
        current_level = root.count(os.path.sep)
        start_level = directory.rstrip(os.path.sep).count(os.path.sep)

        if current_level - start_level > max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if d.lower() != "commande" and not year_pattern.fullmatch(d)]
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
                    verbose_print(f"  Found: {file}", CYAN)

    return pdf_files


def unzip_files_in_directory(directory):

    zip_files = [f for f in os.listdir(directory) if f.endswith('.zip')]

    if zip_files:
        print(f"\n{BOLD_WHITE}Extracting ZIP files...{RESET}")
        for filename in zip_files:
            zip_path = os.path.join(directory, filename)
            print(f"  → Unzipping: {CYAN}{filename}{RESET}")
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(directory)
                print(f"  {GREEN}✓ Extracted{RESET}: {filename}")
                STATS['zip_extracted'] += 1
            except Exception as e:
                print(f"  {RED}✗ Error extracting {filename}: {e}{RESET}")


def delete_empty_folders(directory, max_depth=2):

    deleted_count = 0
    for root, dirs, files in os.walk(directory, topdown=False):
        if root != directory and (not os.listdir(root)):
            verbose_print(f"  Deleting empty folder: {root}", YELLOW)
            if not DRY_RUN:
                os.rmdir(root)
            deleted_count += 1

    if deleted_count > 0:
        print(f"\n{CYAN}Cleaned up {deleted_count} empty folder(s){RESET}")


def print_statistics():

    duration = STATS['end_time'] - STATS['start_time']

    print(f"\n{BOLD_CYAN}{'='*60}")
    print(f"                    PROCESSING SUMMARY")
    print(f"{'='*60}{RESET}\n")

    print(f"{BOLD_WHITE}Files Processed:{RESET}")
    print(f"  Total PDFs found:        {BOLD_CYAN}{STATS['total_files']}{RESET}")
    print(f"  Successfully sorted:     {BOLD_GREEN}{STATS['sorted_files']}{RESET}")
    print(f"  Moved to 'commande':     {BOLD_YELLOW}{STATS['commande_files']}{RESET}")
    print(f"  Could not be sorted:     {BOLD_RED}{STATS['unsorted_files']}{RESET}")
    print(f"  Errors encountered:      {BOLD_RED}{STATS['errors']}{RESET}")

    print(f"\n{BOLD_WHITE}Processing Details:{RESET}")
    print(f"  OCR processed files:     {BOLD_MAGENTA}{STATS['ocr_processed']}{RESET}")
    print(f"  ZIP files extracted:     {BOLD_CYAN}{STATS['zip_extracted']}{RESET}")

    print(f"\n{BOLD_WHITE}Performance:{RESET}")
    print(f"  Total time:              {BOLD_CYAN}{duration:.2f} seconds{RESET}")
    if STATS['total_files'] > 0:
        avg_time = duration / STATS['total_files']
        print(f"  Average per file:        {BOLD_CYAN}{avg_time:.2f} seconds{RESET}")

    success_rate = (STATS['sorted_files'] / STATS['total_files'] * 100) if STATS['total_files'] > 0 else 0
    print(f"  Success rate:            {BOLD_GREEN}{success_rate:.1f}%{RESET}")

    print(f"\n{BOLD_CYAN}{'='*60}{RESET}\n")


def parse_arguments():

    parser = argparse.ArgumentParser(
        description='PDF Invoice Organizer - Automatically sort invoices by date',
        add_help=False
    )

    parser.add_argument('-h', '--help', action='store_true', help='Show help message')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('-d', '--dry-run', action='store_true', help='Preview without moving files')
    parser.add_argument('--version', action='store_true', help='Show version')
    parser.add_argument('--stats', action='store_true', help='Show detailed statistics')
    parser.add_argument('args', nargs='*', help='Year and keywords')

    return parser.parse_args()


def main():
    global VERBOSE, DRY_RUN

    args = parse_arguments()

    if args.help:
        print_help()
        sys.exit(0)

    if args.version:
        print(f"PDF Invoice Organizer v{VERSION}")
        sys.exit(0)

    VERBOSE = args.verbose
    DRY_RUN = args.dry_run

    print_banner()

    if DRY_RUN:
        print(f"{BOLD_YELLOW}⚠ DRY RUN MODE - No files will be moved{RESET}\n")

    # Parse year and keywords
    keywords = ["facture", "invoice", "fechnung", "ticket", "justificatif"]
    year = None

    if args.args and args.args[0].isdigit():
        year = int(args.args[0])
        keywords += [keyword.lower() for keyword in args.args[1:]]
        print(f"{BOLD_WHITE}Filter year:{RESET} {year}")
    else:
        keywords += [keyword.lower() for keyword in args.args]

    print(f"{BOLD_WHITE}Keywords:{RESET} {', '.join(keywords)}\n")

    STATS['start_time'] = time.time()

    # Extract ZIP files
    unzip_files_in_directory(os.getcwd())

    # Find PDF files
    pdf_files = find_pdf_files(os.getcwd())
    STATS['total_files'] = len(pdf_files)

    print(f"\n{BOLD_GREEN}Found {STATS['total_files']} PDF file(s) to process{RESET}")

    if STATS['total_files'] == 0:
        print(f"{YELLOW}No PDF files found in current directory.{RESET}")
        sys.exit(0)

    print(f"{BOLD_WHITE}Starting processing...{RESET}\n")
    print(f"{'─' * 60}\n")

    unsorted_files = []

    # Thread-safe lock for statistics
    from threading import Lock
    stats_lock = Lock()

    # Process files with thread pool
    with ThreadPoolExecutor(max_workers=(os.cpu_count()*2 or 1)) as executor:
        futures = {
            executor.submit(process_pdf_file, pdf, year, keywords, unsorted_files, stats_lock): pdf
            for pdf in pdf_files
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            progress = (completed / STATS['total_files']) * 100
            print(f"\n{CYAN}Progress: {completed}/{STATS['total_files']} ({progress:.1f}%){RESET}")

    # Clean up empty folders
    if not DRY_RUN:
        delete_empty_folders(os.getcwd(), max_depth=2)

    STATS['end_time'] = time.time()

    # Print results
    print(f"\n{'─' * 60}\n")

    if unsorted_files:
        print(f"{BOLD_YELLOW}⚠ The following {len(unsorted_files)} PDF file(s) could not be sorted:{RESET}\n")
        for filepath in unsorted_files:
            print(f"  • {os.path.basename(filepath)}")
    else:
        print(f"{BOLD_GREEN}✓ All PDF files have been sorted successfully!{RESET}")

    # Print statistics
    if args.stats or VERBOSE:
        print_statistics()
    else:
        duration = STATS['end_time'] - STATS['start_time']
        print(f"\n{CYAN}Completed in {duration:.2f} seconds{RESET}")
        print(f"{GREEN}Sorted: {STATS['sorted_files']}/{STATS['total_files']}{RESET}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}⚠ Process interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}✗ Fatal error: {e}{RESET}")
        if VERBOSE:
            traceback.print_exc()
        sys.exit(1)
