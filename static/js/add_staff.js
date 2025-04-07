function validateFname() {
    const username = document.getElementById('name-f').value;
    const usernameError = document.getElementById('fname-error');
    const regex = /^[a-zA-Z]+$/;

    if (username && !regex.test(username)) {
        usernameError.style.display = 'inline';
    } else {
        usernameError.style.display = 'none';
    }
}
function validateLname() {
    const username = document.getElementById('name-l').value;
    const usernameError = document.getElementById('lname-error');
    const regex = /^[a-zA-Z]+$/;

    if (username && !regex.test(username)) {
        usernameError.style.display = 'inline';
    } else {
        usernameError.style.display = 'none';
    }
}

function validateEmail() {
    const email = document.getElementById('email').value;
    const emailError = document.getElementById('email-error');
    const regex = /^[a-z0-9._%+-]+@gmail\.com$/;

    if (email && !regex.test(email)) {
        emailError.style.display = 'inline';
    } else {
        emailError.style.display = 'none';
    }
}

function validateState() {
    const username = document.getElementById('State').value;
    const usernameError = document.getElementById('state-error');
    // Regex to ensure the first letter is uppercase and the rest are lowercase
    const regex = /^[A-Z][a-z]*$/;

    if (username && !regex.test(username)) {
        usernameError.style.display = 'inline';
    } else {
        usernameError.style.display = 'none';
    }
}
function validateAddress() {
    const username = document.getElementById('address-2').value;
    const usernameError = document.getElementById('add-error');
    // Regex to ensure the first letter is uppercase and the rest are lowercase
    const regex = /^[A-Z][a-z]*$/;

    if (username && !regex.test(username)) {
        usernameError.style.display = 'inline';
    } else {
        usernameError.style.display = 'none';
    }
}

function validateZip() {
    const zip = document.getElementById('zip').value;
    const zipError = document.getElementById('zip-error');
    // Regex to ensure exactly 6 digits
    const regex = /^[1-9]\d{5}$/;

    if (zip && !regex.test(zip)) {
        zipError.style.display = 'inline';
    } else {
        zipError.style.display = 'none';
    }
}

function validatePhone() {
    const phone = document.getElementById('tel').value;
    const phoneError = document.getElementById('ph-error');
    const regex = /^[6-9]\d{9}$/;

    if (phone && !regex.test(phone)) {
        phoneError.style.display = 'inline';
    } else {
        phoneError.style.display = 'none';
    }
}

function validateForm(event) {
    // Run all validation functions
    validateFname();
    validateLname();
    validateEmail();
    validateState();
    validateAddress();
    validateZip();
    validatePhone();

    // Check if any error is visible
    const errors = document.querySelectorAll('span[id$="-error"]');
    let hasError = false;

    errors.forEach(function(errorElement) {
        if (errorElement.style.display === 'inline') {
            hasError = true;
        }
    });

    if (hasError) {
        alert('Please correct the errors in the form.');
        event.preventDefault(); // Prevent form submission
    }
}
