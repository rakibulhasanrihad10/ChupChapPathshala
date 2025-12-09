def verify_unified_design():
    style_path = r"c:\Users\rakib\library-management-system\app\static\css\style.css"
    base_path = r"c:\Users\rakib\library-management-system\app\templates\base.html"

    # Check style.css
    with open(style_path, "r", encoding="utf-8") as f:
        style_content = f.read()
    
    if ".search-form.has-suggestions" in style_content and "border-radius: 1.5rem 1.5rem 0 0" in style_content:
        print("PASS: Unified Card styles present in style.css")
    else:
        print("FAIL: Unified Card styles MISSING in style.css")

    # Check base.html JS
    with open(base_path, "r", encoding="utf-8") as f:
        base_content = f.read()
        
    if "classList.add('has-suggestions')" in base_content and "classList.remove('has-suggestions')" in base_content:
        print("PASS: JS logic transforms form shape")
    else:
        print("FAIL: JS logic MISSING for transforming form shape")
        
    if '<svg class="suggestion-icon"' in base_content:
        print("PASS: Suggestion Icon injected")
    else:
        print("FAIL: Suggestion Icon NOT injected")

if __name__ == "__main__":
    verify_unified_design()
