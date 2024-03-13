// set current date as standard date for new expense
document.getElementById("new_date").valueAsDate = new Date();
var expensesTable;

// jquery datatable For table sorting
$(document).ready(function () {
    // Initialize DataTables on your table
    expensesTable = $('#expensesTable').DataTable({
        "columnDefs": [{ 'orderable': false, 'targets': [0, -1] }, { 'searchable': false, 'targets': [0, -1] }], // Disable sorting and searching for the first and last column
        "order": [[2, 'desc']], // Set initial sorting order by date in descending order
        "orderCellsTop": true, // Enable sorting when clicking on the header row,
        "lengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]], // Specify custom labels for the options
        "pageLength": -1 // Set the initial items per page
    });

    // Highlight searchbox if it is in use
    expensesTable.on('search.dt', function () {
        if (expensesTable.search() == '') {
            $('#expensesTable_filter input').removeClass('text-bg-secondary')
        }
        else {
            $('#expensesTable_filter input').addClass('text-bg-secondary')
        }

    });
    // Call the markDuplicates function after initializing the DataTable
    markDuplicates();
});


// Function to mark duplicate entries
function markDuplicates() {
    var rowData = [];
    var duplicateRows = [];

    // Iterate through each row
    expensesTable.rows().every(function () {
        var data = this.data();
        
        // Assuming columns 1, 2, and 3 are used for comparison
        var uniqueKey = data[1] + '-' + data[2] + '-' + data[3];

        // Check if the unique key is already in the rowData array
        if (rowData.indexOf(uniqueKey) !== -1) {
            duplicateRows.push(this.node());
        } else {
            rowData.push(uniqueKey);
        }
    });

    // Add a class to mark duplicate rows
    $(duplicateRows).addClass('table-danger');

    // Update the count of duplicates in the span. shown in info list 
    var noDuplicatesSpan = $('#noDuplicates');
    var listItemDuplicates = $('#listItemDuplicates')
    var duplicatesCount = duplicateRows.length;
    
    noDuplicatesSpan.text(duplicatesCount);

    // Apply styling if there are duplicates
    if (duplicatesCount > 0) {
        listItemDuplicates.addClass('fw-bold text-danger');
    }
}

// Highlight modal input fields that are changed
$(document).ready(function () {
    // Function to highlight modified fields
    function highlightModifiedFields() {
        // Store original values
        var originalValues = {};

        // Capture original values when the modal is opened
        $('#expenseModifyModal').on('show.bs.modal', function () {
            originalValues.modal_description = $('#modal_description').val();
            originalValues.modal_date = $('#modal_date').val();
            originalValues.modal_amount = $('#modal_amount').val();
            originalValues.modal_org_currency = $('#modal_org_currency').val();
            originalValues.modal_category = $('#modal_category').val();
        });

        // Highlight modified input fields on change
        $('input, select').on('change', function () {
            var fieldId = $(this).attr('id');
            var originalValue = originalValues[fieldId];
            var currentValue = $(this).val();

            if (originalValue !== currentValue) {
                $(this).addClass('bg-warning-subtle');
            } else {
                $(this).removeClass('bg-warning-subtle');
            }
        });

        // Reset highlighting when the modal is hidden
        $('#expenseModifyModal').on('hide.bs.modal', function () {
            $('input, select').removeClass('bg-warning-subtle');
        });

    };

    // Call the function every time the modal is opened
    $('#expenseModifyModal').on('show.bs.modal', function () {
        highlightModifiedFields();
    });
});


function formatDate(date) {
    var year = date.getFullYear();
    var month = String(date.getMonth() + 1).padStart(2, '0');
    var day = String(date.getDate()).padStart(2, '0');
    return year + '-' + month + '-' + day;
}

