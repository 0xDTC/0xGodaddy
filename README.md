<a href="https://www.buymeacoffee.com/0xDTC"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a knowledge&emoji=📖&slug=0xDTC&button_colour=FF5F5F&font_colour=ffffff&font_family=Comic&outline_colour=000000&coffee_colour=FFDD00" /></a>
___
# 0xGodaddy

This repository contains two Bash scripts designed to interact with GoDaddy’s services, each located in its respective subdirectory.

## Scripts Overview

### 1. Domain Pull Script

**Directory:** `Domain Pull`

**Description:**  
This script retrieves a list of all domains associated with your GoDaddy account. It’s useful for managing and auditing your domain portfolio.

**Features:**
- Fetches all domains linked to your GoDaddy account.
- Displays domain details in a user-friendly format.

**Usage:**
1. **Configuration:** Ensure your GoDaddy API key and secret are set as environment variables or modify the script to include them directly.
2. **Execution:** Run the script to display your domain information.

**Prerequisites:**
- Bash shell environment.
- cURL installed.
- GoDaddy API key and secret.

> **Note:** Keep your API credentials secure and avoid hard-coding them in publicly accessible files.

### 2. Subdomain Pull Script

**Directory:** `Subdomain Pull`

**Description:**  
This script retrieves all subdomains for a specified domain in your GoDaddy account. It’s helpful for managing DNS records and understanding your domain’s substructure.

**Features:**
- Fetches subdomains for a specified domain.
- Displays subdomain details in a clear format.

**Usage:**
1. **Configuration:** Set your GoDaddy API key and secret as environment variables or include them in the script.
2. **Execution:** Run the script with the target domain as an argument to display its subdomains.

**Prerequisites:**
- Bash shell environment.
- cURL installed.
- GoDaddy API key and secret.

> **Note:** Ensure you have the necessary permissions to access the domain’s DNS records.

## Getting Started

To utilize these scripts:

1. **Clone the Repository:**
```bash
git clone https://github.com/0xDTC/0xGodaddy.git
```

2. **Navigate to the Desired Script Directory:**
```bash
cd 0xGodaddy/'Domain Pull'
# or
cd 0xGodaddy/'Subdomain Pull'
```

3. **Review and Configure the Script:**
- Open the script file in a text editor.
- Update the configuration variables as per your requirements.

4. **Execute the Script:**
```bash
./script_name.sh
```

For more detailed information, refer to the individual README files located within each script’s subdirectory.
