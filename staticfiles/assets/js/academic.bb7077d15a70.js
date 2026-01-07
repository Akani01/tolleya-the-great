// static/js/academic.js
document.addEventListener('DOMContentLoaded', function() {
    // Document Upload
    const docForm = document.getElementById('document-upload-form');
    if (docForm) {
        docForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            fetch('/upload-document/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            })
            .then(response => response