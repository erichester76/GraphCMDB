/**
 * List View Column Management and Filtering
 * Handles column visibility, local storage persistence, and client-side filtering
 */

(function() {
    'use strict';

    const STORAGE_KEY_PREFIX = 'cmdb_list_columns_';

    /**
     * Get the current label from the page
     */
    function getCurrentLabel() {
        const titleElement = document.getElementById('page-title');
        if (titleElement) {
            const text = titleElement.textContent.trim();
            const match = text.match(/^(.+?)\s+Nodes$/);
            return match ? match[1] : null;
        }
        return null;
    }

    /**
     * Get storage key for current label
     */
    function getStorageKey() {
        const label = getCurrentLabel();
        return label ? STORAGE_KEY_PREFIX + label : null;
    }

    /**
     * Load column preferences from local storage
     */
    function loadColumnPreferences() {
        const key = getStorageKey();
        if (!key) return null;
        
        try {
            const stored = localStorage.getItem(key);
            return stored ? JSON.parse(stored) : null;
        } catch (e) {
            console.error('Failed to load column preferences:', e);
            return null;
        }
    }

    /**
     * Save column preferences to local storage
     */
    function saveColumnPreferences(columns) {
        const key = getStorageKey();
        if (!key) return;
        
        try {
            localStorage.setItem(key, JSON.stringify(columns));
        } catch (e) {
            console.error('Failed to save column preferences:', e);
        }
    }

    /**
     * Get currently visible columns from checkboxes
     */
    function getVisibleColumns() {
        const checkboxes = document.querySelectorAll('.column-toggle:checked');
        return Array.from(checkboxes).map(cb => cb.dataset.column);
    }

    /**
     * Apply column visibility based on current checkboxes
     */
    function applyColumnVisibility() {
        const visibleColumns = getVisibleColumns();
        
        // Hide/show header columns
        const headerCells = document.querySelectorAll('thead th[data-column]');
        headerCells.forEach(cell => {
            const column = cell.dataset.column;
            cell.style.display = visibleColumns.includes(column) ? '' : 'none';
        });
        
        // Hide/show body columns
        const bodyCells = document.querySelectorAll('tbody td[data-column]');
        bodyCells.forEach(cell => {
            const column = cell.dataset.column;
            cell.style.display = visibleColumns.includes(column) ? '' : 'none';
        });
        
        // Save preferences
        saveColumnPreferences(visibleColumns);
    }

    /**
     * Apply saved column preferences to checkboxes
     */
    function applySavedPreferences() {
        const savedColumns = loadColumnPreferences();
        if (!savedColumns || savedColumns.length === 0) return;
        
        // Update checkboxes based on saved preferences
        const checkboxes = document.querySelectorAll('.column-toggle');
        checkboxes.forEach(cb => {
            cb.checked = savedColumns.includes(cb.dataset.column);
        });
        
        // Apply visibility
        applyColumnVisibility();
    }

    /**
     * Initialize column selector dropdown
     */
    function initColumnSelector() {
        const button = document.getElementById('column-selector-btn');
        const dropdown = document.getElementById('column-selector-dropdown');
        
        if (!button || !dropdown) return;
        
        // Toggle dropdown
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            dropdown.classList.toggle('hidden');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!dropdown.contains(e.target) && e.target !== button) {
                dropdown.classList.add('hidden');
            }
        });
        
        // Prevent dropdown from closing when clicking inside
        dropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        
        // Handle column toggle changes
        const checkboxes = document.querySelectorAll('.column-toggle');
        checkboxes.forEach(cb => {
            cb.addEventListener('change', function() {
                applyColumnVisibility();
            });
        });
        
        // Apply saved preferences on load
        applySavedPreferences();
    }

    /**
     * Initialize filtering functionality
     */
    function initFiltering() {
        const filterInput = document.getElementById('filter-input');
        const clearButton = document.getElementById('clear-filter');
        
        if (!filterInput) return;
        
        // Show/hide clear button
        filterInput.addEventListener('input', function() {
            if (this.value.trim()) {
                clearButton?.classList.remove('hidden');
            } else {
                clearButton?.classList.add('hidden');
            }
            applyFilter();
        });
        
        // Clear filter
        clearButton?.addEventListener('click', function() {
            filterInput.value = '';
            clearButton.classList.add('hidden');
            applyFilter();
        });
    }

    /**
     * Apply filter to table rows
     */
    function applyFilter() {
        const filterInput = document.getElementById('filter-input');
        if (!filterInput) return;
        
        const filterText = filterInput.value.toLowerCase().trim();
        const rows = document.querySelectorAll('tbody .node-row');
        
        rows.forEach(row => {
            if (!filterText) {
                row.style.display = '';
                return;
            }
            
            // Get all visible cell text
            const cells = row.querySelectorAll('td');
            const rowText = Array.from(cells)
                .map(cell => cell.textContent.toLowerCase())
                .join(' ');
            
            // Show/hide based on match
            row.style.display = rowText.includes(filterText) ? '' : 'none';
        });
    }

    /**
     * Initialize all list view functionality
     */
    function initListView() {
        initColumnSelector();
        initFiltering();
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initListView);
    } else {
        initListView();
    }

    // Re-initialize after HTMX swaps
    document.body.addEventListener('htmx:afterSwap', function(event) {
        // Only re-init if the swap target is related to list view
        if (event.detail.target.id === 'nodes-content' || 
            event.detail.target.id === 'header-actions') {
            // Small delay to ensure DOM is fully updated
            setTimeout(initListView, 50);
        }
    });

})();
