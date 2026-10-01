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

    const page = document.querySelector(".page");

    if (page) {
        page.classList.add("dashboard-hidden");
    }

    const dashboard =
        document.getElementById("dashboard");

    if (dashboard) {
        dashboard.classList.remove("hidden");
    }

    const username =
        user.username || "User";

    const usernameElement =
        document.getElementById("dashboardUsername");

    const accountUsername =
        document.getElementById("accountUsername");

    if (usernameElement) {
        usernameElement.textContent = username;
    }

    if (accountUsername) {
        accountUsername.textContent = username;
    }

    const avatar =
        document.getElementById("dashboardAvatar");

    if (avatar) {
        avatar.textContent =
            username.charAt(0).toUpperCase();
    }

    window.scrollTo(0, 0);

   loadDevices();
}


async function logout() {

    try {

        await fetch("/api/auth/logout", {
            method: "POST",
            credentials: "include"
        });

    } catch (error) {

        console.error(
            "Logout error:",
            error
        );

    }

    window.location.reload();
}


let vpnConnected = false;


function toggleVPN() {

    const indicator =
        document.getElementById(
            "vpnStatusIndicator"
        );

    const statusText =
        document.getElementById(
            "vpnStatusText"
        );

    const description =
        document.getElementById(
            "vpnStatusDescription"
        );

    const button =
        document.getElementById(
            "connectVpnButton"
        );

    if (!vpnConnected) {

        vpnConnected = true;

        indicator.classList.remove(
            "disconnected"
        );

        indicator.classList.add(
            "connected"
        );

        statusText.textContent =
            "CONNECTED";

        description.textContent =
            "PinVPN is ready. WireGuard configuration will be connected here.";

        button.textContent =
            "DISCONNECT";

        button.classList.add(
            "connected"
        );

    } else {

        vpnConnected = false;

        indicator.classList.remove(
            "connected"
        );

        indicator.classList.add(
            "disconnected"
        );

        statusText.textContent =
            "DISCONNECTED";

        description.textContent =
            "Your VPN connection is currently inactive.";

        button.textContent =
            "CONNECT VPN";

        button.classList.remove(
            "connected"
        );
    }
}


// ============================================================
// DEVICES
// ============================================================

async function loadDevices() {

    const devicesList =
        document.getElementById("devicesList");

    if (!devicesList) {
        return;
    }

    try {

        const response = await fetch(
            "/api/devices",
            {
                method: "GET",
                credentials: "include"
            }
        );

        if (!response.ok) {

            if (response.status === 401) {
                console.warn(
                    "Authentication required for devices."
                );
            }

            throw new Error(
                "Failed to load devices."
            );
        }

        const data = await response.json();

        renderDevices(
            data.devices || []
        );

    } catch (error) {

        console.error(
            "Load devices error:",
            error
        );

        devicesList.innerHTML = `
            <div class="no-devices">

                <div class="no-devices-icon">
                    ⚠️
                </div>

                <h3>
                    Failed to load devices
                </h3>

                <p>
                    Please refresh the page and try again.
                </p>

            </div>
        `;
    }
}

function renderDevices(devices) {

    const devicesList =
        document.getElementById("devicesList");

    if (!devicesList) {
        return;
    }


    // No devices

    if (!devices.length) {

        devicesList.innerHTML = `

            <div class="no-devices">

                <div class="no-devices-icon">
                    📱
                </div>

                <h3>
                    No devices connected
                </h3>

                <p>
                    Add your first device to start using PinVPN.
                </p>

                <button
                    class="secondary-button"
                    onclick="addDevice()"
                >
                    + Add device
                </button>

            </div>

        `;

        return;
    }


    // Devices exist

    devicesList.innerHTML = devices.map(
        device => {

            const status =
                device.status || "offline";

            const statusText =
                status.toUpperCase();

            return `

                <div
                    class="device-item"
                    data-device-id="${device.id}"
                >

                    <div class="device-info">

                        <div class="device-icon">
                            💻
                        </div>

                        <div>

                            <div class="device-name">
                                ${escapeHtml(device.name)}
                            </div>

                            <div
                                class="device-status ${status}"
                            >
                                <span class="device-status-dot"></span>
                                ${statusText}
                            </div>

                        </div>

                    </div>


                    <div class="device-actions">

                        <button
                            class="download-config-button"
                            onclick="downloadWireGuardConfig('${device.id}')"
                            title="Download WireGuard configuration"
                        >
                            ↓ Download .conf
                        </button>

                        <button
                            class="delete-device-button"
                            onclick="deleteDevice('${device.id}')"
                            title="Remove device"
                        >
                            ×
                        </button>

                    </div>

                </div>

            `;

        }
    ).join("");
}

