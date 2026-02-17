#!/usr/bin/env python3
"""
Production-grade PDF splitter script using PyMuPDF (fitz).
Enhanced with user input validation and intelligent page range management.

Features:
- Maximum 500 pages per PDF
- User-defined number of splits
- Custom naming or auto-naming
- Page range validation with overlap detection
- Comprehensive error handling

Requirements:
- PyMuPDF (fitz): pip install PyMuPDF
- Python 3.7+

Author: AI Assistant
Version: 1.0
"""

import sys
import os
import argparse
import hashlib
import time
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import fitz  # PyMuPDF

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pdf_splitter.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class PDFSplitterError(Exception):
    """Custom exception for PDF splitter operations."""
    pass


class EnhancedPDFSplitter:
    """
    Enhanced production-grade PDF splitter with robust features.

    Features:
    - User input validation
    - Page range overlap detection
    - Custom naming or auto-naming
    - Comprehensive error handling
    - Cross-platform compatibility
    """

    # Constants for validation
    MAX_PAGES_PER_PDF = 500
    OUTPUT_FOLDER = "output"
    INPUT_FOLDER = "input"

    def __init__(self):
        """Initialize the enhanced PDF splitter."""
        self.input_file: Optional[Path] = None
        self.output_dir: Path = Path(self.OUTPUT_FOLDER)
        self.input_dir: Path = Path(self.INPUT_FOLDER)
        self.setup_directories()

    def setup_directories(self):
        """Setup input and output directories with proper error handling."""
        try:
            # Create input directory if it doesn't exist
            self.input_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Input directory ready: {self.input_dir.absolute()}")

            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Output directory ready: {self.output_dir.absolute()}")

        except Exception as e:
            raise PDFSplitterError(f"Failed to setup directories: {str(e)}")

    def discover_input_pdfs(self) -> List[Path]:
        """
        Discover PDF files in the input directory.
        
        Returns:
            List[Path]: List of valid PDF file paths
        """
        try:
            # Find all PDF files in input directory (case insensitive)
            pdf_files = set()
            pdf_files.update(self.input_dir.glob("*.pdf"))
            pdf_files.update(self.input_dir.glob("*.PDF"))

            # Convert back to list
            pdf_files = list(pdf_files)

            if not pdf_files:
                logger.warning(f"No PDF files found in {self.input_dir}")
                return []

            # Keep files in folder order (no sorting)
            logger.info(f"Discovered {len(pdf_files)} PDF files in input directory")
            for pdf_file in pdf_files:
                logger.info(f"  - {pdf_file.name}")

            return pdf_files

        except Exception as e:
            logger.error(f"Error discovering PDF files: {e}")
            return []

    def validate_pdf_file(self, file_path: str) -> int:
        """
        Validate PDF file and return page count.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            int: Number of pages in the PDF
            
        Raises:
            PDFSplitterError: If file is invalid or exceeds constraints
        """
        try:
            if not os.path.exists(file_path):
                raise PDFSplitterError(f"File not found: {file_path}")

            # Open and validate PDF
            doc = fitz.open(file_path)
            page_count = len(doc)

            # Check page count limit
            if page_count > self.MAX_PAGES_PER_PDF:
                doc.close()
                raise PDFSplitterError(
                    f"PDF has {page_count} pages, exceeding the limit of {self.MAX_PAGES_PER_PDF} pages."
                )

            # Check if PDF is password protected
            if doc.needs_pass:
                doc.close()
                raise PDFSplitterError("PDF is password protected and cannot be processed.")

            doc.close()
            return page_count

        except fitz.FileDataError:
            raise PDFSplitterError(f"File '{file_path}' is not a valid PDF or is corrupted.")
        except fitz.FileNotFoundError:
            raise PDFSplitterError(f"PDF file not found: {file_path}")
        except PDFSplitterError:
            raise  # Re-raise our custom errors
        except Exception as e:
            raise PDFSplitterError(f"Error validating PDF '{file_path}': {str(e)}")

    def get_user_input(self) -> Tuple[str, int, List[str], List[Tuple[int, int]]]:
        """
        Get user input for PDF splitting parameters.
        
        Returns:
            Tuple[str, int, List[str], List[Tuple[int, int]]]: 
            (input_file, num_splits, custom_names, page_ranges)
        """
        print("🎯 Enhanced PDF Splitter - Input Folder Processing")
        print("=" * 60)
        print("This tool processes PDFs from the 'input' folder automatically.")
        print("=" * 60)
        
        # Discover PDF files from input folder
        pdf_files = self.discover_input_pdfs()
        
        if not pdf_files:
            print(f"❌ No PDF files found in input folder.")
            print(f"Please add PDF files to: {self.input_dir.absolute()}")
            return None, 0, [], []

        print(f"✓ Found {len(pdf_files)} PDF files")
        
        # For now, process the first PDF file found
        # In the future, this could be extended to process multiple files
        input_file = str(pdf_files[0])
        
        try:
            page_count = self.validate_pdf_file(input_file)
            print(f"✓ Valid PDF file: {pdf_files[0].name} ({page_count} pages)")
        except PDFSplitterError as e:
            print(f"❌ {str(e)}")
            return None, 0, [], []

        # Get number of splits
        while True:
            try:
                num_splits = int(input(f"How many PDFs do you want to split into? (max {page_count}): "))
                if num_splits <= 0:
                    print("❌ Number of splits must be positive.")
                    continue
                if num_splits > page_count:
                    print(f"❌ Cannot split {page_count} pages into {num_splits} files.")
                    continue
                break
            except ValueError:
                print("❌ Please enter a valid number.")

        # Get custom names or use auto-naming
        custom_names = []
        use_custom_names = input("Do you want to provide custom names for split files? (y/n): ").lower().strip()
        
        if use_custom_names in ['y', 'yes']:
            print("Enter custom names for each split file:")
            for i in range(num_splits):
                while True:
                    name = input(f"Name for split {i+1}: ").strip()
                    if name:
                        # Remove .pdf extension if user included it
                        if name.lower().endswith('.pdf'):
                            name = name[:-4]
                        custom_names.append(name)
                        break
                    else:
                        print("❌ Please enter a valid name.")
        else:
            # Use auto-naming
            base_name = Path(input_file).stem
            custom_names = [f"{base_name}.split[{i+1}]" for i in range(num_splits)]

        # Get page ranges
        page_ranges = []
        print(f"\nEnter page ranges for each split (0-based indexing, max page: {page_count-1}):")
        
        for i in range(num_splits):
            while True:
                try:
                    print(f"\nSplit {i+1}: {custom_names[i]}")
                    
                    # Get start page
                    start_page = int(input(f"Start page (0-{page_count-1}): "))
                    if start_page < 0 or start_page >= page_count:
                        print(f"❌ Start page must be between 0 and {page_count-1}.")
                        continue

                    # Get end page (optional for last split)
                    if i == num_splits - 1:
                        # Last split - can go to end
                        end_input = input(f"End page (optional, press Enter for page {page_count-1}): ").strip()
                        if end_input:
                            end_page = int(end_input)
                        else:
                            end_page = page_count - 1
                    else:
                        # Not last split - must specify end page
                        end_page = int(input(f"End page: "))
                    
                    if end_page < start_page:
                        print("❌ End page must be greater than or equal to start page.")
                        continue
                    
                    if end_page >= page_count:
                        print(f"❌ End page cannot exceed {page_count-1}.")
                        continue

                    # Check for overlap with previous ranges
                    if i > 0:
                        prev_end = page_ranges[-1][1]
                        if start_page <= prev_end:
                            print(f"❌ Overlap detected! Previous range ends at page {prev_end}, "
                                  f"but this range starts at page {start_page}.")
                            continue

                    page_ranges.append((start_page, end_page))
                    print(f"✓ Range {i+1}: pages {start_page}-{end_page}")
                    break

                except ValueError:
                    print("❌ Please enter valid page numbers.")

        return input_file, num_splits, custom_names, page_ranges

    def generate_output_filename(self, base_filename: str) -> str:
        """
        Generate output filename with incremental numbering if file exists.
        
        Args:
            base_filename: Base filename without extension
            
        Returns:
            str: Available filename
        """
        counter = 0
        while True:
            if counter == 0:
                filename = f"{base_filename}.pdf"
            else:
                filename = f"{base_filename}[{counter}].pdf"
            
            output_path = self.output_dir / filename
            if not output_path.exists():
                return str(output_path)
            
            counter += 1

    def split_pdf(self, input_file: str, num_splits: int, custom_names: List[str], 
                  page_ranges: List[Tuple[int, int]]) -> List[str]:
        """
        Split PDF into multiple files based on user specifications.
        
        Args:
            input_file: Path to input PDF file
            num_splits: Number of splits to create
            custom_names: List of custom names for output files
            page_ranges: List of (start_page, end_page) tuples
            
        Returns:
            List[str]: List of output file paths
            
        Raises:
            PDFSplitterError: If splitting fails
        """
        try:
            output_files = []
            
            # Open source document
            source_doc = fitz.open(input_file)
            print(f"\nStarting PDF split process...")
            print(f"Source file: {input_file}")
            print(f"Total pages: {len(source_doc)}")
            
            # Process each split
            for i in range(num_splits):
                start_page, end_page = page_ranges[i]
                custom_name = custom_names[i]
                
                print(f"\nProcessing split {i+1}/{num_splits}: {custom_name}")
                print(f"  Pages: {start_page}-{end_page} ({end_page - start_page + 1} pages)")
                
                # Create new document for this split
                split_doc = fitz.open()
                
                # Copy pages from source to split document
                split_doc.insert_pdf(source_doc, from_page=start_page, to_page=end_page)
                
                # Generate output filename
                output_filename = self.generate_output_filename(custom_name)
                output_path = Path(output_filename)
                
                # Save split document
                split_doc.save(output_filename)
                split_doc.close()
                
                output_files.append(output_filename)
                print(f"  ✓ Saved: {output_path.name}")
            
            # Close source document
            source_doc.close()
            
            return output_files
            
        except Exception as e:
            raise PDFSplitterError(f"Error during PDF splitting: {str(e)}")

    def process_splitting(self) -> None:
        """
        Main method to process PDF splitting with user interaction.
        """
        try:
            start_time = time.time()
            
            # Get user input
            input_file, num_splits, custom_names, page_ranges = self.get_user_input()
            
            # Check if we got valid input
            if input_file is None or num_splits == 0:
                print("❌ No valid input file found. Exiting.")
                return
            
            # Perform the split
            output_files = self.split_pdf(input_file, num_splits, custom_names, page_ranges)
            
            # Final report
            total_time = time.time() - start_time
            print(f"\n🎉 PDF splitting completed in {total_time:.2f}s")
            print(f"📊 Successfully created {len(output_files)} split files")
            print(f"📁 Output directory: {self.output_dir.absolute()}")
            
            print(f"\n📄 Split files created:")
            for i, output_file in enumerate(output_files, 1):
                file_path = Path(output_file)
                print(f"  {i}. {file_path.name}")

        except KeyboardInterrupt:
            print("\n⚠ Operation cancelled by user.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}")
            print(f"💥 Fatal error: {str(e)}")
            sys.exit(1)


def main():
    """Main entry point for the enhanced PDF splitter script."""
    try:
        splitter = EnhancedPDFSplitter()
        splitter.process_splitting()
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 