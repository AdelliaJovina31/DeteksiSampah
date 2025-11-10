// RESPONSIVE NAVBAR
const navbarToggler = document.querySelector(".custom-toggler");
const navbarCollapse = document.querySelector("#navbarNav");
const closeMenuBtn = document.querySelector(".close-menu-btn");
const navbar = document.querySelector(".navbar");

navbarToggler.addEventListener("click", function () {
    navbarCollapse.classList.add("show");
    navbar.classList.add("show-overlay");
});

closeMenuBtn.addEventListener("click", function () {
    navbarCollapse.classList.remove("show");
    navbar.classList.remove("show-overlay");
});

document.addEventListener("click", function (e) {
    if (
        navbar.classList.contains("show-overlay") &&
        !navbarCollapse.contains(e.target) &&
        !navbarToggler.contains(e.target)
    ) {
        navbarCollapse.classList.remove("show");
        navbar.classList.remove("show-overlay");
    }
});

// ======== UPLOAD FILE ========
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");

const actionButton = document.getElementById("actionButton");

const kategoriDropdown = document.getElementById("kategori");
let kategoriValue = kategoriDropdown.value;

let arrow = document.getElementById("arrow");

let eventSource = null;
const recommendation = document.getElementById("recommendation");

kategoriDropdown.addEventListener("click", function() {
    arrow.classList.toggle("fa-chevron-up");
    arrow.classList.toggle("fa-chevron-down");
});

kategoriDropdown.addEventListener("blur", function () {
    arrow.classList.remove("fa-chevron-up");
    arrow.classList.add("fa-chevron-down");
});

fileInput.addEventListener("change", function() {
    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        const fileName = file.name;

        // form data untuk upload ke Flask (app.py)
        let formData = new FormData();
        formData.append("file", file);
        formData.append("kategori", kategoriValue);

        fetch("/upload?kategori=" + kategoriValue, {
            method: "POST",
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if(data.filename) {
                uploadStatus.innerHTML = `
                    <div class="d-inline-flex align-items-center border rounded px-3 py-2 mb-2">
                        <strong class="me-2">${fileName}</strong>
                        <i class="fa-solid fa-xmark" style="cursor: pointer;color: #DD3939;" onclick="removeFile()"></i>
                    </div>
                    <div>
                        <img src="${data.url}?t=${new Date().getTime()}" alt="Hasil Deteksi" class="img-fluid rounded shadow-sm" style="width: 100%; max-width: 500px; height: auto; border: 1px solid #ccc; border-radius: 10px;" />
                    </div>
                `;
            }

            // tampilkan rekomendasi aksi
            if(data.recommendations && data.recommendations.length > 0) {
                const recomList = data.recommendations.map(r => `<li>${r}</li>`).join("");
                recommendation.innerHTML = `
                    <div class="mt-3 text-start" style="max-width: 500px; margin: 0 auto;">
                        <h5 class="fw-bold mt-3">Rekomendasi Aksi: </h5>
                        <ul>${recomList}</ul>
                    </div>
                `;
            } else {
                recommendation.innerHTML = "";
            }

            actionButton.classList.add("d-none");
            recommendation.classList.remove("d-none");
        })
        .catch(error => console.error(error));
    }
});

function removeFile() {
    fileInput.value = ""; // reset file yang sudah diunggah
    uploadStatus.innerHTML = `<p class="text-muted"><i>Belum ada gambar yang diunggah</i></p>`;
    actionButton.classList.remove("d-none");
    recommendation.classList.add("d-none");
}

// ======== Filter Kategori Real-Time ========
const kategori = document.getElementById("kategori");

kategori.addEventListener("change", function() {
    kategoriValue = kategori.value;

    fetch("/set_category", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({kategori: kategoriValue})
    })
    .then(res => res.json())
    .then(data => console.log(data.message));
});

// ======== Filter Confidence Score ========
let confidence_threshold = document.getElementById("confidence-score").value / 100; // ubah skala slider 0-100 menjadi 0.0-1.0
const confSlider = document.getElementById("confidence-score");
const confScore = document.getElementById("confScore");

function updateSliderUI() {
    const value = (confSlider.value - confSlider.min) / (confSlider.max - confSlider.min) * 100;
    confSlider.style.background = `linear-gradient(to right, #73CA22 ${value}%, #ddd ${value}%)`;
    confScore.innerText = confSlider.value + "%";
}

// update slider UI saat halaman di-reload
updateSliderUI();

confSlider.addEventListener("input", function() {
    updateSliderUI();
    
    confidence_threshold = confSlider.value / 100;

    fetch("/set_confidence", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({confidence: confidence_threshold})
    })
    .then(res => res.json())
    .then(data => console.log("Confidence score: ", data.message))
    .catch(error => console.error(error));
});

function startRecommenStream() {
    eventSource = new EventSource("recommendations_feed");

    eventSource.onmessage = function(event) {
        const recs = JSON.parse(event.data);

        if(recs && recs.length > 0) {
            const recomList = recs.map(r => `<li>${r}</li>`).join("");
            recommendation.innerHTML = `
                <div class="mt-3 text-start" style="max-width: 500px; margin: 0 auto;">
                    <h5 class="fw-bold mt-3">Rekomendasi Aksi (Real-Time): </h5>
                    <ul>${recomList}</ul>
                </div>
            `;
            recommendation.classList.remove("d-none");
        } else {
            recommendation.innerHTML = "";
        }
    };

    eventSource.onerror = function() {
        console.log("Rekomendasi aksi terhenti");
        eventSource.close();
    };
}

// ======== AKSES KAMERA ========
const cameraBtn = document.getElementById("cameraBtn");
const cameraContainer = document.getElementById("cameraContainer");
const cameraFeed = document.getElementById("cameraFeed");

cameraBtn.addEventListener("click", () => {
    cameraFeed.src = "video_feed?ts=" + new Date().getTime(); // ambil stream dengan timestamp agar tidak pakai cache
    cameraContainer.classList.remove("d-none");
    actionButton.classList.add("d-none");
    uploadStatus.classList.add("d-none");

    startRecommenStream();
});

function stopCamera() {
    fetch("/stop_feed")
    .then(res => res.json())
    .then(data => console.log("Kamera dimatikan:", data))
    .catch(error => console.error(error));

    cameraFeed.src = "";
    cameraContainer.classList.add("d-none");
    actionButton.classList.remove("d-none");
    recommendation.classList.add("d-none");
    uploadStatus.classList.remove("d-none");
    
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
}
