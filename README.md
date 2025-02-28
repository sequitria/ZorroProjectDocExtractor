### Steps:
- Set up a virtual environment
- use command:  pip install -r requirements.txt or pip3 install -r requirements.txt
- run the script: python zorro_doc_extractor.py or python3 zorro_doc_extractor.py

### The script will:
- Extract all documentation pages from the table of contents
- Download each page and convert it to Markdown
- Add metadata headers
- Create a directory structure matching the documentation hierarchy
- Generate index files

### Output should look like this:
    
    zorro_docs/
    ├── index.md (main index)
    ├── Category_1/
    │   ├── index.md (category index)
    │   ├── page1.md
    │   ├── page2.md
    │   └── Subcategory_1/
    │       ├── index.md (subcategory index)
    │       ├── page3.md
    │       └── page4.md
    └── Category_2/
        └── ...
