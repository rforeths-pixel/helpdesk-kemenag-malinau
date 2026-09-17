document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("formLaporan");

    if (form) {

        form.addEventListener("submit", function () {

            alert("Laporan berhasil dikirim ke Helpdesk IT!");

        });

    }

});