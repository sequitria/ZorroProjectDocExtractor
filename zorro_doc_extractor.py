import requests
from bs4 import BeautifulSoup
import os
import re
import time
import html2text
from urllib.parse import urljoin

# Base URL for Zorro documentation
BASE_URL = "https://zorro-project.com/manual/"

def get_doc_urls():
    """Extract all documentation URLs and hierarchical structure from TOC"""
    response = requests.get(f"{BASE_URL}ht_contents.htm")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    doc_urls = []
    current_category = "Main"
    current_subcategory = None
    
    # Track hierarchy for index creation
    hierarchy = {}
    
    # Find all elements in the TOC
    elements = soup.find_all(['img', 'a'])
    
    for i, element in enumerate(elements):
        # Check if it's a category header (img with p4.gif)
        if element.name == 'img' and 'p4.gif' in element.get('src', ''):
            # Next element should be the category link
            if i+1 < len(elements) and elements[i+1].name == 'a':
                current_category = elements[i+1].get('title') or elements[i+1].text
                current_subcategory = None
                hierarchy[current_category] = {"subcategories": {}, "pages": []}
        
        # Check if it's a subcategory (img with p3.gif)
        elif element.name == 'img' and 'p3.gif' in element.get('src', ''):
            # Next element should be the subcategory text
            if i+1 < len(elements) and elements[i+1].name == 'a':
                current_subcategory = elements[i+1].get('title') or elements[i+1].text
                if current_category in hierarchy:
                    hierarchy[current_category]["subcategories"][current_subcategory] = []
        
        # Check if it's a link to a page (a with class clsTOCItem)
        elif element.name == 'a' and element.get('class') == ['clsTOCItem']:
            url = element.get('href')
            title = element.get('title') or element.text
            
            if url and url.endswith('.htm'):
                # Handle relative URLs
                if not url.startswith('http'):
                    full_url = urljoin(BASE_URL, url)
                else:
                    full_url = url
                
                page_info = {
                    'url': full_url,
                    'title': title,
                    'category': current_category,
                    'subcategory': current_subcategory,
                    'filename': os.path.basename(url)
                }
                doc_urls.append(page_info)
                
                # Add to hierarchy
                if current_category in hierarchy:
                    if current_subcategory and current_subcategory in hierarchy[current_category]["subcategories"]:
                        hierarchy[current_category]["subcategories"][current_subcategory].append(page_info)
                    else:
                        hierarchy[current_category]["pages"].append(page_info)
    
    return doc_urls, hierarchy

def html_to_markdown(html_content):
    """Convert HTML content to Markdown with proper formatting"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title
    title = soup.title.text if soup.title else "Untitled"
    
    # Handle code blocks specially
    code_blocks = []
    code_placeholder = "CODE_BLOCK_PLACEHOLDER_{}"
    
    # Find all code blocks (usually in pre or code tags)
    for i, code_element in enumerate(soup.find_all(['pre', 'code', '.wp_codebox'])):
        # Try to identify language
        language = "c"  # Default for Zorro
        if 'class' in code_element.attrs:
            classes = code_element['class']
            if 'python' in str(classes).lower():
                language = "python"
            elif 'javascript' in str(classes).lower() or 'js' in str(classes).lower():
                language = "javascript"
            elif 'rsplus' in str(classes).lower():
                language = "r"
        
        # Store code with language info
        code_blocks.append((language, code_element.get_text()))
        
        # Replace with placeholder
        placeholder = soup.new_tag('p')
        placeholder.string = code_placeholder.format(i)
        code_element.replace_with(placeholder)
    
    # Convert to markdown
    h2t = html2text.HTML2Text()
    h2t.body_width = 0  # Don't wrap text
    markdown = h2t.handle(str(soup))
    
    # Restore code blocks with proper markdown formatting
    for i, (language, code) in enumerate(code_blocks):
        formatted_code = f"```{language}\n{code.strip()}\n```"
        markdown = markdown.replace(code_placeholder.format(i), formatted_code)
    
    # Clean up the markdown
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)  # Remove excessive newlines
    
    return title, markdown

def find_related_pages(html_content, all_pages, current_url):
    """Find related pages based on links in the content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    related = []
    
    for link in soup.find_all('a'):
        href = link.get('href')
        if href and href.endswith('.htm'):
            # Normalize the URL
            full_url = urljoin(current_url, href)
            # Find matching page
            for page in all_pages:
                if page['url'] == full_url and full_url != current_url:
                    related.append(f"- [{page['title']}]({os.path.basename(href)})")
                    break
    
    # Remove duplicates
    related = list(dict.fromkeys(related))
    
    return related if related else ["- None"]

def create_metadata_header(title, url, category, subcategory, related_pages):
    """Create a metadata header for the document"""
    related_str = "\n".join(related_pages)
    
    return f"""---
title: {title}
url: {url}
category: {category}
subcategory: {subcategory or 'None'}
related_pages:
{related_str}
---

# {title}

"""

