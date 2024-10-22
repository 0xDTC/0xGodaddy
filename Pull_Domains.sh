#!/bin/bash

# Load API key and secret from external file
source secret.txt

# Constants
API_URL="https://api.godaddy.com/v1/domains"
LIMIT=1000                     # Maximum number of domains per page
RATE_LIMIT_DELAY=5             # Time to wait between API calls to respect rate limits
TEMP_FILE="domains.json"       # Temporary file to store API response
ALL_DOMAINS_FILE="all_domains.json"  # File to store all fetched domains
marker=""                      # Marker for pagination, starts as an empty string

# Initialize the output file and open it as a JSON array
echo "[" > "$ALL_DOMAINS_FILE"

# Function to fetch domains from GoDaddy API using pagination
fetch_domains() {
    local url
    if [ -z "$marker" ]; then
        url="$API_URL?limit=$LIMIT"
    else
        url="$API_URL?limit=$LIMIT&marker=$marker"
    fi
    
    # Fetch data and redirect detailed output to /dev/null
    curl -s -X GET "$url" \
        -H "Authorization: sso-key $API_KEY:$API_SECRET" \
        -H "Content-Type: application/json" \
        -H "accept: application/json" > "$TEMP_FILE" 2>/dev/null
}

# Loop through all pages and fetch domains
first_page=true
while true; do
    fetch_domains
    
    # Check if the response contains valid domain data
    if jq -e '.[]' "$TEMP_FILE" >/dev/null 2>&1; then
        # If it's not the first page, add a comma for proper JSON formatting
        if [ "$first_page" = false ]; then
            echo "," >> "$ALL_DOMAINS_FILE"
        fi

        # Append the domains to the output file
        jq -c '.[]' "$TEMP_FILE" >> "$ALL_DOMAINS_FILE"
        first_page=false
        echo "Fetched domains from the current page."

    else
        echo "Error: No valid domain data found in response. Exiting."
        break
    fi

    # Check for the next pagination marker
    marker=$(jq -r '.pagination.nextMarker // empty' "$TEMP_FILE" 2>/dev/null)

    # If no marker exists, stop pagination
    if [ -z "$marker" ]; then
        echo "No more pages. Stopping pagination."
        break
    fi

    # Respect rate limits
    sleep "$RATE_LIMIT_DELAY"
done

# Close the JSON array
echo "]" >> "$ALL_DOMAINS_FILE"

# Clean up the temporary file
rm "$TEMP_FILE"

echo "All domains have been fetched and saved to $ALL_DOMAINS_FILE"
