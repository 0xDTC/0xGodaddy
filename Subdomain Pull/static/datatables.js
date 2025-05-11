/**
 * Custom DataTables Implementation
 * Provides sorting, filtering, and pagination without external dependencies
 */
class CustomDataTable {
    constructor(tableElement, options = {}) {
        this.table = tableElement;
        this.options = Object.assign({
            rowsPerPage: -1, // Show all records by default
            pagingOptions: [10, 25, 50, 100, 250, 500, -1],
            fixedHeader: true
        }, options);
        
        this.originalData = [];
        this.filteredData = [];
        this.currentPage = 0;
        this.sortColumn = 0; // Default sort by Domain
        this.sortDirection = 'asc';
        this.searchTerm = '';
        this.columnFilters = {};
        
        this.init();
    }
    
    init() {
        // Extract table data
        this.extractTableData();
        
        // Create table wrapper elements
        this.createTableStructure();
        
        // Add event listeners
        this.addEventListeners();
        
        // Initial sort and render
        this.sort();
        this.render();
    }
    
    extractTableData() {
        // Get headers
        this.headers = Array.from(this.table.querySelectorAll('thead tr:first-child th')).map(th => th.textContent.trim());
        
        // Get all rows data
        const rows = this.table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = Array.from(row.querySelectorAll('td')).map(td => td.innerHTML);
            const classNames = row.className;
            this.originalData.push({
                data: cells,
                classNames: classNames
            });
        });
        
        this.filteredData = [...this.originalData];
    }
    
    createTableStructure() {
        // Create filter row directly below header
        const thead = this.table.querySelector('thead');
        const filterRow = document.createElement('tr');
        filterRow.className = 'filter-row';
        
        this.headers.forEach((header, index) => {
            const filterCell = document.createElement('th');
            filterCell.className = 'filter-cell';
            filterCell.setAttribute('data-no-sort', 'true');
            
            const filterContainer = document.createElement('div');
            filterContainer.className = 'filter-container';
            
            const input = document.createElement('input');
            input.className = 'column-filter';
            input.placeholder = `Filter ${header}...`;
            input.dataset.columnIndex = index;
            input.setAttribute('aria-label', `Filter ${header}`);
            
            filterContainer.appendChild(input);
            filterCell.appendChild(filterContainer);
            filterRow.appendChild(filterCell);
        });
        
        thead.appendChild(filterRow);
        
        // Create pagination container
        const paginationContainer = document.createElement('div');
        paginationContainer.className = 'pagination-container';
        
        this.paginationInfo = document.createElement('div');
        this.paginationInfo.className = 'table-info';
        
        this.paginationControls = document.createElement('ul');
        this.paginationControls.className = 'pagination';
        
        const pageSizeSelector = document.createElement('select');
        pageSizeSelector.className = 'page-size-selector';
        this.options.pagingOptions.forEach(size => {
            const option = document.createElement('option');
            option.value = size;
            option.textContent = size === -1 ? 'All' : size;
            pageSizeSelector.appendChild(option);
        });
        pageSizeSelector.value = this.options.rowsPerPage;
        
        const pageSizeContainer = document.createElement('div');
        pageSizeContainer.className = 'page-size-container';
        pageSizeContainer.textContent = 'Rows per page: ';
        pageSizeContainer.appendChild(pageSizeSelector);
        
        paginationContainer.appendChild(this.paginationInfo);
        paginationContainer.appendChild(this.paginationControls);
        paginationContainer.appendChild(pageSizeContainer);
        
        this.table.parentNode.insertBefore(paginationContainer, this.table.nextSibling);
    }
    
    addEventListeners() {
        // Column sorting
        const headerCells = this.table.querySelectorAll('thead tr:first-child th');
        headerCells.forEach((th, index) => {
            th.addEventListener('click', () => this.sortBy(index));
            
            // Show initial sort indicator
            if (index === this.sortColumn) {
                th.classList.add(this.sortDirection === 'asc' ? 'sorting-asc' : 'sorting-desc');
            }
        });
        
        // Column filtering
        const filterInputs = this.table.querySelectorAll('.column-filter');
        filterInputs.forEach(input => {
            input.addEventListener('input', () => {
                const columnIndex = parseInt(input.dataset.columnIndex);
                this.columnFilters[columnIndex] = input.value.toLowerCase();
                this.applyFilters();
            });
        });
        
        // Page size selector
        const pageSizeSelector = this.table.parentNode.querySelector('.page-size-selector');
        pageSizeSelector.addEventListener('change', () => {
            this.options.rowsPerPage = parseInt(pageSizeSelector.value);
            this.currentPage = 0;
            this.render();
        });
    }
    
    sortBy(columnIndex) {
        if (this.sortColumn === columnIndex) {
            // Toggle direction if already sorting by this column
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = columnIndex;
            this.sortDirection = 'asc';
        }
        
        this.sort();
        this.render();
    }
    
    sort() {
        if (this.sortColumn === null) return;
        
        const headerCells = this.table.querySelectorAll('thead tr:first-child th');
        headerCells.forEach(th => {
            th.classList.remove('sorting-asc', 'sorting-desc');
        });
        
        const currentHeaderCell = headerCells[this.sortColumn];
        currentHeaderCell.classList.add(this.sortDirection === 'asc' ? 'sorting-asc' : 'sorting-desc');
        
        this.filteredData.sort((a, b) => {
            const valueA = a.data[this.sortColumn].replace(/<[^>]*>/g, '').toLowerCase();
            const valueB = b.data[this.sortColumn].replace(/<[^>]*>/g, '').toLowerCase();
            
            // Try numeric sort if possible
            const numA = parseFloat(valueA);
            const numB = parseFloat(valueB);
            
            if (!isNaN(numA) && !isNaN(numB)) {
                return this.sortDirection === 'asc' ? numA - numB : numB - numA;
            }
            
            // Fall back to string sort
            if (valueA < valueB) return this.sortDirection === 'asc' ? -1 : 1;
            if (valueA > valueB) return this.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }
    
    search(term) {
        this.searchTerm = term.toLowerCase();
        this.applyFilters();
        return this;
    }
    
    applyFilters() {
        this.filteredData = this.originalData.filter(row => {
            // Global search
            if (this.searchTerm) {
                const rowText = row.data.join(' ').toLowerCase();
                if (!rowText.includes(this.searchTerm)) return false;
            }
            
            // Column filters
            for (const [columnIndex, filterValue] of Object.entries(this.columnFilters)) {
                if (filterValue && !row.data[columnIndex].toLowerCase().includes(filterValue)) {
                    return false;
                }
            }
            
            return true;
        });
        
        // Reset to first page and re-sort
        this.currentPage = 0;
        if (this.sortColumn !== null) {
            this.sort();
        }
        
        this.render();
        return this;
    }
    
    draw() {
        this.render();
        return this;
    }
    
    columns() {
        // Return a proxy object to maintain compatibility
        return {
            every: (callback) => {
                this.headers.forEach((header, index) => {
                    callback.call({
                        search: (term) => {
                            this.columnFilters[index] = term.toLowerCase();
                            this.applyFilters();
                            return { draw: () => this.draw() };
                        },
                        footer: () => {
                            return this.table.querySelector('thead tr.filter-row th:nth-child(' + (index + 1) + ')');
                        }
                    });
                });
            }
        };
    }
    
    render() {
        const tbody = this.table.querySelector('tbody');
        tbody.innerHTML = '';
        
        const totalRows = this.filteredData.length;
        const rowsPerPage = this.options.rowsPerPage === -1 ? totalRows : this.options.rowsPerPage;
        const startIndex = this.currentPage * rowsPerPage;
        const endIndex = Math.min(startIndex + rowsPerPage, totalRows);
        
        // Render visible rows
        for (let i = startIndex; i < endIndex; i++) {
            const rowData = this.filteredData[i];
            const tr = document.createElement('tr');
            tr.className = rowData.classNames;
            
            rowData.data.forEach(cellData => {
                const td = document.createElement('td');
                td.innerHTML = cellData;
                tr.appendChild(td);
            });
            
            tbody.appendChild(tr);
        }
        
        // Update pagination info
        this.updatePagination(totalRows, startIndex, endIndex);
    }
    
    updatePagination(totalRows, startIndex, endIndex) {
        // Update info text
        this.paginationInfo.textContent = `Showing ${totalRows > 0 ? startIndex + 1 : 0} to ${endIndex} of ${totalRows} entries`;
        
        // Calculate pagination
        const rowsPerPage = this.options.rowsPerPage === -1 ? totalRows : this.options.rowsPerPage;
        const totalPages = rowsPerPage === -1 ? 1 : Math.ceil(totalRows / rowsPerPage);
        
        // Update pagination controls
        this.paginationControls.innerHTML = '';
        
        if (totalPages <= 1) {
            return;
        }
        
        // Previous button
        const prevButton = document.createElement('li');
        const prevBtn = document.createElement('button');
        prevBtn.textContent = 'Previous';
        prevBtn.disabled = this.currentPage === 0;
        prevBtn.addEventListener('click', () => {
            if (this.currentPage > 0) {
                this.currentPage--;
                this.render();
            }
        });
        prevButton.appendChild(prevBtn);
        this.paginationControls.appendChild(prevButton);
        
        // Page numbers (showing at most 7)
        const maxVisiblePages = 7;
        let startPage = Math.max(0, Math.min(this.currentPage - Math.floor(maxVisiblePages / 2), totalPages - maxVisiblePages));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages);
        
        // First page
        if (startPage > 0) {
            const firstPageButton = document.createElement('li');
            const btn = document.createElement('button');
            btn.textContent = '1';
            btn.addEventListener('click', () => {
                this.currentPage = 0;
                this.render();
            });
            firstPageButton.appendChild(btn);
            this.paginationControls.appendChild(firstPageButton);
            
            if (startPage > 1) {
                const ellipsis = document.createElement('li');
                ellipsis.textContent = '...';
                ellipsis.className = 'ellipsis';
                this.paginationControls.appendChild(ellipsis);
            }
        }
        
        // Page numbers
        for (let i = startPage; i < endPage; i++) {
            const pageButton = document.createElement('li');
            const btn = document.createElement('button');
            btn.textContent = i + 1;
            btn.classList.toggle('active', i === this.currentPage);
            btn.addEventListener('click', () => {
                this.currentPage = i;
                this.render();
            });
            pageButton.appendChild(btn);
            this.paginationControls.appendChild(pageButton);
        }
        
        // Last page
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                const ellipsis = document.createElement('li');
                ellipsis.textContent = '...';
                ellipsis.className = 'ellipsis';
                this.paginationControls.appendChild(ellipsis);
            }
            
            const lastPageButton = document.createElement('li');
            const btn = document.createElement('button');
            btn.textContent = totalPages;
            btn.addEventListener('click', () => {
                this.currentPage = totalPages - 1;
                this.render();
            });
            lastPageButton.appendChild(btn);
            this.paginationControls.appendChild(lastPageButton);
        }
        
        // Next button
        const nextButton = document.createElement('li');
        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Next';
        nextBtn.disabled = this.currentPage >= totalPages - 1;
        nextBtn.addEventListener('click', () => {
            if (this.currentPage < totalPages - 1) {
                this.currentPage++;
                this.render();
            }
        });
        nextButton.appendChild(nextBtn);
        this.paginationControls.appendChild(nextButton);
    }
}

// Initialize the table when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize DataTable for the DNS records table
    const table = document.getElementById('dns_records');
    if (table) {
        const dt = new CustomDataTable(table, {
            rowsPerPage: -1, // Show all records by default
            fixedHeader: true
        });
        
        // Global search
        const globalSearchInput = document.getElementById('globalSearch');
        if (globalSearchInput) {
            globalSearchInput.addEventListener('input', () => {
                const term = globalSearchInput.value;
                dt.search(term).draw();
            });
            
            // Add keyboard shortcut (Ctrl+F or Cmd+F) focus on search
            document.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
                    e.preventDefault(); // Prevent default browser search
                    globalSearchInput.focus();
                }
            });
        }
    }
});
