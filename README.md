# Documentation Crawler and PDF Converter

This project contains Python scripts to crawl and convert a technical documentation site into a single, consolidated PDF file. The process uses `chromedriver` for web automation and `wkhtmltopdf` for HTML-to-PDF conversion. 

Run crawler against a site to create an output yaml file

python3 crawler.py https://site.com/docs/ --output urls.yaml

Edit the yaml file and remove anything you don't want.

Run convert to create a pdf

python3 convert.py urls.yaml