def generate_index(output_dir, hierarchy):
    """Generate comprehensive index files"""
    # Main index
    index_content = "# Zorro Documentation Index\n\n"
    
    for category, data in hierarchy.items():
        safe_category = sanitize_filename(category)
        index_content += f"## {category}\n\n"
        
        # Add direct pages under category
        for page in data["pages"]:
            safe_filename = sanitize_filename(page['filename'].replace('.htm', '.md'))
            index_content += f"- [{page['title']}]({safe_category}/{safe_filename})\n"
        
        # Add subcategories
        for subcategory, pages in data["subcategories"].items():
            if pages:  # Only add subcategories with pages
                safe_subcategory = sanitize_filename(subcategory)
                index_content += f"\n### {subcategory}\n\n"
                
                for page in pages:
                    safe_filename = sanitize_filename(page['filename'].replace('.htm', '.md'))
                    index_content += f"- [{page['title']}]({safe_category}/{safe_subcategory}/{safe_filename})\n"
        
        index_content += "\n"
    
    # Save main index
    with open(os.path.join(output_dir, "index.md"), 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    # Generate category indexes
    for category, data in hierarchy.items():
        safe_category = sanitize_filename(category)
        category_dir = os.path.join(output_dir, safe_category)
        
        category_index = f"# {category}\n\n"
        
        # Add direct pages
        if data["pages"]:
            category_index += "## Pages\n\n"
            for page in data["pages"]:
                safe_filename = sanitize_filename(page['filename'].replace('.htm', '.md'))
                category_index += f"- [{page['title']}]({safe_filename})\n"
            category_index += "\n"
        
        # Add subcategories
        if data["subcategories"]:
            category_index += "## Subcategories\n\n"
            for subcategory, pages in data["subcategories"].items():
                safe_subcategory = sanitize_filename(subcategory)
                category_index += f"### {subcategory}\n\n"
                
                for page in pages:
                    safe_filename = sanitize_filename(page['filename'].replace('.htm', '.md'))
                    category_index += f"- [{page['title']}]({safe_subcategory}/{safe_filename})\n"
                
                category_index += "\n"
                
                # Generate subcategory indexes
                if pages:
                    subcategory_dir = os.path.join(category_dir, safe_subcategory)
                    os.makedirs(subcategory_dir, exist_ok=True)
                    
                    subcategory_index = f"# {subcategory}\n\nPart of [{category}](../index.md)\n\n## Pages\n\n"
                    
                    for page in pages:
                        safe_filename = sanitize_filename(page['filename'].replace('.htm', '.md'))
                        subcategory_index += f"- [{page['title']}]({safe_filename})\n"
                    
                    with open(os.path.join(subcategory_dir, "index.md"), 'w', encoding='utf-8') as f:
                        f.write(subcategory_index)
        
        # Save category index
        with open(os.path.join(category_dir, "index.md"), 'w', encoding='utf-8') as f:
            f.write(category_index)

def sanitize_filename(filename):
    """Convert a string to a safe filename"""
    return re.sub(r'[\\/*?:"<>|]', '_', filename).replace(' ', '_')

def extract_zorro_documentation():
    """Main function to extract all Zorro documentation"""
    output_dir = "zorro_docs"
    os.makedirs(output_dir, exist_ok=True)
    
    print("Getting documentation structure...")
    doc_urls, hierarchy = get_doc_urls()
    print(f"Found {len(doc_urls)} documentation pages")
    
    # Create category directories
    for category in hierarchy.keys():
        category_dir = os.path.join(output_dir, sanitize_filename(category))
        os.makedirs(category_dir, exist_ok=True)
        
        # Create subcategory directories
        for subcategory in hierarchy[category]["subcategories"].keys():
            subcategory_dir = os.path.join(category_dir, sanitize_filename(subcategory))
            os.makedirs(subcategory_dir, exist_ok=True)
    
    # Process each page
    for i, page in enumerate(doc_urls):
        try:
            print(f"Processing {i+1}/{len(doc_urls)}: {page['title']}")
            
            # Get HTML content
            response = requests.get(page['url'])
            html_content = response.text
            
            # Convert to markdown
            title, markdown = html_to_markdown(html_content)
            
            # Find related pages
            related_pages = find_related_pages(html_content, doc_urls, page['url'])
            
            # Create metadata header
            markdown_with_metadata = create_metadata_header(
                title,
                page['url'],
                page['category'],
                page['subcategory'],
                related_pages
            ) + markdown
            
            # Determine output path
            if page['subcategory']:
                output_path = os.path.join(
                    output_dir,
                    sanitize_filename(page['category']),
                    sanitize_filename(page['subcategory']),
                    sanitize_filename(page['filename'].replace('.htm', '.md'))
                )
            else:
                output_path = os.path.join(
                    output_dir,
                    sanitize_filename(page['category']),
                    sanitize_filename(page['filename'].replace('.htm', '.md'))
                )
            
            # Save markdown file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_with_metadata)
            
            # Be nice to the server
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error processing {page['url']}: {e}")
    
    # Generate indexes
    print("Generating index files...")
    generate_index(output_dir, hierarchy)
    
    print(f"Documentation extraction complete! Files saved to {output_dir}")

if __name__ == "__main__":
    extract_zorro_documentation()