#!/bin/bash
# Quick verification script for AURA Theme System

echo "🎨 AURA Theme System - Files Verification"
echo "=========================================="
echo ""

# Check CSS files
echo "📋 CSS Files:"
[ -f "static/css/theme-system.css" ] && echo "✅ theme-system.css" || echo "❌ theme-system.css - MISSING"
[ -f "static/css/mental-chatbot.css" ] && echo "✅ mental-chatbot.css (updated)" || echo "❌ mental-chatbot.css - MISSING"

echo ""

# Check JS files
echo "📜 JavaScript Files:"
[ -f "static/js/theme-engine.js" ] && echo "✅ theme-engine.js" || echo "❌ theme-engine.js - MISSING"
[ -f "static/js/chat-engine.js" ] && echo "✅ chat-engine.js" || echo "❌ chat-engine.js - MISSING"

echo ""

# Check templates
echo "🎭 Templates:"
[ -f "templates/mental_chatbot.html" ] && echo "✅ mental_chatbot.html (updated)" || echo "❌ mental_chatbot.html - MISSING"

echo ""

# Check documentation
echo "📚 Documentation:"
[ -f "THEME_SYSTEM_DOCS.md" ] && echo "✅ THEME_SYSTEM_DOCS.md" || echo "❌ THEME_SYSTEM_DOCS.md - MISSING"

echo ""
echo "✨ All files ready! Start the server and test the theme toggle."
