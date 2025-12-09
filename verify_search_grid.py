import re

def verify_grid_fix():
    style_path = r"c:\Users\rakib\library-management-system\app\static\css\style.css"
    template_path = r"c:\Users\rakib\library-management-system\app\templates\search_results.html"
    
    # Check style.css
    with open(style_path, "r", encoding="utf-8") as f:
        style_content = f.read()
        
    if ".search-results-grid" in style_content and ".book-cover-container" in style_content:
        print("PASS: CSS classes found in style.css")
    else:
        print("FAIL: CSS classes MISSING in style.css")

    # Check search_results.html
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
        
    if 'class="search-results-grid"' in template_content:
        print("PASS: search-results-grid class found in template")
    else:
        print("FAIL: search-results-grid class MISSING in template")
        
    if 'class="book-cover-container group"' in template_content:
        print("PASS: book-cover-container class found in template")
    else:
        print("FAIL: book-cover-container class MISSING/INCORRECT in template")

if __name__ == "__main__":
    verify_grid_fix()
