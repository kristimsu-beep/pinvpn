let authMode = "register";


/* ============================================================
   SERVER STATUS
============================================================ */

async function checkServer() {

    const statusElement =
        document.getElementById(
            "navStatus"
        );

    const cardStatus =
        document.getElementById(
            "cardStatus"
        );

    const databaseStatus =
        document.getElementById(
            "databaseStatus"
        );


    try {

        const response =
            await fetch("/health");


        const data =
            await response.json();


        if (
            data.status === "ok"
        ) {

            statusElement.innerHTML =
                `
                <span class="status-dot"></span>
                <span>Server online</span>
                `;


            cardStatus.textContent =
                "● Online";


            if (
                data.database ===
                "connected"
            ) {

                databaseStatus.textContent =
                    "Connected";

            } else {

                databaseStatus.textContent =
                    "Not connected";

            }

        }

    } catch (error) {

        statusElement.innerHTML =
            `
            <span>● Offline</span>
            `;


        cardStatus.textContent =
            "● Offline";


        databaseStatus.textContent =
            "Unavailable";

    }

}


/* ============================================================
   AUTH MODAL
============================================================ */

function openAuth(mode) {

    authMode = mode;


    const modal =
        document.getElementById(
            "authModal"
        );


    const title =
        document.getElementById(
            "authTitle"
        );


    const description =
        document.getElementById(
            "authDescription"
        );


    const switchButton =
        document.getElementById(
            "switchAuth"
        );


    const message =
        document.getElementById(
            "authMessage"
        );


    message.textContent = "";


    if (
        mode === "register"
    ) {

        title.textContent =
            "Create account";


        description.textContent =
            "Create your PinVPN account.";


        switchButton.textContent =
            "Already have an account? Sign in";

    } else {

        title.textContent =
            "Welcome back";


        description.textContent =
            "Sign in to your PinVPN account.";


        switchButton.textContent =
            "Don't have an account? Create one";

    }


    modal.classList.remove(
        "hidden"
    );


    document
        .getElementById("username")
        .focus();

}


function closeAuth() {

    document
        .getElementById("authModal")
        .classList.add("hidden");

}


function switchAuthMode() {

    if (
        authMode === "register"
    ) {

        openAuth("login");

    } else {

        openAuth("register");

    }

}


/* ============================================================
   AUTH REQUEST
============================================================ */

async function submitAuth(event) {

    event.preventDefault();


    const username =
        document
            .getElementById("username")
            .value
            .trim();


    const password =
        document
            .getElementById("password")
            .value;


    const message =
        document.getElementById(
            "authMessage"
        );


    message.textContent =
        "Please wait...";


    const endpoint =
        authMode === "register"
            ? "/api/auth/register"
            : "/api/auth/login";


    const formData =
        new FormData();


    formData.append(
        "username",
        username
    );


    formData.append(
        "password",
        password
    );


    try {

        const response =
            await fetch(
                endpoint,
                {
                    method: "POST",
                    body: formData,
                    credentials: "include"
                }
            );


        const data =
            await response.json();


        if (
            !response.ok
        ) {

            message.textContent =
                data.detail ||
                "Something went wrong.";

            return;

        }


        message.style.color =
            "#42e695";


        message.textContent =
            data.message ||
            "Success!";


        if (
            authMode === "register"
        ) {

            setTimeout(
                () => {

                    openAuth(
                        "login"
                    );

                },
                800
            );

        } else {

            setTimeout(
                () => {

                    closeAuth();

                    showDashboard(
                        data.user
                    );

                },
                500
            );

        }


    } catch (error) {

        console.error(error);


        message.style.color =
            "#ff8794";


        message.textContent =
            "Unable to connect to server.";

    }

}


/* ============================================================
   DASHBOARD PLACEHOLDER
============================================================ */

function showDashboard(user) {

    alert(
        `Welcome to PinVPN, ${user.username}!`
    );

}


/* ============================================================
   START
============================================================ */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        checkServer();

    }
);
