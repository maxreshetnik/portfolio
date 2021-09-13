var orderModal = document.getElementById('orderModal')
orderModal.addEventListener('show.bs.modal', function (event) {
    // Button that triggered the modal
    var button = event.relatedTarget
    // Extract info from data-bs-* attributes
    var orderNumber = button.getAttribute('data-bs-number')
    //
    // Update the modal's content.
    var modalTitle = orderModal.querySelector('.modal-title')
    var modalBody = orderModal.querySelector('.modal-body')
    var modalFooterForm = orderModal.querySelector('.modal-footer form')
    var modalFooterInput = orderModal.querySelector('.modal-footer input')

    modalTitle.textContent = 'Order No. ' + orderNumber
    modalBody.textContent = 'Are you sure you want to ' + button.textContent + 'your order?'
    modalFooterForm.action = orderNumber + '/'
})