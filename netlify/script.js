const formLaporan = document.getElementById("formLaporan");
const daftarLaporan = document.getElementById("daftarLaporan");

let laporan = [];


formLaporan.addEventListener("submit", function(event) {

    event.preventDefault();

    const nama = document.getElementById("nama").value;
    const judul = document.getElementById("judul").value;
    const deskripsi = document.getElementById("deskripsi").value;

    laporan.push({
        nama: nama,
        judul: judul,
        deskripsi: deskripsi,
        status: "Menunggu"
    });

    tampilkanLaporan();

    formLaporan.reset();

    alert("Laporan berhasil dikirim!");

});


function tampilkanLaporan() {

    if (laporan.length === 0) {

        daftarLaporan.innerHTML =
            "Belum ada laporan.";

        return;
    }


    daftarLaporan.innerHTML = "";


    laporan.forEach(function(item, index) {

        const div = document.createElement("div");

        div.className = "laporan-card";

        div.innerHTML = `
            <h3>${item.judul}</h3>

            <p>
                <strong>Nama:</strong>
                ${item.nama}
            </p>

            <p>
                ${item.deskripsi}
            </p>

            <p>
                <strong>Status:</strong>
                ${item.status}
            </p>
        `;

        daftarLaporan.appendChild(div);

    });

}