async function downloadWireGuardConfig(deviceId) {

    try {

        const response = await fetch(
            `/api/devices/${deviceId}/wireguard`,
            {
                method: "GET",
                credentials: "include"
            }
        );


        if (!response.ok) {

            let message =
                "Failed to download WireGuard configuration.";

            try {

                const data =
                    await response.json();

                if (data.detail) {
                    message = data.detail;
                }

            } catch (error) {
                // Ignore JSON parsing error
            }

            alert(message);

            return;
        }


        const blob =
            await response.blob();


        const url =
            window.URL.createObjectURL(blob);


        const link =
            document.createElement("a");

        link.href = url;

        link.download =
            "PinVPN-WireGuard.conf";

        document.body.appendChild(link);

        link.click();

        link.remove();

        window.URL.revokeObjectURL(url);


    } catch (error) {

        console.error(
            "WireGuard download error:",
            error
        );

        alert(
            "Unable to download WireGuard configuration."
        );

    }
}

async function addDevice() {

    const name =
        prompt(
            "Enter a name for this device:"
        );


    if (name === null) {
        return;
    }


    const deviceName =
        name.trim();


    if (!deviceName) {

        alert(
            "Please enter a device name."
        );

        return;
    }


    if (deviceName.length > 50) {

        alert(
            "Device name cannot be longer than 50 characters."
        );

        return;
    }


    try {

        const response = await fetch(
            "/api/devices",
            {
                method: "POST",

                credentials: "include",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    name: deviceName
                })
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.detail ||
                "Failed to add device."
            );

            return;
        }


        await loadDevices();


    } catch (error) {

        console.error(
            "Add device error:",
            error
        );

        alert(
            "Could not connect to PinVPN server."
        );
    }
}


async function deleteDevice(deviceId) {

    const confirmed =
        confirm(
            "Remove this device from your PinVPN account?"
        );


    if (!confirmed) {
        return;
    }


    try {

        const response = await fetch(
            `/api/devices/${deviceId}`,
            {
                method: "DELETE",
                credentials: "include"
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            alert(
                data.detail ||
                "Failed to delete device."
            );

            return;
        }


        await loadDevices();


    } catch (error) {

        console.error(
            "Delete device error:",
            error
        );

        alert(
            "Could not connect to PinVPN server."
        );
    }
}


// ============================================================
// HTML ESCAPING
// ============================================================

function escapeHtml(value) {

    return String(value)

        .replaceAll("&", "&amp;")

        .replaceAll("<", "&lt;")

        .replaceAll(">", "&gt;")

        .replaceAll('"', "&quot;")

        .replaceAll("'", "&#039;");
}

/* ============================================================
   START
============================================================ */

document.addEventListener("DOMContentLoaded", async () => {

    await checkServer();

    try {

        const response = await fetch(
            "/api/auth/me",
            {
                method: "GET",
                credentials: "include"
            }
        );

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        if (
            data &&
            data.authenticated &&
            data.user
        ) {
            showDashboard(data.user);
        }

    } catch (error) {

        console.error(
            "Session restore error:",
            error
        );

    }

});
