#!/bin/bash

# Source the secrets file to load the API_KEY and API_SECRET
source secret.txt

# Constants
API_URL="https://api.godaddy.com/v1"
LIMIT=1000                     # Maximum number of domains per page
RATE_LIMIT_DELAY=5             # Time to wait between API calls to respect rate limits
TEMP_FILE="domains.json"       # Temporary file to store the response
ALL_DOMAINS_FILE="all_domains.json"  # File to store all the domains

# Initialize the output file
echo "[" > "$ALL_DOMAINS_FILE"

# Function to get domains from the GoDaddy API
get_domains() {
    curl -s -X GET "$API_URL/domains?limit=$LIMIT" -H "Authorization: sso-key $API_KEY:$API_SECRET" -H "Content-Type: application/json" > "$TEMP_FILE"
}

# Fetch domains from GoDaddy API
get_domains

# Check if the current page contains domains
if [ -s "$TEMP_FILE" ]; then
    # Append the domains to the output file, without the brackets
    jq -c '.[]' "$TEMP_FILE" >> "$ALL_DOMAINS_FILE"
fi

# Close the JSON array
echo "]" >> "$ALL_DOMAINS_FILE"

# Clean up the temporary file
rm "$TEMP_FILE"

echo "All domains have been fetched and saved to $ALL_DOMAINS_FILE"
