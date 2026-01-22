const API = "http://127.0.0.1:5000";

function login(){
    fetch(API + "/login", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            username: username.value,
            password: password.value
        })
    })
    .then(res => res.json())
    .then(data => {
        if(data.role){
            localStorage.setItem("role", data.role);
            window.location="dashboard.html";
        } else {
            msg.innerText = "Invalid Credentials";
        }
    });
}

function register(){
    fetch(API + "/register", {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify({
            username: username.value,
            password: password.value,
            role: role.value
        })
    })
    .then(res => res.json())
    .then(data => msg.innerText = data.message);
}