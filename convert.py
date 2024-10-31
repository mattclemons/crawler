import yaml
import requests
import pdfkit
from bs4 import BeautifulSoup
from tqdm import tqdm
import argparse
import os
from PyPDF2 import PdfMerger

# Load site structure from YAML file
def load_site_structure(filename):
    with open(filename, 'r') as file:
        site_structure = yaml.safe_load(file)
    return site_structure

# Fetch HTML content from a given URL
def fetch_html_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return None

# Sanitize HTML to ensure all resources have absolute URLs
def sanitize_html(html_content, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for tag in soup.find_all(['a', 'img', 'link', 'script'], href=True):
        tag['href'] = requests.compat.urljoin(base_url, tag['href'])
    for tag in soup.find_all(['a', 'img', 'link', 'script'], src=True):
        tag['src'] = requests.compat.urljoin(base_url, tag['src'])
    
    return str(soup)

# Remove footer based on specific markers
def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    footer_start = soup.find('devsite-hats-survey') or soup.find('devsite-content-footer')
    
    if footer_start:
        for elem in footer_start.find_all_next():
            elem.decompose()
    
    return str(soup)

# Save individual HTML content to a PDF
def save_individual_pdf(html_content, output_filename):
    config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
    options = {'enable-local-file-access': None}
    pdfkit.from_string(html_content, output_filename, configuration=config, options=options)

# Combine PDFs in small batches to avoid open file limits
def combine_pdfs_in_batches(pdf_filenames, batch_size=50, output_filename="combined_output.pdf"):
    temp_files = []
    batch_files = []

    # Combine PDFs in batches to intermediate files
    for i in range(0, len(pdf_filenames), batch_size):
        batch = pdf_filenames[i:i + batch_size]
        batch_filename = f"temp_batch_{i//batch_size}.pdf"
        with PdfMerger() as merger:
            for pdf_file in batch:
                merger.append(pdf_file)
            merger.write(batch_filename)
        batch_files.append(batch_filename)

    # Combine intermediate files into the final output
    with PdfMerger() as final_merger:
        for batch_file in batch_files:
            final_merger.append(batch_file)
        final_merger.write(output_filename)

    # Clean up intermediate and temporary files
    for pdf_file in pdf_filenames + batch_files:
        os.remove(pdf_file)
    print(f"Combined PDF saved as {output_filename}")

# Main function
def main(input_filename, output_pdf="combined_output.pdf"):
    site_structure = load_site_structure(input_filename)
    pdf_filenames = []
    
    # Total number of links
    total_links = sum(len(data["internal_links"]) for data in site_structure.values())
    
    # Overall progress bar at the bottom
    with tqdm(total=total_links, desc="Overall Progress", position=1, leave=True, bar_format="{desc}: {percentage:3.0f}% | {n_fmt}/{total_fmt} files processed") as overall_pbar:
        # Process each link and display individual status at the top
        for title, data in site_structure.items():
            for i, url in enumerate(data["internal_links"], start=1):
                with tqdm(total=1, desc=f"Processing {url}", position=0, leave=False, bar_format="{desc}") as file_pbar:
                    html_content = fetch_html_content(url)
                    
                    if html_content:
                        cleaned_html = clean_html_content(html_content)
                        sanitized_html = sanitize_html(cleaned_html, url)
                        
                        pdf_filename = f"temp_pdf_{title.replace(' ', '_')}_{i}.pdf"
                        save_individual_pdf(sanitized_html, pdf_filename)
                        pdf_filenames.append(pdf_filename)
                        overall_pbar.update(1)  # Update total progress bar
                    else:
                        print(f"Skipping {url} due to fetch issues.")
                    file_pbar.update(1)  # Mark the file processing as done for the individual bar

    # Combine PDFs in batches
    combine_pdfs_in_batches(pdf_filenames, batch_size=50, output_filename=output_pdf)

# Run the main function
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a single PDF from links in a YAML site structure file.")
    parser.add_argument('input_file', help="Path to the site structure YAML file.")
    parser.add_argument('--output', default="combined_output.pdf", help="Output PDF filename.")
    args = parser.parse_args()

    main(args.input_file, output_pdf=args.output)

