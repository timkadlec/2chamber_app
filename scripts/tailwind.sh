#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# tailwind.sh — install, scaffold, and run Tailwind CSS
#
# Usage:
#   ./scripts/tailwind.sh          # watch mode (development)
#   ./scripts/tailwind.sh --build  # one-shot minified build (production)
# ---------------------------------------------------------------------------

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INPUT="$ROOT/static/css/tailwind.src.css"
OUTPUT="$ROOT/static/css/tailwind.css"
CONFIG="$ROOT/tailwind.config.js"

cd "$ROOT"

# --- 1. Install Tailwind if not present ------------------------------------
if ! node_modules/.bin/tailwindcss --help &>/dev/null; then
  echo "Installing Tailwind CSS..."
  npm install --save-dev tailwindcss @tailwindcss/forms
fi

# --- 2. Scaffold tailwind.config.js if missing ----------------------------
if [ ! -f "$CONFIG" ]; then
  echo "Creating tailwind.config.js..."
  cat > "$CONFIG" <<'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./modules/**/templates/**/*.html",
    "./static/js/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("@tailwindcss/forms"),
  ],
}
EOF
fi

# --- 3. Scaffold input CSS if missing -------------------------------------
if [ ! -f "$INPUT" ]; then
  echo "Creating $INPUT..."
  cat > "$INPUT" <<'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;
EOF
fi

# --- 4. Build or watch -----------------------------------------------------
if [ "${1:-}" = "--build" ]; then
  echo "Building Tailwind CSS (minified)..."
  node_modules/.bin/tailwindcss -i "$INPUT" -o "$OUTPUT" --minify
  echo "Done → $OUTPUT"
else
  echo "Watching for changes (output → $OUTPUT)..."
  node_modules/.bin/tailwindcss -i "$INPUT" -o "$OUTPUT" --watch
fi
