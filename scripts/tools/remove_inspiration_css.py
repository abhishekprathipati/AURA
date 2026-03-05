"""Remove inspiration card CSS from stylesheet."""
import pathlib
import re

css_path = pathlib.Path(r"d:\AURA\static\css\student_dashboard.css")
css = css_path.read_text(encoding='utf-8')

# Remove all inspiration-related CSS blocks
patterns_to_remove = [
    r'\/\* ===== DAILY INSPIRATION CARD ===== \*\/.*?(?=\/\*|\Z)',
    r'\/\* Static Inspiration Card.*?(?=\/\*|\Z)',
    r'\.sidebar-inspiration-card\s*\{.*?\}(?:\s*\..*?\{.*?\})*',
    r'\.inspiration-quote\s*\{.*?\}',
    r'\.quote-mark\s*\{.*?\}',
    r'\.quote-text\s*\{.*?\}',
    r'\.quote-attr\s*\{.*?\}',
    r'\.sidebar-inspiration-static\s*\{.*?\}',
    r'\[data-theme="dark"\]\s*\.sidebar-inspiration.*?\{.*?\}(?:\s*\n)?',
]

for pattern in patterns_to_remove:
    css = re.sub(pattern, '', css, flags=re.DOTALL)

# Clean up excessive whitespace
css = re.sub(r'\n\n\n+', '\n\n', css)

css_path.write_text(css, encoding='utf-8')
print("Inspiration card CSS removed successfully!")
