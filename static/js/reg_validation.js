// reg_validation.js
function validateForm() {
    let isValid = true;

    const firstname = document.getElementById('firstname').value;
    const lastname = document.getElementById('lastname').value;
    const email = document.getElementById('email').value;
    const mob = document.getElementById('mob').value;
    const password1 = document.getElementById('password1').value;
    const password2 = document.getElementById('password2').value;

    if (firstname === "") {
        document.getElementById('error_firstname').innerText = "First name is required";
        document.getElementById('error_firstname').style.display = "block";
        isValid = false;
    } else {
        document.getElementById('error_firstname').style.display = "none";
    }

    if (lastname === "") {
        document.getElementById('error_lastname').innerText = "Last name is required";
        document.getElementById('error_lastname').style.display = "block";
        isValid = false;
    } else {
        document.getElementById('error_lastname').style.display = "none";
    }

    if (email === "") {
        document.getElementById('error_email').innerText = "Email is required";
        document.getElementById('error_email').style.display = "block";
        isValid = false;
    } else if (!validateEmail(email)) {
        document.getElementById('error_email').innerText = "Invalid email format";
        document.getElementById('error_email').style.display = "block";
        isValid = false;
    } else {
        document.getElementById('error_email').style.display = "none";
    }

    if (mob === "") {
        document.getElementById('error_mob').innerText = "Mobile number is required";
        document.getElementById('error_mob').style.display = "block";
        isValid = false;
    } else {
        document.getElementById('error_mob').style.display = "none";
    }

    if (password1 === "") {
        document.getElementById('error_password1').innerText = "Password is required";
        document.getElementById('error_password1').style.display = "block";
        isValid = false;
    } else {
        document.getElementById('error_password1').style.display = "none";
    }

    if (password2 === "") {
        document.getElementById('error_password2').innerText = "Password confirmation is required";
        document.getElementById('error_password2').style.display = "block";
        isValid = false;
    } else if (password1 !== password2) {
        document.getElementById('error_password2').innerText = "Passwords do not match";
        document.getElementById('error_password2').style.display = "block";
        isValid = false;
    } else {
        document.getElementById('error_password2').style.display = "none";
    }

    return isValid;
}

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

function onSignIn(googleUser) {
    const profile = googleUser.getBasicProfile();
    document.getElementById('firstname').value = profile.getGivenName();
    document.getElementById('lastname').value = profile.getFamilyName();
    document.getElementById('email').value = profile.getEmail();
}
