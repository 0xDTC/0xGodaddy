# Subdomain Table Generator

This script automates the process of fetching domain and subdomain information from the GoDaddy API and generates a Markdown table containing the subdomain details, including DNS records.

## Features

1. **Domain Fetching:** Retrieves all domains associated with the provided GoDaddy API credentials.
2. **Subdomain Retrieval:** Fetches DNS records for each domain, including A and CNAME records.
3. **Markdown Table Generation:** Outputs the subdomain data in a clean, readable Markdown table format.

## Prerequisites

1. **Bash Shell:** Ensure you have Bash installed (available on Linux/macOS/WSL on Windows).
2. **GoDaddy API Credentials:**
    - Obtain your API Key and Secret from the GoDaddy Developer Portal.
    - Save the credentials in a `secret.txt` file located in the parent directory of the script.
    
    ```bash
    API_KEY="your_api_key"
    API_SECRET="your_api_secret"
    ```
3. **jq:**
    - Required for parsing JSON responses.
    - Install it using:
      ```bash
      sudo apt install jq        # Debian/Ubuntu
      brew install jq            # macOS
      sudo yum install jq        # Red Hat/CentOS
      ```

## Installation

1. Clone or download this script into a directory of your choice.
2. Ensure the script is executable:
    ```bash
    chmod +x script_name.sh
    ```

## Usage

1. Run the script:
    ```bash
    ./script_name.sh
    ```
2. The script will:
    - Fetch all domains.
    - Retrieve DNS records for each domain.
    - Generate a Markdown table of subdomains and save it to `subdomains_table.md`.

## Output

The output file `subdomains_table.md` will have the following structure:

# Subdomain Table

| Subdomain | Domain      | A          | CNAME            |
|-----------|-------------|------------|------------------|
| @         | example.com | 192.0.2.1  | -                |
| www       | example.com | -          | @                |
| ftp       | example.com | 192.0.2.2  | -                |
| mail      | example.com | -          | mail.example.com |

## How It Works

1. **Fetch Domains:**
    - Uses the GoDaddy API to retrieve a list of domains associated with the API credentials.
    - Handles pagination to ensure all domains are fetched.
2. **Fetch Subdomains:**
    - Retrieves DNS records (A and CNAME) for each domain.
    - Adds the corresponding domain name to each subdomain record for clarity.
3. **Generate Markdown Table:**
    - Formats the subdomain data into a Markdown table for easy readability.

## Error Handling

- **Failed API Requests:**
  - Logs a failure message for domains or subdomains that cannot be fetched.
- **Malformed Responses:**
  - Ensures malformed JSON responses do not crash the script by wrapping objects into arrays when necessary.

## Example

**Command:**
```bash
./script_name.sh
```

**Output:**
A file named `subdomains_table.md` with the formatted table.

## Customization

- **PAGE_SIZE:** Adjust the number of domains fetched per API request by modifying the `PAGE_SIZE` variable.
- **File Paths:** Change the output file paths (`domains.json`, `subdomains.json`, `subdomains_table.md`) to suit your needs.

## License

This script is provided “as-is” without any warranties. You are free to modify and use it for personal or professional purposes.

## Author

Created by 0xDTC. Feel free to reach out for assistance or improvements!