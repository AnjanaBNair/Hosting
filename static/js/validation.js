function validateUsername() {
    const username = document.getElementById('username').value;
    const usernameError = document.getElementById('username-error');
    const regex = /^[a-zA-Z_]+$/;

    if (username && !regex.test(username)) {
        usernameError.style.display = 'inline';
    } else {
        usernameError.style.display = 'none';
    }
}
function validateEmail() {
    const email = document.getElementById('email').value;
    const emailError = document.getElementById('email-error');
    const regex = /^[^\s][a-z0-9._%+-]+@gmail\.com$/;

    if (email && !regex.test(email)) {
        emailError.style.display = 'inline';
    } else {
        emailError.style.display = 'none';
    }
}

function validatePassword() {
    const password = document.getElementById('password1').value;
    const passwordError = document.getElementById('password-error');
    if (password && password.length <6) {
        passwordError.style.display = 'inline';
    } else {
        passwordError.style.display = 'none';
    }
}
function validateConfirmPassword() {
    const password1 = document.getElementById('password1').value;
    const password2 = document.getElementById('password2').value;
    const confirmPasswordError = document.getElementById('confirm-password-error');

    if (password2 && password1 !== password2) {
        confirmPasswordError.style.display = 'inline';
    } else {
        confirmPasswordError.style.display = 'none';
    }
}
function validateForm() {
    const isEmailValid = validateEmail();
    const isUsernameValid = validateUsername();
    const isPasswordValid = validatePassword();

    if (!isEmailValid || !isUsernameValid || !isPasswordValid) {
        alert('Please fill the form correctly.');
        return false;
    }
    return true;
}
function validateForm(event) {
    const isEmailValid = validateEmail();
    const isUsernameValid = validateUsername();
    const isPasswordValid = validatePassword();
    const isConfirmPasswordValid = validateConfirmPassword();

    if (!isEmailValid || !isUsernameValid || !isPasswordValid || !isConfirmPasswordValid) {
        alert('Please fill the form correctly.');
        event.preventDefault();
        return false;
    }
    return true;
}
