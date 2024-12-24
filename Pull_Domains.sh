#!/bin/bash

# Load secrets
source secret.txt

# Variables
PAGE_SIZE=1000
marker=""
output_file="domains.json"

# Initialize the output file with an empty array
echo "[]" > "$output_file"

while true; do
    # Fetch the domains data
    response=$(curl -s -X GET -H "Authorization: sso-key $API_KEY:$API_SECRET" -H "Accept: application/json" "https://api.godaddy.com/v1/domains?limit=$PAGE_SIZE&marker=$marker")

    # Check if the response is empty
    if [[ -z "$response" ]]; then
        echo "Failed to fetch domains."
        exit 1
    fi

    # Create a temporary file
    tmp_file=$(mktemp)

    # Merge with the output file
    jq -s '.[0] + .[1]' "$output_file" <(echo "$response") > "$tmp_file" && mv "$tmp_file" "$output_file"

    # Check if the number of domains fetched is less than PAGE_SIZE
    count=$(jq 'length' <<< "$response")
    if (( count < PAGE_SIZE )); then
        break
    fi

    # Update the marker for the next page
    marker=$(jq -r '.[-1].domain' <<< "$response")
done

# Print the counts directly with jq
echo "Counts of Domains by Status:"
echo "-----------------------------"

# Extract all unique statuses and count them
jq -r '.[].status' "$output_file" | sort | uniq -c | while read -r count status; do
    printf "%-25s: %d\n" "$status" "$count"
done

echo "Domains fetched successfully."

