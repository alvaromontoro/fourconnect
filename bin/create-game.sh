#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=== 4Connect Game Creator ===${NC}\n"

# Find the latest game date
LATEST_GAME_PATH=$(find "$PROJECT_ROOT/games" -mindepth 3 -maxdepth 3 -type d | sort | tail -1)

if [ -z "$LATEST_GAME_PATH" ]; then
  # No games exist, use a default starting date
  SUGGESTED_DATE="2026-01-01"
  LATEST_DATE_STR=""
else
  # Extract year, month, day from path: /path/to/games/YYYY/MM/DD
  DAY=$(basename "$LATEST_GAME_PATH")
  MONTH=$(basename "$(dirname "$LATEST_GAME_PATH")")
  YEAR=$(basename "$(dirname "$(dirname "$LATEST_GAME_PATH")")")
  LATEST_DATE_STR="$YEAR-$MONTH-$DAY"
  
  # Calculate next date (add 1 day)
  SUGGESTED_DATE=$(date -j -v+1d -f "%Y-%m-%d" "$LATEST_DATE_STR" "+%Y-%m-%d" 2>/dev/null || date -d "$LATEST_DATE_STR + 1 day" "+%Y-%m-%d" 2>/dev/null)
fi

echo -e "${BLUE}Latest game date: $LATEST_DATE_STR${NC}"
echo -e "${BLUE}Suggested next date: $SUGGESTED_DATE${NC}\n"

