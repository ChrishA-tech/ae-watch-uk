cat << 'EOF' > .env
GEMINI_API_KEY=PASTE_YOUR_KEY_HERE
GEMINI_REASONING_MODEL=gemini-3.8-flash
GEMINI_FAST_MODEL=gemini-3.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
EOF

cat << 'EOF' > .gitignore
.env
__pycache__/
*.pyc
.venv/
mlruns/
data/raw/
data/processed/
.DS_Store
EOF