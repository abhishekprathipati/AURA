@echo off
cd /d d:\AURA

echo Staging all changes...
git add -A

echo Committing changes...
git commit -m "Refactor: extract inline styles and improve flashcard parsing

- Extracted 50+ inline styles from templates/student_dashboard.html
- Moved styles to semantic CSS utility classes in static/css/student_dashboard.css
- Added ~300 lines of new utility classes for layout, charts, modals, forms, and settings
- Improved parseFlashcards() in static/js/study_chatbot.js to handle multiple flashcard formats

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

echo Pushing to GitHub...
git push

echo Done!
pause
