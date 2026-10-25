document.addEventListener("DOMContentLoaded", function () {

    // -----------------------------------------
    // Mobile sidebar menu
    // -----------------------------------------

    var menuButton = document.querySelector(".mobile-bar [data-menu-toggle]");

    function setMenu(open) {
        document.body.classList.toggle("menu-open", open);

        if (menuButton) {
            menuButton.setAttribute("aria-expanded", open ? "true" : "false");
            menuButton.setAttribute("aria-label", open ? "Close menu" : "Open menu");
        }

        if (open) {
            var first = document.querySelector("#main-nav a");
            if (first) { first.focus(); }
        }
    }

    document.querySelectorAll("[data-menu-toggle]").forEach(function (button) {
        button.addEventListener("click", function () {
            setMenu(!document.body.classList.contains("menu-open"));
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && document.body.classList.contains("menu-open")) {
            setMenu(false);
            if (menuButton) { menuButton.focus(); }
        }
    });


    // -----------------------------------------
    // Confirmation dialog for destructive actions
    // <button data-confirm="Delete this?"> inside a form
    // -----------------------------------------

    var dialog = null;

    function confirmDialog(message, onConfirm) {

        if (!window.HTMLDialogElement) {
            if (window.confirm(message)) { onConfirm(); }
            return;
        }

        if (!dialog) {
            dialog = document.createElement("dialog");
            dialog.className = "confirm";
            dialog.setAttribute("aria-labelledby", "confirm-title");
            dialog.innerHTML =
                '<h3 id="confirm-title">Are you sure?</h3><p data-confirm-text></p>' +
                '<div class="actions" style="justify-content:flex-end;">' +
                '<button type="button" class="btn btn-ghost" data-confirm-cancel>Cancel</button>' +
                '<button type="button" class="btn btn-danger" data-confirm-ok>Delete</button></div>';
            document.body.appendChild(dialog);
            dialog.querySelector("[data-confirm-cancel]").addEventListener("click", function () { dialog.close(); });
        }

        dialog.querySelector("[data-confirm-text]").textContent = message;

        var ok = dialog.querySelector("[data-confirm-ok]");
        var fresh = ok.cloneNode(true);
        ok.parentNode.replaceChild(fresh, ok);

        fresh.addEventListener("click", function () {
            dialog.close();
            onConfirm();
        });

        dialog.showModal();
        dialog.querySelector("[data-confirm-cancel]").focus();
    }

    document.querySelectorAll("[data-confirm]").forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();

            var form = button.closest("form");

            confirmDialog(button.getAttribute("data-confirm"), function () {
                if (form) { form.submit(); }
            });
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
    // File checks before upload (type from "accept", max 5 MB)
    // The server checks again; this only gives faster feedback.
    // -----------------------------------------

    var MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

    function fileErrorBox(input) {
        var holder = input.closest(".field") || input.parentElement;
        var box = holder.querySelector(".field-error");

        if (!box) {
            box = document.createElement("p");
            box.className = "field-error";
            box.setAttribute("role", "alert");
            holder.appendChild(box);
        }

        return box;
    }

    function validateFile(input) {
        var file = input.files[0];
        var box = fileErrorBox(input);
        var allowed = (input.getAttribute("accept") || "").split(",").map(function (a) { return a.trim().toLowerCase(); }).filter(Boolean);
        var name = file ? file.name.toLowerCase() : "";
        var message = "";

        if (file && allowed.length && !allowed.some(function (ext) { return name.endsWith(ext); })) {
            message = "This file type is not supported. Please choose a " + allowed.join(" or ").toUpperCase().replace(/\./g, "") + " file.";
        } else if (file && file.size > MAX_UPLOAD_BYTES) {
            message = "This file is " + (file.size / (1024 * 1024)).toFixed(1) + " MB. The maximum size is 5 MB.";
        }

        box.textContent = message;

        if (message) {
            input.value = "";
            return false;
        }

        return true;
    }

    document.querySelectorAll("input[type=file]").forEach(function (input) {
        if (!input.closest(".dropzone")) {
            input.addEventListener("change", function () { validateFile(input); });
        }
    });


    // -----------------------------------------
    // Drag and drop upload box
    // -----------------------------------------

    document.querySelectorAll(".dropzone").forEach(function (zone) {

        var input = zone.querySelector("input[type=file]");
        var fileLabel = zone.querySelector(".dropzone-file");

        input.addEventListener("change", function () {
            var file = input.files[0];

            if (!file || !validateFile(input)) {
                zone.classList.remove("has-file");
                fileLabel.textContent = "";
                return;
            }

            var sizeMb = (file.size / (1024 * 1024)).toFixed(2);
            fileLabel.textContent = "Selected: " + file.name + " (" + sizeMb + " MB)";
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
    // Job match: paste / file / role tabs
    // Fields in hidden panels are disabled, so they are
    // neither validated nor submitted.
    // -----------------------------------------

    document.querySelectorAll("[data-mode-form]").forEach(function (form) {

        function showMode() {
            var checked = form.querySelector("input[name=mode]:checked");
            var mode = checked ? checked.value : "paste";

            form.querySelectorAll("[data-mode-panel]").forEach(function (panel) {
                var visible = panel.getAttribute("data-mode-panel").split(" ").indexOf(mode) !== -1;

                panel.hidden = !visible;

                panel.querySelectorAll("input, select, textarea").forEach(function (field) {
                    field.disabled = !visible;
                });
            });
        }

        form.querySelectorAll("input[name=mode]").forEach(function (radio) {
            radio.addEventListener("change", showMode);
        });

        showMode();

        // A saved resume version replaces the upload

        var versionSelect = form.querySelector("[data-version-select]");
        var uploadField = form.querySelector("[data-upload-field]");

        if (versionSelect && uploadField) {

            var toggleUpload = function () {
                var useVersion = versionSelect.value !== "";
                uploadField.hidden = useVersion;
                uploadField.querySelector("input[type=file]").disabled = useVersion;
            };

            versionSelect.addEventListener("change", toggleUpload);
            toggleUpload();
        }
    });


    // -----------------------------------------
    // JSON POST helper (sends the CSRF token)
    // -----------------------------------------

    window.postJSON = function (url, data) {
        var meta = document.querySelector("meta[name=csrf-token]");

        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-Token": meta ? meta.content : ""
            },
            body: JSON.stringify(data || {})
        }).then(function (response) {
            return response.json().then(function (body) {
                if (!response.ok) {
                    throw new Error(body.error || "Request failed");
                }
                return body;
            });
        });
    };


    // -----------------------------------------
    // Job match: preview the extracted requirements (rule-based, no AI)
    // -----------------------------------------

    document.querySelectorAll("[data-preview-requirements]").forEach(function (button) {

        var form = button.closest("form");
        var box = form.querySelector("[data-preview-box]");
        var error = form.querySelector("[data-preview-error]");

        function chips(items, kind) {
            if (!items.length) { return '<p class="empty">None found</p>'; }
            return '<div class="chips">' + items.map(function (s) {
                return '<span class="chip' + (kind ? " chip-" + kind : "") + '">' + escapeHtml(s) + "</span>";
            }).join("") + "</div>";
        }

        button.addEventListener("click", function () {

            error.textContent = "";
            button.disabled = true;

            window.postJSON("/job-match/preview", { job_description: form.querySelector("#job_description").value })
                .then(function (data) {
                    var years = data.experience_years === null ? "not stated" : (data.experience_years === 0 ? "entry level / freshers" : data.experience_years + "+ years");

                    box.innerHTML =
                        '<p class="section-label">Required (' + data.mandatory.length + ')</p>' + chips(data.mandatory, "primary") +
                        '<p class="section-label" style="margin-top:12px;">Preferred (' + data.preferred.length + ')</p>' + chips(data.preferred, "") +
                        '<p class="small" style="margin-top:12px;"><strong>Experience:</strong> ' + escapeHtml(years) +
                        (data.education ? " &nbsp;·&nbsp; <strong>Education:</strong> " + escapeHtml(data.education) : "") + "</p>" +
                        '<p class="field-hint" style="margin-top:8px;">Quick preview from the text. The full analysis also uses AI and may find a few more.</p>';
                    box.hidden = false;
                })
                .catch(function (e) { error.textContent = e.message; })
                .then(function () { button.disabled = false; });
        });
    });


    // -----------------------------------------
    // Improvement assistant: accept / reject
    // -----------------------------------------

    var STATUS_LABELS = { accepted: "Accepted", rejected: "Rejected", pending: "" };

    function refreshCounts() {
        ["accepted", "rejected", "pending"].forEach(function (status) {
            var badge = document.querySelector('[data-count="' + status + '"]');
            if (badge) {
                var n = document.querySelectorAll('.suggestion[data-status="' + status + '"]').length;
                badge.textContent = n + " " + (status === "pending" ? "to review" : status);
            }
        });
    }

    document.querySelectorAll(".suggestion").forEach(function (card) {

        var badge = card.querySelector("[data-status-badge]");
        var message = card.querySelector("[data-message]");

        function show(status) {
            card.setAttribute("data-status", status);
            badge.textContent = STATUS_LABELS[status] || "";
            badge.className = "badge status-badge " + (status === "accepted" ? "tint-good" : "tint-low");
            refreshCounts();
        }

        show(card.getAttribute("data-status"));

        var editButton = card.querySelector("[data-edit-suggestion]");

        if (editButton) {
            editButton.addEventListener("click", function () {
                var box = card.querySelector("[data-improved]");
                box.focus();
                box.setSelectionRange(box.value.length, box.value.length);
                message.textContent = "Edit the text, then press Accept.";
            });
        }

        card.querySelectorAll("[data-set-status]").forEach(function (button) {
            button.addEventListener("click", function () {
                var status = button.getAttribute("data-set-status");
                var data = { status: status };
                var improved = card.querySelector("[data-improved]");

                if (improved && status === "accepted") {
                    data.improved = improved.value;
                }

                message.textContent = "Saving…";

                window.postJSON("/assistant/suggestion/" + card.getAttribute("data-suggestion"), data)
                    .then(function () {
                        show(status);
                        message.textContent = "";
                    })
                    .catch(function (error) {
                        message.textContent = error.message;
                    });
            });
        });
    });


    // -----------------------------------------
    // Learning roadmap: mark tasks done
    // -----------------------------------------

    document.querySelectorAll("[data-roadmap-item]").forEach(function (item) {

        var checkbox = item.querySelector("input[type=checkbox]");

        checkbox.addEventListener("change", function () {

            window.postJSON("/roadmap/item/" + item.getAttribute("data-roadmap-item"), { done: checkbox.checked })
                .then(function (body) {
                    item.classList.toggle("done", checkbox.checked);

                    var text = document.querySelector("[data-progress-text]");
                    var bar = document.querySelector("[data-progress-bar]");

                    if (text) { text.textContent = body.done + " / " + body.total; }
                    if (bar) {
                        bar.style.width = (body.total ? body.done / body.total * 100 : 0) + "%";
                        bar.parentElement.setAttribute("aria-valuenow", body.done);
                    }
                })
                .catch(function () {
                    checkbox.checked = !checkbox.checked;
                });
        });
    });


    // -----------------------------------------
    // Mock interview: answers, feedback, voice
    // -----------------------------------------

    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    function escapeHtml(text) {
        var div = document.createElement("div");
        div.textContent = text == null ? "" : String(text);
        return div.innerHTML;
    }

    function renderFeedback(box, feedback) {
        var meters = Object.keys(feedback.scores || {}).filter(function (k) {
            return feedback.scores[k] !== null;
        }).map(function (k) {
            var value = Math.round(feedback.scores[k]);
            return '<div class="meter"><div class="meter-head"><span>' + escapeHtml(k.charAt(0).toUpperCase() + k.slice(1)) +
                '</span><strong>' + value + '%</strong></div><div class="meter-track"><div class="meter-fill" style="width:' + value + '%"></div></div></div>';
        }).join("");

        box.innerHTML =
            '<div class="grid grid-2"><div><p class="section-label">Scores</p>' + meters + "</div>" +
            '<div><p class="section-label">Feedback</p><p class="small">' + escapeHtml(feedback.feedback) + "</p>" +
            (feedback.improved_answer ? '<p class="section-label" style="margin-top:12px;">Stronger answer (for learning)</p><p class="small">' + escapeHtml(feedback.improved_answer) + "</p>" : "") +
            "</div></div>";
        box.hidden = false;
    }

    document.querySelectorAll("[data-question]").forEach(function (card) {

        var textarea = card.querySelector("[data-answer]");
        var message = card.querySelector("[data-message]");
        var submit = card.querySelector("[data-submit-answer]");
        var voice = card.querySelector("[data-voice]");

        submit.addEventListener("click", function () {
            submit.disabled = true;
            message.textContent = "Getting feedback…";

            window.postJSON("/interview/" + card.getAttribute("data-jd") + "/answer", {
                index: Number(card.getAttribute("data-question")),
                answer: textarea.value
            }).then(function (body) {
                renderFeedback(card.querySelector("[data-feedback]"), body.feedback);
                message.textContent = "Feedback saved.";
                card.dispatchEvent(new CustomEvent("answer-saved"));
            }).catch(function (error) {
                message.textContent = error.message;
            }).then(function () {
                submit.disabled = false;
            });
        });

        if (SpeechRecognition && voice) {

            voice.hidden = false;

            voice.addEventListener("click", function () {
                var recognition = new SpeechRecognition();
                recognition.lang = "en-IN";
                recognition.interimResults = false;

                message.textContent = "Listening…";

                recognition.onresult = function (event) {
                    var spoken = Array.prototype.map.call(event.results, function (r) { return r[0].transcript; }).join(" ");
                    textarea.value = (textarea.value ? textarea.value + " " : "") + spoken;
                };
                recognition.onend = function () { message.textContent = ""; };
                recognition.onerror = function () { message.textContent = "Microphone not available."; };

                recognition.start();
            });
        }
    });


    // -----------------------------------------
    // Mock interview: one question at a time
    // -----------------------------------------

    document.querySelectorAll("[data-interview]").forEach(function (box) {

        var cards = Array.prototype.slice.call(box.querySelectorAll("[data-question]"));
        var pager = box.querySelector("[data-pager]");

        if (!cards.length || !pager) { return; }

        var buttons = cards.map(function (card, i) {
            var b = document.createElement("button");
            b.type = "button";
            b.textContent = String(i + 1);
            b.addEventListener("click", function () { show(i, true); });
            pager.appendChild(b);
            return b;
        });

        function mark(i) {
            var answered = cards[i].getAttribute("data-answered") === "1";
            buttons[i].classList.toggle("answered", answered);
            buttons[i].setAttribute("aria-label", "Question " + (i + 1) + (answered ? ", answered" : ""));
            buttons[i].textContent = answered ? (i + 1) + " ✓" : String(i + 1);
        }

        function show(index, focus) {
            cards.forEach(function (card, i) {
                card.hidden = i !== index;
                buttons[i].classList.toggle("active", i === index);
                buttons[i].setAttribute("aria-current", i === index ? "true" : "false");
            });
            if (focus) { cards[index].querySelector("[data-answer]").focus(); }
        }

        cards.forEach(function (card, i) {
            mark(i);
            var prev = card.querySelector("[data-prev-question]");
            var next = card.querySelector("[data-next-question]");
            if (prev) { prev.addEventListener("click", function () { show(Math.max(0, i - 1), true); }); }
            if (next) { next.addEventListener("click", function () { show(Math.min(cards.length - 1, i + 1), true); }); }
            card.addEventListener("answer-saved", function () { card.setAttribute("data-answered", "1"); mark(i); });
        });

        // Start at the first unanswered question

        var start = cards.findIndex(function (c) { return c.getAttribute("data-answered") !== "1"; });
        show(start === -1 ? 0 : start, false);
    });


    // -----------------------------------------
    // Charts (Chart.js, loaded only on pages that have charts)
    // <canvas data-chart="line|bar" data-source="id-of-json-script">
    // -----------------------------------------

    function cssVar(name) {
        return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    }

    if (window.Chart) {

        var ink = cssVar("--text-2");
        var grid = cssVar("--chart-grid");

        Chart.defaults.font.family = "Inter, system-ui, sans-serif";
        Chart.defaults.color = ink;

        document.querySelectorAll("canvas[data-chart]").forEach(function (canvas) {

            var source = document.getElementById(canvas.getAttribute("data-source"));

            if (!source) {
                return;
            }

            var data = JSON.parse(source.textContent);
            var type = canvas.getAttribute("data-chart");

            // Colours follow the series' fixed slot, never its rank
            var datasets = data.datasets.map(function (set, i) {
                var color = cssVar("--series-" + ((i % 6) + 1));

                return Object.assign({
                    borderColor: color,
                    backgroundColor: color,
                    borderWidth: type === "line" ? 2 : 0,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBorderColor: cssVar("--surface"),
                    pointBorderWidth: 2,
                    borderRadius: 4,
                    borderSkipped: "start",
                    maxBarThickness: 22,
                    tension: 0
                }, set);
            });

            new Chart(canvas, {
                type: type,
                data: { labels: data.labels, datasets: datasets },
                options: {
                    maintainAspectRatio: false,
                    indexAxis: data.horizontal ? "y" : "x",
                    interaction: { mode: type === "line" ? "index" : "nearest", intersect: false },
                    plugins: {
                        legend: { display: datasets.length > 1, position: "top", align: "start", labels: { boxWidth: 12, boxHeight: 12 } },
                        tooltip: {
                            padding: 10,
                            callbacks: {
                                // Optional full names for short axis labels
                                title: function (items) {
                                    var i = items[0].dataIndex;
                                    return data.titles ? data.titles[i] + " (" + data.labels[i] + ")" : data.labels[i];
                                }
                            }
                        }
                    },
                    scales: {
                        x: { grid: { display: !!data.horizontal, color: grid }, border: { display: false }, ticks: { maxRotation: 0, autoSkip: true, precision: 0 }, max: data.horizontal ? data.max : undefined, beginAtZero: true },
                        y: { grid: { display: !data.horizontal, color: grid }, border: { display: false }, ticks: { precision: 0 }, beginAtZero: true, max: data.horizontal ? undefined : data.max }
                    }
                }
            });
        });
    }


    // -----------------------------------------
    // Copy text buttons
    // -----------------------------------------

    document.querySelectorAll("[data-copy]").forEach(function (button) {
        button.addEventListener("click", function () {
            var target = document.querySelector(button.getAttribute("data-copy"));

            if (!target || !navigator.clipboard) {
                return;
            }

            navigator.clipboard.writeText(target.textContent.trim()).then(function () {
                var original = button.innerHTML;
                button.innerHTML = '<i class="fa-solid fa-check"></i> Copied';
                setTimeout(function () {
                    button.innerHTML = original;
                }, 1500);
            });
        });
    });
});
