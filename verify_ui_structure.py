import re

def check_structure():
    file_path = r"c:\Users\rakib\library-management-system\app\templates\base.html"
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find the search form
    search_form_pattern = r'<form action="{{ url_for\(\'main.search\'\) }}"[^>]*class="[^"]*search-form[^"]*"[^>]*>'
    form_match = re.search(search_form_pattern, content)
    
    if not form_match:
        print("FAIL: .search-form not found")
        return

    form_start_index = form_match.end()
    form_end_index = content.find('</form>', form_start_index)
    
    if form_end_index == -1:
        print("FAIL: Closing </form> tag not found")
        return
        
    form_content = content[form_start_index:form_end_index]
    
    # Check if suggestions div is inside the form content
    if 'id="suggestions"' in form_content:
        print("PASS: #suggestions is inside .search-form")
        
        # Check classes using regex since attributes might be in any order
        suggestions_match = re.search(r'<div id="suggestions"[^>]*class="([^"]*)"', form_content)
        if suggestions_match:
            classes = suggestions_match.group(1).split()
            if 'shadow-md' in classes and 'absolute' in classes and 'w-full' in classes:
                print("PASS: Classes look correct (shadow-md, absolute, w-full)")
            else:
                print(f"WARNING: Check classes: {classes}")
    else:
        print("FAIL: #suggestions is NOT inside .search-form")

if __name__ == "__main__":
    check_structure()
