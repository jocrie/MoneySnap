$(document).ready(function() {
    function checkFile() {
        var fileInput = document.getElementById('fileInput');
        var fileName = fileInput.value;
        var acceptedFormats = ['.xlsx', '.xls', '.csv'];
    
        var isValidFormat = false;
        for (var i = 0; i < acceptedFormats.length; i++) {
            if (fileName.endsWith(acceptedFormats[i])) {
                isValidFormat = true;
                break;
            }
        }
    
        if (!isValidFormat) {
            alert('Invalid file format. Please use .xlsx, .xls or .csv files.');
            // Optionally, you can clear the file input to prevent submission
            fileInput.value = '';
        }
    }

    var table = $('#importTable').DataTable({
        searching: false,  // Disable the search box
        "lengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]], // Specify custom labels for the options
        "pageLength": -1 // Set the initial items per page
    });

    // Declare columnMapping outside the event handler
    var columnMapping = {};
    var jsonData = [];
    var tableHeaders = [];

    // Function to open the column mapping modal
    function openColumnMappingModal() {
        $('#columnMappingModal').modal('show');
    }

    // Function to dynamically generate column mapping rows
    function generateColumnMappingRows() {
        var columnMappingBody = document.getElementById('columnMappingBody');
        columnMappingBody.innerHTML = '';

        tableHeaders = Array.from(document.getElementById('importTable').querySelectorAll('thead th')).map(th => th.textContent);

        tableHeaders.forEach(function(tableHeader) {
            var row = document.createElement('tr');

            // Table header column
            var tableHeaderCell = document.createElement('td');
            tableHeaderCell.textContent = tableHeader;
            row.appendChild(tableHeaderCell);

            // Dropdown column for choosing column header
            var chooseHeaderCell = document.createElement('td');
            var selectField = document.createElement('select');
            selectField.name = 'columnMapping';
            selectField.className = 'form-control';

            // Add an "Unmapped" option
            var unmappedOption = document.createElement('option');
            unmappedOption.value = '';
            unmappedOption.text = '*Unmapped*';

            // Description, date and amount are mandatory
            if (['Currency (optional)', 'Category (optional)'].includes(tableHeader))
            {
                selectField.add(unmappedOption);
            }

            // Add options for column headers from the input file
            var columnHeaderOptions = jsonData[0];
            columnHeaderOptions.forEach(function(columnHeaderOption) {
                var option = document.createElement('option');
                option.value = columnHeaderOption;
                option.text = columnHeaderOption;
                selectField.add(option);
            });

            chooseHeaderCell.appendChild(selectField);
            row.appendChild(chooseHeaderCell);

            columnMappingBody.appendChild(row);
        });
    }

    // Function to apply column mapping and close the modal
    function applyColumnMapping() {
        var selectFields = document.getElementsByName('columnMapping');

        // Reset columnMapping to avoid using previous mappings
        columnMapping = {};

        // Retrieve the selected column headers
        Array.from(selectFields).forEach(function(selectField) {
            var tableHeader = selectField.closest('tr').querySelector('td:first-child').textContent;
            var columnHeader = selectField.value;

            columnMapping[tableHeader] = columnHeader;
        });

        // Perform actions with the column mapping (e.g., update DataTable, etc.)

        // Close the modal
        $('#columnMappingModal').modal('hide');
    }

    $('#importButton').on('click', function() {
        checkFile();
        var input = document.getElementById('fileInput');

        if (input.files.length > 0) {
            var file = input.files[0];
            var reader = new FileReader();

            reader.onload = function(e) {
                var data = new Uint8Array(e.target.result);
                var workbook = XLSX.read(data);

                // Assume the first sheet is the one you want
                var sheetName = workbook.SheetNames[0];
                var sheet = workbook.Sheets[sheetName];

                // Convert sheet data to JSON
                jsonData = XLSX.utils.sheet_to_json(sheet, {
                    header: 1,
                    raw: false,
                    cellText: true,
                    defval: '',
                    cellDates: false,
                    CodePage: 65001, // UTF-8 encoding
                    });

                // Specify the maximum row number you want to include
                var maxRowNumber = parseInt(document.getElementById('lastRowNo').value, 10);
                var skip = parseInt(document.getElementById('headerRowNo').value, 10) - 1; 

                if (maxRowNumber == 0)
                {
                    // Skip depending on where header row is. Filter out empty rows.
                    jsonData = jsonData.slice(skip).filter(row => row.filter(cell => cell !== undefined && cell !== null && cell !== '').length > 0);
                }
                else
                {
                    jsonData = jsonData.slice(skip, maxRowNumber).filter(row => row.filter(cell => cell !== undefined && cell !== null && cell !== '').length > 0);
                }

                // Populate and open the column mapping modal
                generateColumnMappingRows();
                openColumnMappingModal();

                
            };

            // Read the file as an ArrayBuffer
            reader.readAsArrayBuffer(file);

        }
    });

    $('#applyMappingButton').on('click', function() {
        // Apply column mapping and close modal
        applyColumnMapping();

        // Map columns based on the user-selected mapping
        jsonData = jsonData.map(row => {
            var mappedRow = [];
        
            Object.keys(columnMapping).forEach(mappedHeader => {
                var originalHeader = columnMapping[mappedHeader];
                var columnIndex = jsonData[0].indexOf(originalHeader);
        
                if (columnIndex !== -1) {
                    mappedRow.push(row[columnIndex]);
                    }
                else {
                // Set an empty string if there is no mapping
                mappedRow.push('');
                }
            });
        
            return mappedRow;
        });

        // Clear existing table data
        table.clear().draw();

        // Add new data to DataTable. skip first row(header)
        table.rows.add(jsonData.slice(1)).draw();

        // Activate button to save to list
        if (jsonData.slice(1).length > 0)
        {
            document.getElementById("copyToExpenseListButton").disabled = false;
            document.getElementById("copyToExpenseListButton").classList.replace('btn-secondary', 'btn-success')
            document.getElementById("org_currency").disabled = false;
        }
        else
        {
            document.getElementById("copyToExpenseListButton").disabled = true;
            document.getElementById("copyToExpenseListButton").classList.replace('btn-success', 'btn-secondary')
            document.getElementById("org_currency").disabled = true;
        }

        // Currency mapped
        if (jsonData[0][3] !== '')
        {
            document.getElementById("takeOverFromTableOption").disabled = false;
            document.getElementById("org_currency").selectedIndex = 0;
        }
        else
        {
            document.getElementById("takeOverFromTableOption").disabled = true;
            document.getElementById("org_currency").selectedIndex = 1;

        }

    });

    $('#copyToExpenseListButton').on('click', function() {
        // Create a hidden input field for the table data
        var tableDataInput = $('<input>')
            .attr('type', 'hidden')
            .attr('name', 'tableData')
            .val(JSON.stringify(table.rows().data().toArray()));

        // Append the hidden input to the form
        $('#expenseListForm').append(tableDataInput);

        // Submit the form
        $('#expenseListForm').submit();
    });


});