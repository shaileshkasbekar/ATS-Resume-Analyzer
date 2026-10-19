document.addEventListener("DOMContentLoaded", function () {

    // -----------------------------------------
    // Mobile sidebar menu
    // -----------------------------------------

    document.querySelectorAll("[data-menu-toggle]").forEach(function (button) {
        button.addEventListener("click", function () {
            document.body.classList.toggle("menu-open");
        });
    });


    // -----------------------------------------
    // Close flash messages
    // -----------------------------------------

    document.querySelectorAll(".flash button").forEach(function (button) {
        button.addEventListener("click", function () {
            button.parentElement.remove();
        });
    });


    // -----------------------------------------
    // Drag and drop upload box
    // -----------------------------------------

    document.querySelectorAll(".dropzone").forEach(function (zone) {

        var input = zone.querySelector("input[type=file]");
        var fileLabel = zone.querySelector(".dropzone-file");

        input.addEventListener("change", function () {
            var file = input.files[0];

            if (!file) {
                zone.classList.remove("has-file");
                fileLabel.textContent = "";
                return;
            }

            var sizeMb = (file.size / (1024 * 1024)).toFixed(2);
            fileLabel.textContent = file.name + " (" + sizeMb + " MB)";
            zone.classList.add("has-file");
        });

        ["dragenter", "dragover"].forEach(function (name) {
            input.addEventListener(name, function () {
                zone.classList.add("dragging");
            });
        });

        ["dragleave", "drop"].forEach(function (name) {
            input.addEventListener(name, function () {
                zone.classList.remove("dragging");
            });
        });
    });


    // -----------------------------------------
    // "Analyzing..." screen while the AI works
    // -----------------------------------------

    var overlay = document.getElementById("loading-overlay");

    document.querySelectorAll("form[data-loading]").forEach(function (form) {
        form.addEventListener("submit", function () {
            if (overlay) {
                overlay.hidden = false;
            }

            var button = form.querySelector("button[type=submit]");

            if (button) {
                button.disabled = true;
            }
        });
    });

    // Hide it again if the user comes back with the browser Back button
    window.addEventListener("pageshow", function () {
        if (overlay) {
            overlay.hidden = true;
        }

        document.querySelectorAll("form[data-loading] button[type=submit]").forEach(function (button) {
            button.disabled = false;
        });
    });


    // -----------------------------------------
    // History search + filter
    // -----------------------------------------

    var search = document.querySelector("[data-history-search]");
    var typeFilter = document.querySelector("[data-history-type]");
    var rows = document.querySelectorAll("[data-history-row]");
    var noMatch = document.querySelector("[data-history-nomatch]");

    function filterHistory() {
        var text = search ? search.value.trim().toLowerCase() : "";
        var type = typeFilter ? typeFilter.value : "";
        var visible = 0;

        rows.forEach(function (row) {
            var matchesText = row.textContent.toLowerCase().indexOf(text) !== -1;
            var matchesType = !type || row.getAttribute("data-type") === type;
            var show = matchesText && matchesType;

            row.hidden = !show;

            if (show) {
                visible++;
            }
        });

        if (noMatch) {
            noMatch.hidden = visible !== 0;
        }
    }

    if (search) {
        search.addEventListener("input", filterHistory);
    }

    if (typeFilter) {
        typeFilter.addEventListener("change", filterHistory);
    }
});
