# Domain Fetch Script by **0xDTC**

This script, developed by 0xDTC, fetches domain data from the GoDaddy API and aggregates it into a single JSON file. It dynamically identifies and counts all domain statuses, ensuring flexibility for future additions.

## Features

1. **Fetch Domains:** Retrieves domain data from the GoDaddy API in pages and saves it in a JSON file (`domains.json`).
2. **Dynamic Aggregation:** Automatically identifies and counts all unique domain statuses.
3. **Pagination Support:** Handles large datasets by managing API pagination seamlessly.
4. **Human-Readable Output:** Generates a clear summary of domain statuses directly in the terminal.

## Prerequisites

1. **Bash Shell:**
    - Ensure you have a Bash shell environment (Linux/macOS/WSL on Windows).

2. **API Credentials:**
    - Create a `secret.txt` file in the same directory as the script and add the following:
    ```sh
    API_KEY="your_api_key"
    API_SECRET="your_api_secret"
    ```

3. **Dependencies:**
    - Install the JSON processor `jq` required for parsing API responses:
    ```sh
    sudo apt install jq     # For Debian/Ubuntu
    brew install jq         # For macOS
    sudo yum install jq     # For Red Hat/CentOS
    ```

## How to Use

### Step 1: Clone or Download the Script
- Save the script to your desired directory.

### Step 2: Configure `secret.txt`
- Create a `secret.txt` file with the following format:
    ```sh
    API_KEY="your_api_key"
    API_SECRET="your_api_secret"
    ```

### Step 3: Run the Script
- Make the script executable and run it:
    ```sh
    chmod +x script_name.sh   # Make the script executable
    ./script_name.sh          # Run the script
    ```

### Step 4: Review Output
- The fetched domains will be saved in `domains.json`.
- A dynamic summary of domain statuses will be printed to the terminal:

#### Counts of Domains by Status:
```
ACTIVE                   : 1138
CANCELLED                : 76
PENDING_TRANSFER         : 24
EXPIRED_REASSIGNED       : 1
Domains fetched successfully.
```

## Configuration Options

- **PAGE_SIZE:** Adjust the number of domains fetched per API request by modifying the `PAGE_SIZE` variable in the script.
- **Output File:** Change the name or path of the output file by editing the `output_file` variable.

## Error Handling

- If the API returns an empty response, the script will stop and display:
    ```
    Failed to fetch domains.
    ```
- If the script reaches the end of available data, it will stop further requests and display:
    ```
    No more pages to fetch.
    ```

## Example Output

### Terminal Output:
```
Counts of Domains by Status:
-----------------------------
ACTIVE                   : 1138
CANCELLED                : 76
PENDING_TRANSFER         : 24
EXPIRED_REASSIGNED       : 1
Domains fetched successfully.
```

### JSON File (`domains.json`):
```json
[
  {
    "domain": "example1.com",
    "status": "ACTIVE"
  },
  {
    "domain": "example2.com",
    "status": "CANCELLED"
  }
]
```