# Ask for game date
while true; do
  read -p "Enter game date (YYYY-MM-DD) or press Enter for [$SUGGESTED_DATE]: " GAME_DATE
  
  # Use suggested date if empty
  if [ -z "$GAME_DATE" ]; then
    GAME_DATE="$SUGGESTED_DATE"
  fi
  
  if [[ $GAME_DATE =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    break
  else
    echo -e "${RED}Invalid date format. Please use YYYY-MM-DD${NC}"
  fi
done

# Ask for game title
read -p "Enter game title: " GAME_TITLE

# Ask for categories
read -p "Enter categories (comma-separated, e.g., tech,webdev): " CATEGORIES_INPUT

# Ask for game data
echo "Enter game data (JSON format). Press Ctrl+D when done:"
GAME_DATA=$(cat)

# Validate JSON
if ! echo "$GAME_DATA" | jq empty 2>/dev/null; then
  echo -e "${RED}Error: Invalid JSON format${NC}"
  exit 1
fi

# Parse date components
YEAR=$(echo "$GAME_DATE" | cut -d'-' -f1)
MONTH=$(echo "$GAME_DATE" | cut -d'-' -f2)
DAY=$(echo "$GAME_DATE" | cut -d'-' -f3)

# Convert date to word format (e.g., "June 16, 2025")
DATE_LONG=$(date -j -f "%Y-%m-%d" "$GAME_DATE" "+%B %d, %Y" 2>/dev/null || date -d "$GAME_DATE" "+%B %d, %Y" 2>/dev/null)
PAGE_TITLE="4Connect - $GAME_TITLE - $DATE_LONG"
CANONICAL_URL="https://fourconnect.net/games/$YEAR/$MONTH/$DAY"

if [ -n "$CATEGORIES_INPUT" ]; then
  IFS=',' read -ra CATEGORY_NAMES <<< "$CATEGORIES_INPUT"
  CLEAN_CATEGORY_NAMES=()
  for category in "${CATEGORY_NAMES[@]}"; do
    CATEGORY_NAME=$(echo "$category" | xargs)
    if [ -n "$CATEGORY_NAME" ]; then
      CLEAN_CATEGORY_NAMES+=("$CATEGORY_NAME")
    fi
  done
  CATEGORY_LIST=$(IFS=', '; echo "${CLEAN_CATEGORY_NAMES[*]}")
else
  CATEGORY_LIST=""
fi

META_DESCRIPTION="Play the $GAME_TITLE 4Connect puzzle for $DATE_LONG."
if [ -n "$CATEGORY_LIST" ]; then
  META_DESCRIPTION+=" Categories: $CATEGORY_LIST."
fi
META_DESCRIPTION+=" Find the connections between 16 words."

# Parse categories
IFS=',' read -ra CATEGORIES <<< "$CATEGORIES_INPUT"
# Trim whitespace from categories
CATEGORIES=("${CATEGORIES[@]// /}")

echo -e "\n${BLUE}Creating game structure...${NC}"

# Create game folder structure
GAME_FOLDER="$PROJECT_ROOT/games/$YEAR/$MONTH/$DAY"
mkdir -p "$GAME_FOLDER"
echo -e "${GREEN}✓ Created folder: $GAME_FOLDER${NC}"

# Copy and modify base_game.html
cp "$PROJECT_ROOT/games/base_game.html" "$GAME_FOLDER/index.html"

# Replace placeholders in index.html
sed -i '' "s|\[DATE_ISO_FORMAT\]|$GAME_DATE|g" "$GAME_FOLDER/index.html"
sed -i '' "s|\[DATE_WORD_FORMAT\]|$DATE_LONG|g" "$GAME_FOLDER/index.html"
sed -i '' "s|\[GAME_TITLE\]|$GAME_TITLE|g" "$GAME_FOLDER/index.html"
sed -i '' "s|\[GAME_DATA\]|$GAME_DATA|g" "$GAME_FOLDER/index.html"
sed -i '' "s|\[PAGE_TITLE\]|$PAGE_TITLE|g" "$GAME_FOLDER/index.html"
sed -i '' "s|\[CANONICAL_URL\]|$CANONICAL_URL|g" "$GAME_FOLDER/index.html"
sed -i '' "s|\[META_DESCRIPTION\]|$META_DESCRIPTION|g" "$GAME_FOLDER/index.html"

# Create a relative link to previous day's game (if exists)
PREV_DAY=$(date -j -v-1d -f "%Y-%m-%d" "$GAME_DATE" "+%Y/%m/%d" 2>/dev/null || date -d "$GAME_DATE - 1 day" "+%Y/%m/%d" 2>/dev/null)
PREV_LINK="/games/$PREV_DAY"
sed -i '' "s|\[LINK_TO_PREVIOUS_GAME\]|$PREV_LINK|g" "$GAME_FOLDER/index.html"

echo -e "${GREEN}✓ Created and configured index.html${NC}"

# Create categories array in JSON format
CATEGORIES_JSON="["
for i in "${!CATEGORIES[@]}"; do
  CATEGORIES_JSON+="\"${CATEGORIES[$i]}\""
  if [ $i -lt $((${#CATEGORIES[@]} - 1)) ]; then
    CATEGORIES_JSON+=", "
  fi
done
CATEGORIES_JSON+="]"

# Create data.json
DATA_JSON_FILE="$GAME_FOLDER/data.json"
cat > "$DATA_JSON_FILE" << EOF
{
  "title": "$GAME_TITLE",
  "date": "$GAME_DATE",
  "dateLong": "$DATE_LONG",
  "categories": $CATEGORIES_JSON,
  "game": $GAME_DATA
}
EOF

echo -e "${GREEN}✓ Created data.json${NC}"

# Update category files
for category in "${CATEGORIES[@]}"; do
  CATEGORY_FILE="$PROJECT_ROOT/categories/$category.json"
  
  if [ -f "$CATEGORY_FILE" ]; then
    # Check if date already exists in the file
    if ! grep -q "\"$GAME_DATE\"" "$CATEGORY_FILE"; then
      # Add date to the dates array
      python3 << PYTHON
import json
with open('$CATEGORY_FILE', 'r') as f:
    data = json.load(f)
if '$GAME_DATE' not in data['dates']:
    data['dates'].append('$GAME_DATE')
    data['dates'].sort(reverse=True)
with open('$CATEGORY_FILE', 'w') as f:
    json.dump(data, f, indent=2)
PYTHON
      echo -e "${GREEN}✓ Updated categories/$category.json${NC}"
    else
      echo -e "${BLUE}✓ Date already exists in categories/$category.json${NC}"
    fi
  else
    # Create new category file if it doesn't exist
    echo '{"dates": ["'$GAME_DATE'"]}' | python3 -m json.tool > "$CATEGORY_FILE"
    echo -e "${GREEN}✓ Created categories/$category.json${NC}"
  fi
done

# Refresh RSS feeds after category files change
python3 "$PROJECT_ROOT/bin/update-index-from-latest-game.py" --rss-only

# Export PNG image for the new game as the final step
echo -e "\n${BLUE}Exporting game image...${NC}"
if command -v npm >/dev/null 2>&1; then
  if (cd "$PROJECT_ROOT" && npm run -s export:png -- --date "$GAME_DATE" --overwrite); then
    echo -e "${GREEN}✓ Exported game PNG: $GAME_FOLDER/fourconnect-$GAME_DATE.png${NC}"
  else
    echo -e "${RED}⚠ Could not export game PNG automatically.${NC}"
    echo -e "${BLUE}Run manually: cd $PROJECT_ROOT && npm run export:png -- --date $GAME_DATE --overwrite${NC}"
  fi
else
  echo -e "${RED}⚠ npm is not available. Skipping PNG export.${NC}"
  echo -e "${BLUE}Run manually when available: cd $PROJECT_ROOT && npm run export:png -- --date $GAME_DATE --overwrite${NC}"
fi

echo -e "\n${GREEN}=== Game successfully created! ===${NC}"
echo -e "Location: ${BLUE}$GAME_FOLDER${NC}"
echo -e "URL: ${BLUE}/games/$YEAR/$MONTH/$DAY/${NC}"
