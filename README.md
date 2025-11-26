# PDF Invoice Organizer 📄

Automatically sorts PDF invoices(facture) by date into organized folder structures with OCR support for scanned documents.

## ✨ Features

- **Automatic Date Extraction**: Supports multiple date formats (dd/mm/yyyy, dd-mm-yyyy, dd.mm.yyyy, etc.)
- **OCR Support**: Automatically processes scanned/image-based PDFs using EasyOCR
- **Multi-language**: Handles English, French, and German invoice keywords
- **Smart Organization**: Sorts invoices into `YYYY/Facture fournisseur/MM/` structure
- **Duplicate Handling**: Automatically renames duplicate files
- **ZIP Extraction**: Automatically extracts ZIP files before processing
- **Multi-threaded**: Fast processing using concurrent execution
- **Verbose Mode**: Detailed logging for debugging
- **Dry Run**: Preview changes without moving files
- **Statistics**: Comprehensive processing reports

## 📋 Requirements

- Python 3.7+
- PyMuPDF (fitz)
- easyocr
- Pillow (PIL)
- numpy

## 🚀 Installation

1. Clone or download this repository

2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## 📖 Usage

### Basic Usage

Process all PDF invoices in the current directory:

```bash
python script.py
```

### Verbose Mode

See detailed processing information:

```bash
python script.py -v
```

### Dry Run

Preview what would happen without moving files:

```bash
python script.py --dry-run -v
```

### With Statistics

Show detailed statistics after processing:

```bash
python script.py --stats
```

### Filter by Year

Process only invoices from a specific year:

```bash
python script.py 2024
```

### Custom Keywords

Add custom keywords to search for:

```bash
python script.py bill receipt nota
```

### Combined Options

```bash
python script.py -v --stats 2024 bill receipt
```

## 📁 Folder Structure

The script organizes invoices into the following structure:

```
Current Directory/
├── 2023/
│   └── Facture fournisseur/
│       ├── 01/  (January invoices)
│       ├── 02/  (February invoices)
│       ├── 03/  (March invoices)
│       └── ...
├── 2024/
│   └── Facture fournisseur/
│       ├── 01/
│       ├── 02/
│       └── ...
├── 2025/
│   └── Facture fournisseur/
│       └── ...
└── commande/  (Non-invoice documents)
```

## 🔍 Supported Date Formats

The script can extract dates in the following formats:

- **dd/mm/yyyy**: 25/04/2025, 14/02/2025
- **dd-mm-yyyy**: 25-04-2025, 14-02-2025
- **dd.mm.yyyy**: 25.04.2025, 14.02.2025
- **dd/mm/yy**: 25/04/25, 14/02/25
- **dd-mm-yy**: 25-04-25, 14-02-25
- **dd.mm.yy**: 25.04.25, 14.02.25
- **yyyy-mm-dd**: 2025-04-25, 2025-02-14
- **dd Mon yyyy**: 25 Apr 2025, 14 Feb 2025
- **French months**: janvier, février, mars, avril, mai, juin, juillet, août, septembre, octobre, novembre, décembre

### Date with Time

The script also handles dates with time components:
- `25/04/25-14:14:28`
- `du 14-02-2025 43:52:10`

## 🏷️ Default Keywords

The script searches for these keywords to identify invoices:

- **facture** (French)
- **invoice** (English)
- **rechnung** (German)
- **facturation** (French)
- **repas** (French - meal receipts)

You can add more keywords via command line arguments.

## ⚙️ Command Line Options

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-v, --verbose` | Enable verbose output with detailed processing info |
| `-d, --dry-run` | Preview actions without moving files |
| `--version` | Show version information |
| `--stats` | Show detailed statistics at the end |

## 📊 Example Output

### Normal Mode
```
╔═══════════════════════════════════════════════════════════╗
║           PDF Invoice Organizer v2.0.0                    ║
║     Automatic invoice sorting with OCR support           ║
╚═══════════════════════════════════════════════════════════╝

Keywords: facture, invoice, fechnung

Scanning for PDF files...

Found 15 PDF file(s) to process

Starting processing...
────────────────────────────────────────────────────────────

  ✓ Moved: invoice_2024_01.pdf → 01/2024

Progress: 1/15 (6.7%)

  ✓ Moved: facture_feb.pdf → 02/2024

Progress: 2/15 (13.3%)
...
```

### Verbose Mode
```
Processing: invoice_2024_01.pdf
  → Pages: 1
  → Page 1: Extracted 1250 characters
  → Found keywords: facture
  → Extracted date: 01/2024 (from: 15-01-2024)
  ✓ Moved: invoice_2024_01.pdf → 01/2024
```

### Statistics Output
```
============================================================
                    PROCESSING SUMMARY
============================================================

Files Processed:
  Total PDFs found:        15
  Successfully sorted:     13
  Moved to 'commande':     1
  Could not be sorted:     1
  Errors encountered:      0

Processing Details:
  OCR processed files:     3
  ZIP files extracted:     1

Performance:
  Total time:              45.23 seconds
  Average per file:        3.02 seconds
  Success rate:            86.7%

============================================================
```

## 🔧 How It Works

1. **ZIP Extraction**: Automatically extracts any ZIP files in the directory
2. **PDF Scanning**: Finds all PDF files (up to 2 levels deep)
3. **Text Extraction**: Extracts text from PDFs using PyMuPDF
4. **OCR Processing**: If no text found, uses EasyOCR on images
5. **Keyword Detection**: Searches for invoice-related keywords
6. **Date Extraction**: Extracts dates using regex patterns
7. **File Organization**: Moves files to appropriate folders
8. **Cleanup**: Removes empty folders

## 🐛 Troubleshooting

### No date found

If the script can't find a date, run with verbose mode to see what text was extracted:

```bash
python script.py -v
```

The verbose output will show:
```
→ No date found in text: [first 200 characters of extracted text]
```

### OCR not working

Make sure EasyOCR is properly installed:

```bash
pip install --upgrade easyocr
```

### Files not moving

Use dry-run mode to see what would happen:

```bash
python script.py --dry-run -v
```

## 📝 Notes

- The script skips folders named "commande" and year folders (2000-2099) during scanning
- Duplicate filenames get a random 3-character suffix
- Empty folders are automatically cleaned up after processing
- Multi-threaded processing uses all available CPU cores
- OCR processing is slower but automatic for image-based PDFs

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## 📄 License

This project is open source and available under the MIT License.