function populateModal(inData, mode) {

    var resultObject = {};
    
    if (mode == "single")
    {
        // Access the specific row data
        resultObject = expensesData[inData];
        // To show number of modified elements in modal
        document.getElementById('itemCount').textContent = 1;
    }
    else if (mode == "multiple")
    {
        // To show number of modified elements in modal
        document.getElementById('itemCount').textContent = inData.length;

        // Check array for common values
        const resultMap = {};
        var placeholder = '';

        inData.forEach(item => {
            // Iterate through each property in the item
            for (const key in item) {
                // If the key already exists in the result map, check the value
                if (resultMap.hasOwnProperty(key)) {
                    // If the value is different, set it to the placeholder
                    if (resultMap[key] !== item[key]) {
                        resultMap[key] = placeholder;
                    }
                } else {
                    // If the key doesn't exist, add it to the result map
                    resultMap[key] = item[key];
                }
            }
        });

        // Convert the result map to an array
        for (const key in resultMap) {
            resultObject[key] = resultMap[key];
        }
    }

    // Populate modal fields
    document.getElementById("modal_description").value = resultObject.description;
    if (resultObject.date != placeholder)
    {
        document.getElementById("modal_date").value = formatDate(new Date(resultObject.date));
    } 
    if (resultObject.amount != placeholder)
    {
        document.getElementById("modal_amount").value = resultObject.amount;
    }
    document.getElementById("modal_org_currency").value = resultObject.org_currency;

    var modifyButtonIdValue;
    var removeButtonIdValue;

    if (mode == "single")
    {
        modifyButtonIdValue = "modify|" + resultObject.expense_id
        removeButtonIdValue = "remove|" + resultObject.expense_id
    }
    else if (mode == "multiple")
    {
        const expenseIdsString = inData.map(item => item.expense_id).join(',');
        modifyButtonIdValue = "modify|" + expenseIdsString
        removeButtonIdValue = "remove|" + expenseIdsString
    }
    
    document.getElementById("modalModifyButton").value = modifyButtonIdValue
    document.getElementById("modalDeleteButton").value = removeButtonIdValue



    // Check if the category is not in dropdownlist yet
    var modalCategoryDropdown = document.getElementById("modal_category");
    var existingOption = Array.from(modalCategoryDropdown.options).find(option => option.value === resultObject.category);

    // Add the new option to the dropdown
    if (!existingOption) {
        // Create a new option element
        var newOption = document.createElement("option");

        // Set the value and text content for the new option
        newOption.value = resultObject.category;
        newOption.text = resultObject.category;

        // Set the color of the new option to red
        newOption.style.color = "red";

        // Append the new option to the dropdown
        modalCategoryDropdown.add(newOption);
    }

    modalCategoryDropdown.value = resultObject.category;

    // Show the modal
    $('#expenseModifyModal').modal('show');
}

function checkUncheck()
{
    var allCheckboxes = document.querySelectorAll('#expensesTable tbody input[type="checkbox"]')
    var numberChecked = document.querySelectorAll('#expensesTable tbody input[type="checkbox"]:checked').length

    var newBool = true;
    if (numberChecked > 0){
        newBool = false;
    }

    // Iterate through each checkbox and set it to checked
    allCheckboxes.forEach(function(checkbox) {
        checkbox.checked = newBool;
    });
}


function modifySelected() {
    // Get all selected checkboxes
    var selectedCheckboxes = document.querySelectorAll('#expensesTable tbody input[type="checkbox"]:checked')

    if (selectedCheckboxes.length > 0) {
        var selectedRowsData = [];
        var rowIndex;

        selectedCheckboxes.forEach(function (checkbox) 
        {
            rowIndex = parseInt(checkbox.id); //is defined starting with 0
            var row = expensesData[rowIndex];
            selectedRowsData.push(row);
        });

        if (selectedRowsData.length == 1)
        {
            populateModal(rowIndex, "single")
        }
        else
        {
            populateModal(selectedRowsData, "multiple")
        }
    }
    else
    {
        alert("Select items in list below first")
    }
}




