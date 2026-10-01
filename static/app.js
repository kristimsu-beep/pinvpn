async function checkServer() {

    const statusElement =
        document.getElementById("serverStatus");

    const cardStatus =
        document.getElementById("cardStatus");

    const databaseStatus =
        document.getElementById("databaseStatus");


    statusElement.textContent =
        "Checking...";


    try {

        const response =
            await fetch("/health");


        const data =
            await response.json();


        if (data.status === "ok") {

            statusElement.textContent =
                "Server online";

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

        } else {

            statusElement.textContent =
                "Server error";

            cardStatus.textContent =
                "● Error";

        }

    } catch (error) {

        statusElement.textContent =
            "Offline";

        cardStatus.textContent =
            "● Offline";

        databaseStatus.textContent =
            "Unavailable";

        console.error(error);

    }
}


function startPinVPN() {

    alert(
        "PinVPN account system is coming soon."
    );

}


document.addEventListener(
    "DOMContentLoaded",
    () => {

        checkServer();

    }
);
