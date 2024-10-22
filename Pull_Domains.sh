#!/bin/bash

# Set your GoDaddy API Key and Secret
source secret.txt

# Variables
PAGE=1
PER_PAGE=1000  # Number of domains per page
TEMP_FILE="domains_temp.json"
DOMAINS_TABLE="domains_table.txt"
SUBDOMAINS_FILE="subdomains_table.txt"
FINAL_FILE="final_table.txt"

# Clear any existing files
> $TEMP_FILE
> $DOMAINS_TABLE
> $SUBDOMAINS_FILE
> $FINAL_FILE

# Step 1: Fetch domains from GoDaddy API with pagination
echo "Fetching domain data from GoDaddy API..."

while true; do
    RESPONSE=$(curl -s -X GET "https://api.godaddy.com/v1/domains?page=$PAGE&perPage=$PER_PAGE" \
      -H "Authorization: sso-key $API_KEY:$API_SECRET" \
      -H "Content-Type: application/json")

    # Check if response is valid JSON
    if ! jq empty <<<"$RESPONSE" 2>/dev/null; then
        echo "Error: Invalid JSON response, or rate limit exceeded."
        break
    fi

    # Check if the response is empty or contains no domains
    DOMAIN_COUNT=$(echo "$RESPONSE" | jq '. | length')
    if [[ "$DOMAIN_COUNT" -eq 0 ]]; then
        echo "No more domains found, stopping."
        break
    fi

    # Append the response to the temporary file
    echo "$RESPONSE" >> $TEMP_FILE

    # Increment the page number for the next loop
    PAGE=$((PAGE + 1))

    echo "Fetched page $PAGE with $DOMAIN_COUNT domains"

    # Stop if fewer than expected domains were returned, indicating the last page
    if [[ "$DOMAIN_COUNT" -lt "$PER_PAGE" ]]; then
        echo "Last page detected (fewer than $PER_PAGE domains), stopping."
        break
    fi
done

echo "Domain data saved in $TEMP_FILE"

# Step 2: Parse domain data using jq and extract into a table
echo "Parsing domain data into a table..."

# Create header for the domains table
echo -e "Domain\tStatus\tExpiry" > $DOMAINS_TABLE

# Use jq to extract fields from the temporary file
jq -r '.[] | [.domain, .status, .expires] | @tsv' $TEMP_FILE >> $DOMAINS_TABLE

echo "Domains table saved in $DOMAINS_TABLE"

# Step 3: Fetch subdomains for each domain
echo "Fetching subdomains for each domain..."

while IFS=$'\t' read -r DOMAIN STATUS EXPIRY; do
    echo "Fetching subdomains for $DOMAIN"
    
    # Fetch subdomains using subfinder
    subfinder -d $DOMAIN -silent | tee -a $SUBDOMAINS_FILE
    
done < <(tail -n +2 $DOMAINS_TABLE)  # Skip the header in domains table

echo "Subdomains saved in $SUBDOMAINS_FILE"

# Step 4: Combine domain and subdomain data into the final table
echo -e "Domain\tStatus\tExpiry\tSubdomains" > $FINAL_FILE

while IFS=$'\t' read -r DOMAIN STATUS EXPIRY; do
    SUBDOMAINS=$(grep $DOMAIN $SUBDOMAINS_FILE | tr '\n' ',' | sed 's/,$//')
    echo -e "$DOMAIN\t$STATUS\t$EXPIRY\t$SUBDOMAINS" >> $FINAL_FILE
done < <(tail -n +2 $DOMAINS_TABLE)

echo "Final table with domains and subdomains saved in $FINAL_FILE"

# Step 5: Clean up temporary files
rm $TEMP_FILE $DOMAINS_TABLE $SUBDOMAINS_FILE

echo "Cleanup complete. Only $FINAL_FILE remains."
