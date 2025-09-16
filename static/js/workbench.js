/**
 * Django Workbench JavaScript
 */

$(document).ready(function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-refresh token before expiry
    setupTokenRefresh();
    
    // Setup CSRF token for AJAX requests
    setupCSRF();
    
    // Initialize code editors
    setupCodeEditors();
    
    // Setup query result handlers
    setupQueryResults();
    
    // Setup bulk job monitoring
    setupBulkJobMonitoring();
});

/**
 * Setup automatic token refresh
 */
function setupTokenRefresh() {
    // Refresh token every 30 minutes
    setInterval(function() {
        refreshAccessToken();
    }, 30 * 60 * 1000);
}

/**
 * Refresh Salesforce access token
 */
function refreshAccessToken() {
    $.ajax({
        url: '/auth/refresh-token/',
        method: 'POST',
        success: function(response) {
            console.log('Token refreshed successfully');
        },
        error: function(xhr, status, error) {
            console.warn('Token refresh failed:', error);
            if (xhr.status === 401) {
                showToast('Session expired. Please log in again.', 'warning');
                setTimeout(function() {
                    window.location.href = '/auth/login/';
                }, 3000);
            }
        }
    });
}

/**
 * Setup CSRF token for AJAX requests
 */
function setupCSRF() {
    // Get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    const csrftoken = getCookie('csrftoken');
    
    // Setup AJAX defaults
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!this.crossDomain && settings.type !== 'GET') {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });
}

/**
 * Setup code editors with syntax highlighting and line numbers
 */
