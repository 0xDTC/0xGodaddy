#!/bin/bash

# Load API key and secret
source secret.txt

# Constants
API_URL="https://api.godaddy.com/v1/domains"
LIMIT=1000                     # Maximum number of domains per page
RATE_LIMIT_DELAY=5             # Time to wait between API calls to respect rate limits
TEMP_FILE="domains.json"       # Temporary file to store API response
ALL_DOMAINS_FILE="all_domains.json"  # File to store all fetched domains
marker=""                      # Marker for pagination, starts as an empty string

# Initialize the output file
> "$ALL_DOMAINS_FILE"  # Clear the file if it exists

# Function to fetch domains from GoDaddy API using pagination
fetch_domains() {
    local url
    if [ -z "$marker" ]; then
        url="$API_URL?limit=$LIMIT"
    else
        url="$API_URL?limit=$LIMIT&marker=$marker"
    fi
    
    curl -s -X GET "$url" \
        -H "Authorization: sso-key $API_KEY:$API_SECRET" \
        -H "Content-Type: application/json" \
        -H "accept: application/json" > "$TEMP_FILE"

    echo "Raw response:"
    cat "$TEMP_FILE"  # Debug: print raw response to check its structure
}

# Loop through all pages and fetch domains
while true; do
    fetch_domains
    
    # Check the structure of the response
    if jq -e '.domains' "$TEMP_FILE" >/dev/null 2>&1; then
        # If the domains field exists, append current domains to the output file
        domain_count=$(jq '.domains | length' "$TEMP_FILE")
        if [ "$domain_count" -gt 0 ]; then
            jq -c '.domains[]' "$TEMP_FILE" >> "$ALL_DOMAINS_FILE"
            echo "Fetched $domain_count domains"
        else
            echo "No domains found in this page. Stopping."
            break
        fi
    else
        echo "Error: Expected 'domains' field not found in response. Exiting."
        break
    fi

    # Check for pagination marker
    if jq -e '.pagination.nextMarker' "$TEMP_FILE" >/dev/null 2>&1; then
        marker=$(jq -r '.pagination.nextMarker // empty' "$TEMP_FILE")
        if [ -z "$marker" ]; then
            echo "No more pages. Stopping pagination."
            break
        fi
    else
        echo "No pagination info found. Assuming no more pages."
        break
    fi

    # Respect rate limits by sleeping between requests
    sleep "$RATE_LIMIT_DELAY"
done

# Formatting the output file
jq -s '.' "$ALL_DOMAINS_FILE" > "cleaned_$ALL_DOMAINS_FILE"

# Clean up the temporary file
rm "$TEMP_FILE"

echo "All domains have been fetched and saved to cleaned_$ALL_DOMAINS_FILE"