
function first_name() {
    const username = document.getElementById('first_name').value;
    const usernameError = document.getElementById('first_name-error');
    const regex = /^[a-zA-Z]+$/;

    if (username && !regex.test(username)) {
        usernameError.style.display = 'inline';
    } else {
        usernameError.style.display = 'none';
    }
}
function last_name() {
    const username = document.getElementById('last_name').value;
    const usernameError = document.getElementById('last_name-error');
    const regex = /^[a-zA-Z]+$/;

    if (username && !regex.test(username)) {
        usernameError.style.display = 'inline';
    } else {
        usernameError.style.display = 'none';
    }
}
function country() {
    const username = document.getElementById('country').value;
    const usernameError = document.getElementById('country-error');
    const regex = /^[a-zA-Z]+$/;

    if (username && !regex.test(username)) {
        usernameError.style.display = 'inline';
    } else {
        usernameError.style.display = 'none';
    }
}

function phonenumber() {
    const username = document.getElementById('phone_number').value;
    const usernameError = document.getElementById('phone_number-error');
    const regex =/^[9|8|7|6]\d{9}$/;

    if (username && !regex.test(username)) {
        usernameError.style.display = 'inline';
    } else {
        usernameError.style.display = 'none';
    }
}

function validate_user_profile_Form(){
    const isfirstname = first_name();
    const islastname = last_name();
    const iscountry = country();
    const isphonenumber = phonenumber();

    if (!isfirstname || !islastname || !iscountry || !isphonenumber) {
        alert('Please fill the form correctly.');
        event.preventDefault();
        return false;
    }
    return true;
}


function firstname() {
    const firstName = document.getElementById('first_name').value.trim();
    const firstNameError = document.getElementById('first_name-error');
    const regex = /^[a-zA-Z]+$/;

    if (!firstName || !regex.test(firstName)) {
        console.log("Invalid first name");
        firstNameError.style.display = 'block';
        return false;
    } else {
        firstNameError.style.display = 'none';
        return true;
    }

}

function lastname() {
    const lastName = document.getElementById('last_name').value;
    const lastNameError = document.getElementById('last_name-error');
    const regex = /^[a-zA-Z]+$/;

    if (lastName && !regex.test(lastName)) {
        lastNameError.style.display = 'block';
        return false;
    } else {
        lastNameError.style.display = 'none';
        return true;
    }
}

function phone_number() {
    const phoneNumber = document.getElementById('phone_number').value;
    const phoneNumberError = document.getElementById('phone_number-error');
    const regex = /^[6-9]\d{9}$/;

    if (phoneNumber && !regex.test(phoneNumber)) {
        phoneNumberError.style.display = 'block';
        return false;
    } else {
        phoneNumberError.style.display = 'none';
        return true;
    }
}

function validate_user_profile_edit_Form(event) {
    const isFirstNameValid = firstname();
    const isLastNameValid = lastname();
    const isPhoneNumberValid = phone_number();

    if (!isFirstNameValid || !isLastNameValid || !isPhoneNumberValid) {
        alert('Please fill the form correctly.');
        event.preventDefault();
        return false;
    }
    return true;
}