function setupCodeEditors() {
    $('.code-editor').each(function() {
        const editor = $(this);
        const mode = editor.data('mode') || 'text';
        
        // Add line numbers if requested
        if (editor.data('line-numbers')) {
            addLineNumbers(editor);
        }
        
        // Auto-resize
        editor.on('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    });
}

/**
 * Add line numbers to code editor
 */
function addLineNumbers(editor) {
    const wrapper = $('<div class="code-editor-wrapper"></div>');
    const lineNumbers = $('<div class="line-numbers"></div>');
    
    editor.wrap(wrapper);
    editor.before(lineNumbers);
    
    function updateLineNumbers() {
        const lines = editor.val().split('\n');
        let lineNumbersHtml = '';
        for (let i = 1; i <= lines.length; i++) {
            lineNumbersHtml += i + '\n';
        }
        lineNumbers.text(lineNumbersHtml);
    }
    
    editor.on('input scroll', updateLineNumbers);
    updateLineNumbers();
}

/**
 * Setup query result handlers
 */
function setupQueryResults() {
    // Export results functionality
    $(document).on('click', '.export-results', function(e) {
        e.preventDefault();
        const format = $(this).data('format');
        const queryId = $(this).data('query-id');
        exportQueryResults(queryId, format);
    });
    
    // Load more results
    $(document).on('click', '.load-more-results', function(e) {
        e.preventDefault();
        const nextUrl = $(this).data('next-url');
        loadMoreResults(nextUrl);
    });
    
    // Copy to clipboard
    $(document).on('click', '.copy-to-clipboard', function(e) {
        e.preventDefault();
        const text = $(this).data('text') || $(this).parent().find('code').text();
        copyToClipboard(text);
    });
}

/**
 * Export query results in specified format
 */
function exportQueryResults(queryId, format) {
    const url = `/query/export/${queryId}/?format=${format}`;
    
    // Create temporary download link
    const link = document.createElement('a');
    link.href = url;
    link.download = `query_results_${queryId}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Load more query results
 */
function loadMoreResults(nextUrl) {
    const resultsContainer = $('.query-results-table tbody');
    const loadMoreBtn = $('.load-more-results');
    
    loadMoreBtn.html('<span class="loading-spinner"></span> Loading...');
    
    $.get(nextUrl)
        .done(function(response) {
            resultsContainer.append(response.html);
            
            if (response.nextRecordsUrl) {
                loadMoreBtn.data('next-url', response.nextRecordsUrl);
                loadMoreBtn.html('Load More Results');
            } else {
                loadMoreBtn.hide();
            }
        })
        .fail(function() {
            loadMoreBtn.html('Load More Results');
            showToast('Failed to load more results', 'error');
        });
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showToast('Copied to clipboard', 'success');
        }).catch(function() {
            fallbackCopyToClipboard(text);
        });
    } else {
        fallbackCopyToClipboard(text);
    }
}

/**
 * Fallback copy to clipboard for older browsers
 */
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showToast('Copied to clipboard', 'success');
    } catch (err) {
        showToast('Failed to copy to clipboard', 'error');
    }
    
    document.body.removeChild(textArea);
}

/**
 * Setup bulk job monitoring
 */
function setupBulkJobMonitoring() {
    // Auto-refresh job status
    if ($('.bulk-job-status').length > 0) {
        setInterval(refreshBulkJobStatus, 5000);
    }
    
    // Manual refresh button
    $(document).on('click', '.refresh-job-status', function(e) {
        e.preventDefault();
        const jobId = $(this).data('job-id');
        refreshJobStatus(jobId);
    });
}

/**
 * Refresh bulk job status
 */
function refreshBulkJobStatus() {
    $('.bulk-job-status').each(function() {
        const statusContainer = $(this);
        const jobId = statusContainer.data('job-id');
        const currentStatus = statusContainer.data('status');
        
        // Don't refresh completed or failed jobs
        if (currentStatus === 'completed' || currentStatus === 'failed' || currentStatus === 'aborted') {
            return;
        }
        
        refreshJobStatus(jobId);
    });
}

/**
 * Refresh individual job status
 */
function refreshJobStatus(jobId) {
    $.get(`/bulk/job/${jobId}/status/`)
        .done(function(response) {
            const statusContainer = $(`.bulk-job-status[data-job-id="${jobId}"]`);
            statusContainer.replaceWith(response.html);
        })
        .fail(function() {
            console.warn(`Failed to refresh status for job ${jobId}`);
        });
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info', duration = 5000) {
    const toastId = 'toast-' + Date.now();
    const toastClass = type === 'error' ? 'bg-danger' : type === 'success' ? 'bg-success' : type === 'warning' ? 'bg-warning' : 'bg-info';
    
    const toastHtml = `
        <div id="${toastId}" class="toast ${toastClass} text-white" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header ${toastClass} text-white border-0">
                <strong class="me-auto">Workbench</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast container if it doesn't exist
    if ($('.toast-container').length === 0) {
        $('body').append('<div class="toast-container"></div>');
    }
    
    $('.toast-container').append(toastHtml);
    
    const toast = new bootstrap.Toast(document.getElementById(toastId), {
        autohide: true,
        delay: duration
    });
    
    toast.show();
    
    // Remove toast element after it's hidden
    $(`#${toastId}`).on('hidden.bs.toast', function() {
        $(this).remove();
    });
}

/**
 * Format JSON with syntax highlighting
 */
function formatJSON(jsonString, container) {
    try {
        const obj = JSON.parse(jsonString);
        const formatted = JSON.stringify(obj, null, 2);
        
        // Basic syntax highlighting
        const highlighted = formatted
            .replace(/"([^"]+)":/g, '<span class="json-key">"$1":</span>')
            .replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>')
            .replace(/: (\d+)/g, ': <span class="json-number">$1</span>')
            .replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>');
        
        container.html(`<pre><code>${highlighted}</code></pre>`);
    } catch (e) {
        container.html(`<pre><code>${jsonString}</code></pre>`);
    }
}

/**
 * Debounce function
 */
function debounce(func, wait, immediate) {
    let timeout;
    return function executedFunction() {
        const context = this;
        const args = arguments;
        const later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

/**
 * Validate SOQL query syntax (basic)
 */
function validateSOQL(query) {
    const errors = [];
    
    // Check for SELECT
    if (!/^\s*SELECT\s+/i.test(query)) {
        errors.push('Query must start with SELECT');
    }
    
    // Check for FROM
    if (!/\bFROM\s+\w+/i.test(query)) {
        errors.push('Query must include FROM clause');
    }
    
    // Check for balanced parentheses
    const openParens = (query.match(/\(/g) || []).length;
    const closeParens = (query.match(/\)/g) || []).length;
    if (openParens !== closeParens) {
        errors.push('Unbalanced parentheses');
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

/**
 * Validate SOSL query syntax (basic)
 */
function validateSOSL(query) {
    const errors = [];
    
    // Check for FIND
    if (!/^\s*FIND\s+/i.test(query)) {
        errors.push('Search must start with FIND');
    }
    
    // Check for IN clause
    if (!/\bIN\s+(ALL\s+FIELDS|NAME\s+FIELDS|EMAIL\s+FIELDS|PHONE\s+FIELDS|SIDEBAR\s+FIELDS)/i.test(query)) {
        errors.push('Search must include IN clause with field specification');
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

// Global utility functions
window.workbench = {
    showToast: showToast,
    copyToClipboard: copyToClipboard,
    formatJSON: formatJSON,
    validateSOQL: validateSOQL,
    validateSOSL: validateSOSL,
    refreshAccessToken: refreshAccessToken
};