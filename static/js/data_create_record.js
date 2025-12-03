(function() {
    const form = document.getElementById('create-record-form');
    if (!form) {
        return;
    }

    const messagesContainer = document.getElementById('insert-messages');
    const sobjectValueField = document.getElementById('sobject-select');
    const sobjectDropdown = document.getElementById('sobject-dropdown');
    const sobjectMenu = document.getElementById('sobject-dropdown-menu');
    const sobjectOptionList = document.getElementById('sobject-option-list');
    const sobjectFilterInput = document.getElementById('sobject-filter-input');
    const sobjectSelectedDisplay = document.getElementById('sobject-selected-display');
    const sobjectNoResults = document.getElementById('sobject-no-results');
    const modeSelect = document.getElementById('mode-select');
    const fileUploadGroup = document.getElementById('file-upload-group');
    const csvFileInput = document.getElementById('csv-file-input');
    const nextButton = document.getElementById('next-button');

    const singleConfigSection = document.getElementById('single-record-config');
    const singleTableBody = document.querySelector('#single-record-table tbody');
    const addSingleFieldButton = document.getElementById('add-single-field');
    const singleInsertButton = document.getElementById('single-insert-button');

    const csvConfigSection = document.getElementById('csv-config');
    const csvTableBody = document.querySelector('#csv-mapping-table tbody');
    const addCsvMappingButton = document.getElementById('add-csv-mapping');
    const csvInsertButton = document.getElementById('csv-insert-button');
    const selectStepSection = form;
    const singleBackButton = document.getElementById('single-back-button');
    const csvBackButton = document.getElementById('csv-back-button');
    const singleConfirmSection = document.getElementById('single-confirm-section');
    const singleConfirmTableBody = document.querySelector('#single-confirm-table tbody');
    const singleConfirmObject = document.getElementById('single-confirm-object');
    const singleConfirmEditButton = document.getElementById('single-confirm-edit-button');
    const singleConfirmInsertButton = document.getElementById('single-confirm-insert-button');
    const csvConfirmSection = document.getElementById('csv-confirm-section');
    const csvConfirmObject = document.getElementById('csv-confirm-object');
    const csvConfirmMappingList = document.getElementById('csv-confirm-mapping-list');
    const csvPreviewCount = document.getElementById('csv-preview-count');
    const csvPreviewTableHead = document.getElementById('csv-preview-table-head');
    const csvPreviewTableBody = document.querySelector('#csv-preview-table tbody');
    const csvConfirmEditButton = document.getElementById('csv-confirm-edit-button');
    const csvConfirmInsertButton = document.getElementById('csv-confirm-insert-button');
    const resultSection = document.getElementById('operation-result-section');
    const resultMessageContainer = document.getElementById('operation-result-message');
    const resultErrorWrapper = document.getElementById('operation-error-table-wrapper');
    const resultErrorTableBody = document.querySelector('#operation-error-table tbody');
    const resultBackButton = document.getElementById('result-back-button');

    const state = {
        sobject: '',
        mode: 'single',
        fieldsCache: {},
        currentFields: [],
        requiredFields: [],
        csvHeaders: [],
        csvFile: null,
        objectFilter: '',
        dropdownOpen: false,
        selectedOption: null,
        pendingSinglePayload: null,
        pendingCsvMappings: [],
        pendingCsvPreview: null,
        pendingCsvTotalRows: 0,
        pendingCsvHeaders: [],
        lastOperation: null,
    };

    const fieldsEndpoint = window.DATA_FIELDS_ENDPOINT;
    const submitUrl = window.CREATE_RECORD_POST_URL;

    function normaliseText(value) {
        return (value || '').toString().trim().toLowerCase();
    }

    const sobjectOptionsDataElement = document.getElementById('sobject-options-data');
    const rawSobjectOptions = sobjectOptionsDataElement ? JSON.parse(sobjectOptionsDataElement.textContent) : [];
    const sobjectOptions = (Array.isArray(rawSobjectOptions) ? rawSobjectOptions : []).map((option) => {
        const apiName = option.name || option.value || '';
        const label = option.label || apiName;
        return {
            value: apiName,
            label: `${label} (${apiName})`,
            searchText: `${label} (${apiName}) ${apiName}`.toLowerCase(),
            raw: option,
        };
    });

    function getOptionButtons() {
        return Array.from(sobjectOptionList ? sobjectOptionList.querySelectorAll('[data-value]') : []);
    }

    function updateSobjectSelectionVisuals(selectedValue) {
        getOptionButtons().forEach((button) => {
            const isActive = button.dataset.value === selectedValue;
            button.classList.toggle('active', isActive);
            button.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });
    }

    function clearConfigTables() {
        singleTableBody.innerHTML = '';
        csvTableBody.innerHTML = '';
        state.currentFields = [];
        state.requiredFields = [];
        state.csvHeaders = [];
    }

    function showSelectStep() {
        if (selectStepSection) {
            selectStepSection.classList.remove('d-none');
            selectStepSection.setAttribute('aria-hidden', 'false');
        }
        singleConfigSection.classList.add('d-none');
        singleConfigSection.setAttribute('aria-hidden', 'true');
        csvConfigSection.classList.add('d-none');
        csvConfigSection.setAttribute('aria-hidden', 'true');
        if (singleConfirmSection) {
            singleConfirmSection.classList.add('d-none');
            singleConfirmSection.setAttribute('aria-hidden', 'true');
        }
        if (csvConfirmSection) {
            csvConfirmSection.classList.add('d-none');
            csvConfirmSection.setAttribute('aria-hidden', 'true');
        }
        if (resultSection) {
            resultSection.classList.add('d-none');
            resultSection.setAttribute('aria-hidden', 'true');
        }
        closeSobjectDropdown(false);
        state.mode = modeSelect.value;
        toggleFileUploadVisibility();
    }

    function showSingleStep() {
        if (selectStepSection) {
            selectStepSection.classList.add('d-none');
            selectStepSection.setAttribute('aria-hidden', 'true');
        }
        singleConfigSection.classList.remove('d-none');
        singleConfigSection.setAttribute('aria-hidden', 'false');
        csvConfigSection.classList.add('d-none');
        csvConfigSection.setAttribute('aria-hidden', 'true');
        if (singleConfirmSection) {
            singleConfirmSection.classList.add('d-none');
            singleConfirmSection.setAttribute('aria-hidden', 'true');
        }
        if (csvConfirmSection) {
            csvConfirmSection.classList.add('d-none');
            csvConfirmSection.setAttribute('aria-hidden', 'true');
        }
        if (resultSection) {
            resultSection.classList.add('d-none');
            resultSection.setAttribute('aria-hidden', 'true');
        }
        state.mode = 'single';
        if (singleBackButton) {
            singleBackButton.focus();
        }
    }

    function showCsvStep() {
        if (selectStepSection) {
            selectStepSection.classList.add('d-none');
            selectStepSection.setAttribute('aria-hidden', 'true');
        }
        csvConfigSection.classList.remove('d-none');
        csvConfigSection.setAttribute('aria-hidden', 'false');
        singleConfigSection.classList.add('d-none');
        singleConfigSection.setAttribute('aria-hidden', 'true');
        if (singleConfirmSection) {
            singleConfirmSection.classList.add('d-none');
            singleConfirmSection.setAttribute('aria-hidden', 'true');
        }
        if (csvConfirmSection) {
            csvConfirmSection.classList.add('d-none');
            csvConfirmSection.setAttribute('aria-hidden', 'true');
        }
        if (resultSection) {
            resultSection.classList.add('d-none');
            resultSection.setAttribute('aria-hidden', 'true');
        }
        state.mode = 'csv';
        if (csvBackButton) {
            csvBackButton.focus();
        }
    }

    function showSingleConfirmStep(payload) {
        if (!singleConfirmSection) {
            return;
        }
        state.pendingSinglePayload = payload;
        singleConfirmTableBody.innerHTML = '';
        payload.forEach((item) => {
            const row = document.createElement('tr');
            const fieldCell = document.createElement('td');
            fieldCell.textContent = item.field || item.name || '';
            const valueCell = document.createElement('td');
            valueCell.textContent = item.value !== undefined && item.value !== null && item.value !== '' ? item.value : '（空）';
            row.appendChild(fieldCell);
            row.appendChild(valueCell);
            singleConfirmTableBody.appendChild(row);
        });
        if (singleConfirmObject) {
            singleConfirmObject.textContent = state.selectedOption ? state.selectedOption.label : state.sobject || '--';
        }
        singleConfigSection.classList.add('d-none');
        singleConfigSection.setAttribute('aria-hidden', 'true');
        selectStepSection.classList.add('d-none');
        selectStepSection.setAttribute('aria-hidden', 'true');
        csvConfigSection.classList.add('d-none');
        csvConfigSection.setAttribute('aria-hidden', 'true');
        if (csvConfirmSection) {
            csvConfirmSection.classList.add('d-none');
            csvConfirmSection.setAttribute('aria-hidden', 'true');
        }
        if (resultSection) {
            resultSection.classList.add('d-none');
            resultSection.setAttribute('aria-hidden', 'true');
        }
        singleConfirmSection.classList.remove('d-none');
        singleConfirmSection.setAttribute('aria-hidden', 'false');
        if (singleConfirmEditButton) {
            singleConfirmEditButton.focus();
        }
    }

    function showCsvConfirmStep({ headers, rows, totalRows, mappings }) {
        if (!csvConfirmSection) {
            return;
        }
        state.pendingCsvPreview = rows;
        state.pendingCsvHeaders = headers;
        state.pendingCsvTotalRows = totalRows;
        state.pendingCsvMappings = mappings;

        csvPreviewTableHead.innerHTML = '';
        headers.forEach((header) => {
            const th = document.createElement('th');
            th.textContent = header || '';
            csvPreviewTableHead.appendChild(th);
        });

        csvPreviewTableBody.innerHTML = '';
        const maxRows = 5;
        rows.slice(0, maxRows).forEach((row) => {
            const tr = document.createElement('tr');
            headers.forEach((_, index) => {
                const td = document.createElement('td');
                td.textContent = row[index] !== undefined ? row[index] : '';
                tr.appendChild(td);
            });
            csvPreviewTableBody.appendChild(tr);
        });

        if (csvPreviewCount) {
            const displayCount = Math.min(rows.length, maxRows);
            csvPreviewCount.textContent = `${displayCount}/${totalRows}`;
        }

        if (csvConfirmObject) {
            csvConfirmObject.textContent = state.selectedOption ? state.selectedOption.label : state.sobject || '--';
        }

        if (csvConfirmMappingList) {
            csvConfirmMappingList.innerHTML = '';
            mappings.forEach((mapping) => {
                const li = document.createElement('li');
                li.textContent = `${mapping.field || ''} ← ${mapping.csvField || ''}`;
                csvConfirmMappingList.appendChild(li);
            });
        }

        selectStepSection.classList.add('d-none');
        selectStepSection.setAttribute('aria-hidden', 'true');
        singleConfigSection.classList.add('d-none');
        singleConfigSection.setAttribute('aria-hidden', 'true');
        if (singleConfirmSection) {
            singleConfirmSection.classList.add('d-none');
            singleConfirmSection.setAttribute('aria-hidden', 'true');
        }
        if (resultSection) {
            resultSection.classList.add('d-none');
            resultSection.setAttribute('aria-hidden', 'true');
        }
        csvConfigSection.classList.add('d-none');
        csvConfigSection.setAttribute('aria-hidden', 'true');
        csvConfirmSection.classList.remove('d-none');
        csvConfirmSection.setAttribute('aria-hidden', 'false');
        if (csvConfirmEditButton) {
            csvConfirmEditButton.focus();
        }
    }

    function showResultSection({ success, message, errors }) {
        if (!resultSection) {
            return;
        }
        selectStepSection.classList.add('d-none');
        selectStepSection.setAttribute('aria-hidden', 'true');
        singleConfigSection.classList.add('d-none');
        singleConfigSection.setAttribute('aria-hidden', 'true');
        csvConfigSection.classList.add('d-none');
        csvConfigSection.setAttribute('aria-hidden', 'true');
        if (singleConfirmSection) {
            singleConfirmSection.classList.add('d-none');
            singleConfirmSection.setAttribute('aria-hidden', 'true');
        }
        if (csvConfirmSection) {
            csvConfirmSection.classList.add('d-none');
            csvConfirmSection.setAttribute('aria-hidden', 'true');
        }

        const alertClass = success ? 'success' : 'danger';
        resultMessageContainer.innerHTML = `
            <div class="alert alert-${alertClass}" role="alert">
                ${message}
            </div>
        `;

        if (errors && errors.length) {
            resultErrorTableBody.innerHTML = '';
            errors.forEach((error, index) => {
                const tr = document.createElement('tr');
                const rowCell = document.createElement('td');
                rowCell.textContent = (error.row !== undefined ? error.row : index + 1);
                const errorCell = document.createElement('td');
                errorCell.textContent = error.error || error.message || error;
                const recordCell = document.createElement('td');
                const recordText = error.record ? JSON.stringify(error.record) : (error.values ? JSON.stringify(error.values) : '');
                recordCell.textContent = recordText;
                tr.appendChild(rowCell);
                tr.appendChild(errorCell);
                tr.appendChild(recordCell);
                resultErrorTableBody.appendChild(tr);
            });
            resultErrorWrapper.classList.remove('d-none');
        } else {
            resultErrorWrapper.classList.add('d-none');
            resultErrorTableBody.innerHTML = '';
        }

        csvConfirmSection.classList.add('d-none');
        csvConfirmSection.setAttribute('aria-hidden', 'true');
        resultSection.classList.remove('d-none');
        resultSection.setAttribute('aria-hidden', 'false');
        if (resultBackButton) {
            resultBackButton.focus();
        }
    }

    function resetToInitialStep() {
        clearMessages();
        resultMessageContainer.innerHTML = '';
        resultErrorWrapper.classList.add('d-none');
        resultErrorTableBody.innerHTML = '';
        state.pendingSinglePayload = null;
        state.pendingCsvMappings = [];
        state.pendingCsvPreview = null;
        state.pendingCsvHeaders = [];
        state.pendingCsvTotalRows = 0;
        state.lastOperation = null;
        state.csvFile = null;
        csvFileInput.value = '';
        state.mode = 'single';
        modeSelect.value = 'single';
        clearConfigTables();
        showSelectStep();
        if (sobjectValueField) {
            sobjectValueField.value = '';
        }
        if (sobjectSelectedDisplay) {
            sobjectSelectedDisplay.textContent = '请选择对象';
            sobjectSelectedDisplay.style.display = 'block';
        }
        state.sobject = '';
        state.selectedOption = null;
        if (sobjectFilterInput) {
            sobjectFilterInput.value = '';
        }
        if (sobjectDropdown) {
            sobjectDropdown.classList.remove('has-value');
        }
        applySobjectFilter('');
    }

    function selectSobject(value, { closeDropdown = false, focusToggle = true, emitChange = true } = {}) {
        const option = sobjectOptions.find((item) => item.value === value);
        state.sobject = option ? option.value : '';
        state.selectedOption = option || null;
        if (sobjectValueField) {
            sobjectValueField.value = state.sobject;
        }
        if (sobjectSelectedDisplay) {
            if (option) {
                sobjectSelectedDisplay.textContent = option.label;
                sobjectSelectedDisplay.style.display = 'none';
            } else {
                sobjectSelectedDisplay.textContent = '请选择对象';
                sobjectSelectedDisplay.style.display = 'block';
            }
        }
        if (sobjectFilterInput) {
            if (option) {
                sobjectFilterInput.value = option.label;
            } else {
                sobjectFilterInput.value = '';
            }
        }
        // Toggle has-value class on wrapper
        if (sobjectDropdown) {
            sobjectDropdown.classList.toggle('has-value', !!option);
        }
        updateSobjectSelectionVisuals(state.sobject);
        if (closeDropdown) {
            closeSobjectDropdown(focusToggle);
        }
        if (emitChange) {
            form.dispatchEvent(new CustomEvent('sobject:change', {
                bubbles: true,
                detail: {
                    value: state.sobject,
                    option,
                },
            }));
        }
    }

    function buildSobjectOptionList() {
        if (!sobjectOptionList) return;
        sobjectOptionList.innerHTML = '';
        sobjectOptions.forEach((option) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'modern-select-option';
            button.dataset.value = option.value;
            button.dataset.searchText = option.searchText;
            button.textContent = option.label;
            button.setAttribute('role', 'option');
            button.addEventListener('click', () => {
                selectSobject(option.value, { closeDropdown: true });
            });
            button.addEventListener('keydown', (event) => handleOptionKeydown(event, button));
            sobjectOptionList.appendChild(button);
        });
        updateSobjectSelectionVisuals(state.sobject);
    }

    function applySobjectFilter(query) {
        state.objectFilter = query || '';
        const normalized = normaliseText(state.objectFilter);
        let firstVisible = null;

        getOptionButtons().forEach((button) => {
            const matches = !normalized || (button.dataset.searchText || '').includes(normalized);
            button.hidden = !matches;
            button.setAttribute('aria-hidden', matches ? 'false' : 'true');
            if (matches && !firstVisible) {
                firstVisible = button;
            }
        });

        if (sobjectNoResults) {
            sobjectNoResults.hidden = Boolean(firstVisible);
        }

        return firstVisible;
    }

    function openSobjectDropdown() {
        if (state.dropdownOpen || !sobjectDropdown) return;
        state.dropdownOpen = true;
        sobjectDropdown.classList.add('open');
        if (sobjectFilterInput) {
            sobjectFilterInput.setAttribute('aria-expanded', 'true');
            // Clear input on open to allow filtering from scratch
            const currentValue = sobjectFilterInput.value;
            if (state.selectedOption && currentValue === state.selectedOption.label) {
                sobjectFilterInput.value = '';
            }
        }
        applySobjectFilter(sobjectFilterInput ? sobjectFilterInput.value : '');
        document.addEventListener('click', handleDocumentClick, true);
    }

    function closeSobjectDropdown(clearInput = false) {
        if (!state.dropdownOpen || !sobjectDropdown) return;
        state.dropdownOpen = false;
        sobjectDropdown.classList.remove('open');
        if (sobjectFilterInput) {
            sobjectFilterInput.setAttribute('aria-expanded', 'false');
            if (clearInput) {
                sobjectFilterInput.value = '';
                state.objectFilter = '';
                applySobjectFilter('');
            } else if (state.selectedOption) {
                // Restore the selected option label when closing without clearing
                sobjectFilterInput.value = state.selectedOption.label;
            }
        }
        document.removeEventListener('click', handleDocumentClick, true);
    }

    function toggleSobjectDropdown() {
        if (state.dropdownOpen) {
            closeSobjectDropdown(false);
        } else {
            openSobjectDropdown();
        }
    }

    function handleDocumentClick(event) {
        if (!sobjectDropdown || sobjectDropdown.contains(event.target)) {
            return;
        }
        closeSobjectDropdown(true);
    }

    function getVisibleOptionButtons() {
        return getOptionButtons().filter((button) => !button.hidden);
    }

    function focusOption(button) {
        if (!button) return;
        button.focus();
    }

    function focusFirstOption() {
        focusOption(getVisibleOptionButtons()[0]);
    }

    function focusLastOption() {
        const visible = getVisibleOptionButtons();
        focusOption(visible[visible.length - 1]);
    }

    function moveFocusFromOption(currentButton, direction) {
        const visible = getVisibleOptionButtons();
        const index = visible.indexOf(currentButton);
        if (index === -1) {
            (direction > 0 ? focusFirstOption() : focusLastOption());
            return;
        }
        let nextIndex = index + direction;
        if (nextIndex < 0) {
            nextIndex = visible.length - 1;
        } else if (nextIndex >= visible.length) {
            nextIndex = 0;
        }
        focusOption(visible[nextIndex]);
    }

    function handleOptionKeydown(event, button) {
        if (!button) return;
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            moveFocusFromOption(button, 1);
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            moveFocusFromOption(button, -1);
        } else if (event.key === 'Home') {
            event.preventDefault();
            focusFirstOption();
        } else if (event.key === 'End') {
            event.preventDefault();
            focusLastOption();
        } else if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            selectSobject(button.dataset.value, { closeDropdown: true });
        } else if (event.key === 'Escape') {
            event.preventDefault();
            closeSobjectDropdown(true);
        } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
            if (sobjectFilterInput) {
                sobjectFilterInput.focus();
                setTimeout(() => {
                    sobjectFilterInput.value = event.key;
                    const first = applySobjectFilter(sobjectFilterInput.value);
                    if (first) {
                        focusOption(first);
                    }
                }, 0);
            }
        }
    }

    function getCsrfToken() {
        const name = 'csrftoken=';
        const decoded = decodeURIComponent(document.cookie || '');
        const parts = decoded.split(';');
        for (let i = 0; i < parts.length; i += 1) {
            let c = parts[i].trim();
            if (c.indexOf(name) === 0) {
                return c.substring(name.length, c.length);
            }
        }
        return '';
    }

    function clearMessages() {
        if (messagesContainer) {
            messagesContainer.innerHTML = '';
        }
    }

    function showMessage(type, text) {
        if (!messagesContainer) return;
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.setAttribute('role', 'alert');
        alert.innerHTML = `
            <div>${text}</div>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        messagesContainer.appendChild(alert);
    }

    function toggleFileUploadVisibility() {
        if (!fileUploadGroup) {
            return;
        }
        const mode = modeSelect.value;
        fileUploadGroup.style.display = mode === 'csv' ? 'block' : 'none';
        if (mode !== 'csv') {
            csvFileInput.value = '';
            state.csvFile = null;
        }
    }

    function resetConfigurationSections() {
        clearConfigTables();
        showSelectStep();
    }

    function parseCsvLine(line) {
        const result = [];
        let current = '';
        let inQuotes = false;
        for (let i = 0; i < line.length; i += 1) {
            const char = line[i];
            if (char === '"') {
                const peek = line[i + 1];
                if (inQuotes && peek === '"') {
                    current += '"';
                    i += 1;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (char === ',' && !inQuotes) {
                result.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        result.push(current.trim());
        return result.map((value) => value.replace(/^\uFEFF/, ''));
    }

    function readCsvHeaders(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onerror = () => reject(new Error('无法读取 CSV 文件。'));
            reader.onload = (event) => {
                const text = event.target.result || '';
                const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
                if (!lines.length) {
                    reject(new Error('CSV 文件为空或缺少表头。'));
                    return;
                }
                const headers = parseCsvLine(lines[0]).filter((value) => value);
                if (!headers.length) {
                    reject(new Error('未能解析 CSV 表头，请确认文件格式。'));
                    return;
                }
                resolve(headers);
            };
            reader.readAsText(file, 'utf-8');
        });
    }

    function buildCsvPreview(file, limit = 5) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onerror = () => reject(new Error('无法读取 CSV 文件。'));
            reader.onload = (event) => {
                const text = event.target.result || '';
                const rawLines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
                if (!rawLines.length) {
                    reject(new Error('CSV 文件为空或缺少表头。'));
                    return;
                }
                const headers = parseCsvLine(rawLines[0]);
                if (!headers.length) {
                    reject(new Error('未能解析 CSV 表头，请确认文件格式。'));
                    return;
                }
                const rows = rawLines.slice(1).map((line) => parseCsvLine(line));
                resolve({
                    headers,
                    rows,
                    totalRows: rows.length,
                    limitedRows: rows.slice(0, limit),
                });
            };
            reader.readAsText(file, 'utf-8');
        });
    }

    function buildFieldOptionText(field) {
        const label = field.label || field.name;
        return field.required ? `${label} (${field.name}) *` : `${label} (${field.name})`;
    }

    function createFieldSelect(fields, cssClass) {
        const select = document.createElement('select');
        select.className = cssClass;
        select.innerHTML = '<option value="">选择字段</option>';
        fields.forEach((field) => {
            const option = document.createElement('option');
            option.value = field.name;
            option.textContent = buildFieldOptionText(field);
            option.dataset.required = field.required ? 'true' : 'false';
            select.appendChild(option);
        });
        return select;
    }

    function addSingleFieldRow(defaultField) {
        const row = document.createElement('tr');
        row.dataset.fieldRow = 'single';

        const actionCell = document.createElement('td');
        actionCell.className = 'text-center align-middle';
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'btn btn-link text-danger p-0';
        removeButton.dataset.removeRow = 'true';
        removeButton.innerHTML = '<i class="fas fa-times" aria-hidden="true"></i><span class="visually-hidden">删除字段</span>';
        actionCell.appendChild(removeButton);

        const fieldCell = document.createElement('td');
        const fieldSelect = createFieldSelect(state.currentFields, 'form-select form-select-sm single-field-select');
        if (defaultField) {
            fieldSelect.value = defaultField;
        }
        fieldCell.appendChild(fieldSelect);

        const valueCell = document.createElement('td');
        const valueInput = document.createElement('input');
        valueInput.type = 'text';
        valueInput.className = 'form-control form-control-sm single-field-value';
        valueInput.placeholder = '输入字段值';
        valueCell.appendChild(valueInput);

        const smartCell = document.createElement('td');
        const smartPlaceholder = document.createElement('span');
        smartPlaceholder.className = 'text-muted small';
        smartPlaceholder.textContent = 'Smart Lookup 待支持';
        smartCell.appendChild(smartPlaceholder);

        row.appendChild(actionCell);
        row.appendChild(fieldCell);
        row.appendChild(valueCell);
        row.appendChild(smartCell);

        singleTableBody.appendChild(row);
    }

    function addCsvMappingRow(defaultField) {
        const row = document.createElement('tr');
        row.dataset.fieldRow = 'csv';

        const actionCell = document.createElement('td');
        actionCell.className = 'text-center align-middle';
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'btn btn-link text-danger p-0';
        removeButton.dataset.removeRow = 'true';
        removeButton.innerHTML = '<i class=\"fas fa-times\" aria-hidden=\"true\"></i><span class=\"visually-hidden\">删除映射</span>';
        actionCell.appendChild(removeButton);

        const fieldCell = document.createElement('td');
        const fieldSelect = createFieldSelect(state.currentFields, 'form-select form-select-sm csv-field-select');
        if (defaultField) {
            fieldSelect.value = defaultField;
        }
        fieldCell.appendChild(fieldSelect);

        const csvCell = document.createElement('td');
        const csvSelect = document.createElement('select');
        csvSelect.className = 'form-select form-select-sm csv-column-select';
        csvSelect.innerHTML = '<option value="">选择 CSV 列</option>';
        state.csvHeaders.forEach((header) => {
            const option = document.createElement('option');
            option.value = header;
            option.textContent = header;
            csvSelect.appendChild(option);
        });
        csvCell.appendChild(csvSelect);

        const smartCell = document.createElement('td');
        const smartPlaceholder = document.createElement('span');
        smartPlaceholder.className = 'text-muted small';
        smartPlaceholder.textContent = 'Smart Lookup 待支持';
        smartCell.appendChild(smartPlaceholder);

        row.appendChild(actionCell);
        row.appendChild(fieldCell);
        row.appendChild(csvCell);
        row.appendChild(smartCell);

        csvTableBody.appendChild(row);
    }

    function initialiseSingleTable() {
        singleTableBody.innerHTML = '';
        const initial = state.requiredFields.length ? state.requiredFields : state.currentFields.slice(0, 3);
        if (!initial.length && state.currentFields.length) {
            initial.push(state.currentFields[0]);
        }
        if (!initial.length) {
            showMessage('danger', '所选对象没有可创建的字段。');
            return false;
        }
        initial.forEach((field) => addSingleFieldRow(field.name));
        return true;
    }

    function initialiseCsvTable() {
        csvTableBody.innerHTML = '';
        const initial = state.requiredFields.length ? state.requiredFields : state.currentFields.slice(0, 3);
        if (!initial.length && state.currentFields.length) {
            initial.push(state.currentFields[0]);
        }
        if (!initial.length) {
            showMessage('danger', '所选对象没有可创建的字段。');
            return false;
        }
        initial.forEach((field) => addCsvMappingRow(field.name));
        return true;
    }

    function fetchFieldsForObject(sobject) {
        if (state.fieldsCache[sobject]) {
            return Promise.resolve(state.fieldsCache[sobject]);
        }
        const url = `${fieldsEndpoint}?sobject=${encodeURIComponent(sobject)}`;
        return fetch(url, {
            credentials: 'same-origin',
        }).then(async (response) => {
            let payload = null;
            try {
                payload = await response.json();
            } catch (err) {
                payload = null;
            }

            if (!response.ok) {
                const message = payload && payload.error ? payload.error : '无法加载字段信息。';
                throw new Error(message);
            }

            return payload || {};
        }).then((data) => {
            const fields = (data.fields || []).filter((field) => field.createable);
            state.fieldsCache[sobject] = fields;
            return fields;
        });
    }

    function handleNextClick(event) {
        event.preventDefault();
        clearMessages();
        clearConfigTables();

        const sobject = state.sobject;
        if (!sobject) {
            showMessage('warning', '请选择 Salesforce 对象。');
            return;
        }

        const mode = modeSelect.value;
        state.sobject = sobject;
        state.mode = mode;

        if (mode === 'csv') {
            if (!csvFileInput.files.length) {
                showMessage('warning', '请选择用于导入的 CSV 文件。');
                return;
            }
            state.csvFile = csvFileInput.files[0];
        }

        nextButton.disabled = true;
        fetchFieldsForObject(sobject)
            .then((fields) => {
                state.currentFields = fields;
                state.requiredFields = fields.filter((field) => field.required);
                if (mode === 'single') {
                    const initialised = initialiseSingleTable();
                    if (initialised) {
                        showSingleStep();
                    } else {
                        showSelectStep();
                    }
                } else {
                    return readCsvHeaders(state.csvFile).then((headers) => {
                        state.csvHeaders = headers;
                        const initialised = initialiseCsvTable();
                        if (initialised) {
                            showCsvStep();
                        } else {
                            showSelectStep();
                        }
                    });
                }
                return null;
            })
            .catch((error) => {
                showMessage('danger', error.message || '加载字段信息时出现问题。');
            })
            .finally(() => {
                nextButton.disabled = false;
            });
    }

    function gatherSinglePayload() {
        const rows = singleTableBody.querySelectorAll('tr');
        const payload = [];
        rows.forEach((row) => {
            const fieldSelect = row.querySelector('.single-field-select');
            const valueInput = row.querySelector('.single-field-value');
            if (!fieldSelect || !valueInput) {
                return;
            }
            const field = fieldSelect.value;
            const value = valueInput.value;
            if (field && value !== '') {
                payload.push({ field, value });
            }
        });
        return payload;
    }

    function handleSingleInsert() {
        clearMessages();
        if (!state.sobject) {
            showMessage('warning', '请先选择 Salesforce 对象并点击下一步。');
            return;
        }
        const fields = gatherSinglePayload();
        if (!fields.length) {
            showMessage('warning', '请至少填写一个字段值。');
            return;
        }
        showSingleConfirmStep(fields);
    }

    function gatherCsvMappings() {
        const rows = csvTableBody.querySelectorAll('tr');
        const mappings = [];
        rows.forEach((row) => {
            const fieldSelect = row.querySelector('.csv-field-select');
            const csvSelect = row.querySelector('.csv-column-select');
            if (!fieldSelect || !csvSelect) {
                return;
            }
            const field = fieldSelect.value;
            const csvField = csvSelect.value;
            if (field && csvField) {
                mappings.push({ field, csvField });
            }
        });
        return mappings;
    }

    function handleCsvInsert() {
        clearMessages();
        if (!state.sobject) {
            showMessage('warning', '请先选择 Salesforce 对象并点击下一步。');
            return;
        }
        if (!state.csvFile) {
            showMessage('warning', '请选择用于导入的 CSV 文件。');
            return;
        }
        const mappings = gatherCsvMappings();
        if (!mappings.length) {
            showMessage('warning', '请至少配置一条字段映射。');
            return;
        }

        csvInsertButton.disabled = true;
        buildCsvPreview(state.csvFile)
            .then(({ headers, rows, totalRows, limitedRows }) => {
                showCsvConfirmStep({
                    headers,
                    rows: limitedRows,
                    totalRows,
                    mappings,
                });
            })
            .catch((error) => {
                showMessage('danger', error.message || '读取 CSV 预览失败。');
            })
            .finally(() => {
                csvInsertButton.disabled = false;
            });
    }

    function executeSingleInsert() {
        if (!state.pendingSinglePayload || !state.pendingSinglePayload.length || !state.sobject) {
            showSelectStep();
            return;
        }

        singleConfirmInsertButton.disabled = true;
        fetch(submitUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                mode: 'single',
                sobject: state.sobject,
                fields: state.pendingSinglePayload,
            }),
        })
            .then((response) => response.json().then((data) => ({ status: response.status, data })))
            .then(({ status, data }) => {
                const success = status === 200 && data.success;
                const message = data.message || (success ? '记录创建成功。' : '插入失败，请稍后重试。');
                const errors = success ? [] : [{ row: 1, error: data.message || '未知错误', record: state.pendingSinglePayload.reduce((acc, item) => ({ ...acc, [item.field]: item.value }), {}) }];
                showResultSection({ success, message, errors });
            })
            .catch((error) => {
                showResultSection({ success: false, message: error.message || '请求过程中出现问题，请稍后重试。', errors: [] });
            })
            .finally(() => {
                singleConfirmInsertButton.disabled = false;
                state.pendingSinglePayload = null;
            });
    }

    function executeCsvInsert() {
        if (!state.sobject || !state.csvFile || !state.pendingCsvMappings || !state.pendingCsvMappings.length) {
            showSelectStep();
            return;
        }

        const formData = new FormData();
        formData.append('mode', 'csv');
        formData.append('sobject', state.sobject);
        formData.append('mapping', JSON.stringify(state.pendingCsvMappings));
        formData.append('csv_file', state.csvFile);

        csvConfirmInsertButton.disabled = true;
        fetch(submitUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin',
            body: formData,
        })
            .then((response) => response.json().then((data) => ({ status: response.status, data })))
            .then(({ status, data }) => {
                const success = status === 200 && data.success;
                let message = data.message || (success ? '文件上传成功。' : '文件上传失败。');
                const errors = Array.isArray(data.errors) ? data.errors.map((error, index) => ({
                    row: error.row || index + 1,
                    error: error.error || error.message || '未知错误',
                    record: error.record || error.values || null,
                })) : [];
                if (data.summary && success) {
                    message += `（总计 ${data.summary.record_count}，成功 ${data.summary.success_count}，失败 ${data.summary.error_count}）`;
                }
                showResultSection({ success, message, errors });
            })
            .catch((error) => {
                showResultSection({ success: false, message: error.message || '上传过程中出现问题，请稍后重试。', errors: [] });
            })
            .finally(() => {
                csvConfirmInsertButton.disabled = false;
                state.pendingCsvMappings = [];
                state.pendingCsvPreview = null;
                state.pendingCsvHeaders = [];
                state.pendingCsvTotalRows = 0;
            });
    }

    function handleDynamicTableActions(event) {
        const trigger = event.target.closest('[data-remove-row="true"]');
        if (trigger) {
            const row = trigger.closest('tr');
            if (row) {
                row.remove();
            }
        }
    }

    // Event bindings
    modeSelect.addEventListener('change', () => {
        toggleFileUploadVisibility();
        resetConfigurationSections();
        clearMessages();
    });

    csvFileInput.addEventListener('change', (event) => {
        const [file] = event.target.files;
        state.csvFile = file || null;
    });

    if (singleBackButton) {
        singleBackButton.addEventListener('click', () => {
            clearMessages();
            showSelectStep();
            nextButton.focus();
        });
    }

    if (csvBackButton) {
        csvBackButton.addEventListener('click', () => {
            clearMessages();
            showSelectStep();
            nextButton.focus();
        });
    }

    if (singleConfirmEditButton) {
        singleConfirmEditButton.addEventListener('click', () => {
            singleConfirmSection.classList.add('d-none');
            showSingleStep();
            singleInsertButton.focus();
        });
    }

    if (singleConfirmInsertButton) {
        singleConfirmInsertButton.addEventListener('click', () => {
            clearMessages();
            executeSingleInsert();
        });
    }

    if (csvConfirmEditButton) {
        csvConfirmEditButton.addEventListener('click', () => {
            csvConfirmSection.classList.add('d-none');
            showCsvStep();
            csvInsertButton.focus();
        });
    }

    if (csvConfirmInsertButton) {
        csvConfirmInsertButton.addEventListener('click', () => {
            clearMessages();
            executeCsvInsert();
        });
    }

    if (resultBackButton) {
        resultBackButton.addEventListener('click', () => {
            resetToInitialStep();
        });
    }

    buildSobjectOptionList();
    selectSobject(sobjectValueField && sobjectValueField.value ? sobjectValueField.value : '', { emitChange: false });
    applySobjectFilter('');

    if (sobjectFilterInput) {
        // Open dropdown when input receives focus
        sobjectFilterInput.addEventListener('focus', (event) => {
            openSobjectDropdown();
        });

        // Close dropdown when input loses focus (with small delay to allow clicks on options)
        sobjectFilterInput.addEventListener('blur', (event) => {
            setTimeout(() => {
                closeSobjectDropdown(false);
            }, 200);
        });

        // Filter options as user types
        sobjectFilterInput.addEventListener('input', (event) => {
            applySobjectFilter(event.target.value);
        });

        // Keyboard navigation
        sobjectFilterInput.addEventListener('keydown', (event) => {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                const first = applySobjectFilter(event.target.value) || getVisibleOptionButtons()[0];
                if (first) {
                    focusOption(first);
                }
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                const visible = getVisibleOptionButtons();
                const last = visible[visible.length - 1];
                if (last) {
                    focusOption(last);
                }
            } else if (event.key === 'Enter') {
                event.preventDefault();
                const first = applySobjectFilter(event.target.value);
                if (first) {
                    selectSobject(first.dataset.value, { closeDropdown: true });
                }
            } else if (event.key === 'Escape') {
                event.preventDefault();
                closeSobjectDropdown(true);
            }
        });
    }

    if (sobjectOptionList) {
        sobjectOptionList.addEventListener('keydown', (event) => {
            if (event.key === 'Tab') {
                closeSobjectDropdown(false);
            }
        });
    }

    nextButton.addEventListener('click', handleNextClick);
    addSingleFieldButton.addEventListener('click', () => addSingleFieldRow());
    addCsvMappingButton.addEventListener('click', () => addCsvMappingRow());
    singleInsertButton.addEventListener('click', handleSingleInsert);
    csvInsertButton.addEventListener('click', handleCsvInsert);

    singleTableBody.addEventListener('click', handleDynamicTableActions);
    csvTableBody.addEventListener('click', handleDynamicTableActions);

    toggleFileUploadVisibility();
    showSelectStep();
})();
