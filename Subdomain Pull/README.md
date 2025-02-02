<a href="https://www.buymeacoffee.com/0xDTC"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a knowledge&emoji=📖&slug=0xDTC&button_colour=FF5F5F&font_colour=ffffff&font_family=Comic&outline_colour=000000&coffee_colour=FFDD00" /></a>

# Subdomain Table Generator

Automates domain and subdomain retrieval from GoDaddy and Cloudflare, then generates a sorted Markdown table.

## Features
- Fetch domains (with pagination).
- Retrieve DNS records (A, CNAME, etc.) from GoDaddy and Cloudflare.
- Group and sort records by domain and subdomain.
- Generate a clean Markdown table.
- Optional logging, error handling, and cleanup.

## Prerequisites
- Bash shell (Linux, macOS, or WSL).
- jq (for JSON parsing).  
    • Debian/Ubuntu: sudo apt install jq  
    • macOS: brew install jq  
    • Red Hat/CentOS: sudo yum install jq  
- GoDaddy API key/secret (saved in secret.txt).
- Cloudflare API token (saved in secret.txt).

## Installation
1. Clone the repo:  
     git clone https://github.com/0xdtc/0xGodaddy.git  
2. cd '0xGodaddy/Subdomain Pull'
3. chmod +x GDSubDomains.sh 

## Usage
./GDSubDomains.sh [-l]  
(-l enables logging; default logs to /dev/null.)

## What the Script Does
1. Fetch domains from GoDaddy.  
2. Fetch subdomain DNS records from GoDaddy and Cloudflare.  
3. Merge and sort results into final_subdomains.json.  
4. Generate subdomains_table.md organized by domain and subdomain.  
5. Clean up temporary files.

## Demo Output
| Subdomain | Domain      | Type  | Data              | Source     |
|-----------|------------ |-------|-------------------|------------|
| blog      | demo.com    | A     | 192.0.2.10        | GoDaddy    |
| mail      | demo.com    | A     | 192.0.2.20        | Cloudflare |
| shop      | demo.com    | CNAME | shop.demo.net     | Cloudflare |
| www       | demo.com    | CNAME | demo.com          | GoDaddy    |
| api       | sample.org  | A     | 203.0.113.5       | GoDaddy    |
| ftp       | sample.org  | A     | 203.0.113.15      | Cloudflare |
| app       | sample.org  | CNAME | app.sample.net    | Cloudflare |
| www       | sample.org  | CNAME | sample.org        | GoDaddy    |

## Customization
- Adjust PAGE_SIZE in the script for domain fetch size.
- Modify file paths as needed.

## Troubleshooting
- Check credentials in secret.txt.
- Ensure jq is installed and in PATH.
- Use -l flag for logs in script_debug.log.

## Support
Open an issue or buy me a coffee at the link above.