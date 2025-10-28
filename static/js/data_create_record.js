(function() {
    const form = document.getElementById('create-record-form');
    if (!form) {
        return;
    }

    const messagesContainer = document.getElementById('insert-messages');
    const sobjectSelect = document.getElementById('sobject-select');
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

    const state = {
        sobject: '',
        mode: 'single',
        fieldsCache: {},
        currentFields: [],
        requiredFields: [],
        csvHeaders: [],
        csvFile: null,
    };

    const fieldsEndpoint = window.DATA_FIELDS_ENDPOINT;
    const submitUrl = window.CREATE_RECORD_POST_URL;

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
        const mode = modeSelect.value;
        fileUploadGroup.style.display = mode === 'csv' ? 'block' : 'none';
        if (mode !== 'csv') {
            csvFileInput.value = '';
            state.csvFile = null;
        }
    }

    function resetConfigurationSections() {
        singleConfigSection.classList.add('d-none');
        csvConfigSection.classList.add('d-none');
        singleTableBody.innerHTML = '';
        csvTableBody.innerHTML = '';
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

        row.appendChild(fieldCell);
        row.appendChild(valueCell);
        row.appendChild(smartCell);

        singleTableBody.appendChild(row);
    }

    function addCsvMappingRow(defaultField) {
        const row = document.createElement('tr');
        row.dataset.fieldRow = 'csv';

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
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-link btn-sm text-danger ms-1 p-0 align-baseline';
        removeBtn.dataset.removeRow = 'true';
        removeBtn.textContent = '移除';
        csvCell.appendChild(csvSelect);
        csvCell.appendChild(removeBtn);

        const smartCell = document.createElement('td');
        const smartPlaceholder = document.createElement('span');
        smartPlaceholder.className = 'text-muted small';
        smartPlaceholder.textContent = 'Smart Lookup 待支持';
        smartCell.appendChild(smartPlaceholder);

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
            return;
        }
        initial.forEach((field) => addSingleFieldRow(field.name));
        singleConfigSection.classList.remove('d-none');
        csvConfigSection.classList.add('d-none');
    }

    function initialiseCsvTable() {
        csvTableBody.innerHTML = '';
        const initial = state.requiredFields.length ? state.requiredFields : state.currentFields.slice(0, 3);
        if (!initial.length && state.currentFields.length) {
            initial.push(state.currentFields[0]);
        }
        if (!initial.length) {
            showMessage('danger', '所选对象没有可创建的字段。');
            return;
        }
        initial.forEach((field) => addCsvMappingRow(field.name));
        csvConfigSection.classList.remove('d-none');
        singleConfigSection.classList.add('d-none');
    }

    function fetchFieldsForObject(sobject) {
        if (state.fieldsCache[sobject]) {
            return Promise.resolve(state.fieldsCache[sobject]);
        }
        const url = `${fieldsEndpoint}?sobject=${encodeURIComponent(sobject)}`;
        return fetch(url, {
            credentials: 'same-origin',
        }).then((response) => {
            if (!response.ok) {
                throw new Error('无法加载字段信息。');
            }
            return response.json();
        }).then((data) => {
            const fields = (data.fields || []).filter((field) => field.createable);
            state.fieldsCache[sobject] = fields;
            return fields;
        });
    }

    function handleNextClick(event) {
        event.preventDefault();
        clearMessages();
        resetConfigurationSections();

        const sobject = sobjectSelect.value;
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
                    initialiseSingleTable();
                } else {
                    return readCsvHeaders(state.csvFile).then((headers) => {
                        state.csvHeaders = headers;
                        initialiseCsvTable();
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

        singleInsertButton.disabled = true;
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
                fields,
            }),
        })
            .then((response) => response.json().then((data) => ({ status: response.status, data })))
            .then(({ status, data }) => {
                const type = status === 200 && data.success ? 'success' : 'danger';
                showMessage(type, data.message || '完成请求。');
            })
            .catch(() => {
                showMessage('danger', '请求过程中出现问题，请稍后重试。');
            })
            .finally(() => {
                singleInsertButton.disabled = false;
            });
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

        const formData = new FormData();
        formData.append('mode', 'csv');
        formData.append('sobject', state.sobject);
        formData.append('mapping', JSON.stringify(mappings));
        formData.append('csv_file', state.csvFile);

        csvInsertButton.disabled = true;
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
                const type = status === 200 && data.success ? 'success' : 'danger';
                let message = data.message || '完成请求。';
                if (data.summary) {
                    message += `（总计 ${data.summary.record_count}，成功 ${data.summary.success_count}，失败 ${data.summary.error_count}）`;
                }
                showMessage(type, message);
            })
            .catch(() => {
                showMessage('danger', '上传过程中出现问题，请稍后重试。');
            })
            .finally(() => {
                csvInsertButton.disabled = false;
            });
    }

    function handleDynamicTableActions(event) {
        const target = event.target;
        if (target.dataset.removeRow === 'true') {
            const row = target.closest('tr');
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

    nextButton.addEventListener('click', handleNextClick);
    addSingleFieldButton.addEventListener('click', () => addSingleFieldRow());
    addCsvMappingButton.addEventListener('click', () => addCsvMappingRow());
    singleInsertButton.addEventListener('click', handleSingleInsert);
    csvInsertButton.addEventListener('click', handleCsvInsert);

    singleTableBody.addEventListener('click', handleDynamicTableActions);
    csvTableBody.addEventListener('click', handleDynamicTableActions);

    toggleFileUploadVisibility();
})();
