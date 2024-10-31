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
        response.raise_for_status()  # Ensure the request was successful
        return response.text
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return None

# Sanitize HTML to ensure all resources have absolute URLs
def sanitize_html(html_content, base_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Convert relative URLs to absolute URLs for images, CSS, and scripts
    for tag in soup.find_all(['a', 'img', 'link', 'script'], href=True):
        tag['href'] = requests.compat.urljoin(base_url, tag['href'])
    for tag in soup.find_all(['a', 'img', 'link', 'script'], src=True):
        tag['src'] = requests.compat.urljoin(base_url, tag['src'])
    
    return str(soup)

# Remove footer based on specific markers
def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Identify the start of the footer section
    footer_start_tags = ['devsite-hats-survey', 'devsite-thumb-rating', 'devsite-feedback', 'devsite-content-footer']
    footer_start = None
    for tag in footer_start_tags:
        footer_start = soup.find(tag)
        if footer_start:
            break
    
    # If a footer start tag is found, remove everything after it
    if footer_start:
        for elem in footer_start.find_all_next():
            elem.decompose()

    return str(soup)

# Save individual HTML content to a PDF
def save_individual_pdf(html_content, output_filename):
    config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')
    options = {
        'enable-local-file-access': None,
    }
    pdfkit.from_string(html_content, output_filename, configuration=config, options=options)

# Combine multiple PDFs into a single PDF
def combine_pdfs(pdf_filenames, output_filename="combined_output.pdf"):
    merger = PdfMerger()
    for pdf_file in pdf_filenames:
        merger.append(pdf_file)
    merger.write(output_filename)
    merger.close()
    print(f"Combined PDF saved as {output_filename}")

# Main function to load, create individual PDFs, and then combine them
def main(input_filename, output_pdf="combined_output.pdf"):
    # Load site structure
    site_structure = load_site_structure(input_filename)
    
    # List to store paths of individual PDF files
    pdf_filenames = []
    
    # Generate individual PDFs with a progress bar
    for title, data in tqdm(site_structure.items(), desc="Processing sections"):
        for i, url in enumerate(data["internal_links"], start=1):
            print(f"Fetching content from {url}...")
            html_content = fetch_html_content(url)
            
            if html_content:
                # Remove footer content
                cleaned_html = clean_html_content(html_content)
                
                # Sanitize HTML to ensure all resources have absolute URLs
                sanitized_html = sanitize_html(cleaned_html, url)
                
                # Save each page as an individual PDF
                pdf_filename = f"temp_pdf_{title.replace(' ', '_')}_{i}.pdf"
                save_individual_pdf(sanitized_html, pdf_filename)
                pdf_filenames.append(pdf_filename)
            else:
                print(f"Skipping {url} due to fetch issues.")
    
    # Combine all individual PDFs into one
    combine_pdfs(pdf_filenames, output_filename=output_pdf)
    
    # Clean up individual PDFs
    for pdf_file in pdf_filenames:
        os.remove(pdf_file)
    print("Temporary individual PDFs deleted.")

# Run the main function
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a single PDF from links in a YAML site structure file.")
    parser.add_argument('input_file', help="Path to the site structure YAML file.")
    parser.add_argument('--output', default="combined_output.pdf", help="Output PDF filename.")
    args = parser.parse_args()

    main(args.input_file, output_pdf=args.output)

