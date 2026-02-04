(function () {

    const queue = [];
    let showing = false;

    function ensureContainer() {
        const id = "globalToastContainer";

        let container = document.getElementById(id);
        if (!container) {
            container = document.createElement("div");
            container.id = id;
            container.className = "toast-container position-fixed bottom-0 end-0 p-3";
            container.style.zIndex = "1055";

            document.body.appendChild(container);
        }

        return container;
    }

    function escape(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    function processQueue() {
        if (showing) return;
        if (queue.length === 0) return;

        const { message, type } = queue.shift();
        showNow(message, type);
    }

    function showNow(message, type = "success") {
        showing = true;

        const allowed = ["success", "danger", "warning", "info", "primary", "secondary"];
        if (!allowed.includes(type)) {
            type = "info";
        }

        const container = ensureContainer();
        const id = "toast_" + Math.random().toString(36).slice(2);

        const el = document.createElement("div");
        el.id = id;
        el.className = `toast align-items-center text-bg-${type} border-0`;
        el.setAttribute("role", "alert");
        el.setAttribute("aria-live", "assertive");
        el.setAttribute("aria-atomic", "true");

        el.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${escape(message)}</div>
                <button type="button"
                        class="btn-close btn-close-white me-2 m-auto"
                        data-bs-dismiss="toast"
                        aria-label="Close">
                </button>
            </div>
        `;

        container.appendChild(el);

        const toast = new bootstrap.Toast(el, {
            delay: 3800
        });

        el.addEventListener("hidden.bs.toast", () => {
            el.remove();
            showing = false;

            // Small breathing space between messages
            setTimeout(processQueue, 200);
        });

        toast.show();
    }

    // --- Public API -------------------------------------------------

    window.showToast = function (message, type = "success") {
        queue.push({ message, type });
        processQueue();
    };

    // --- Session bridge --------------------------------------------

    document.addEventListener("DOMContentLoaded", () => {

        const msg = sessionStorage.getItem("toast:message");
        const type = sessionStorage.getItem("toast:type") || "success";

        if (msg) {
            sessionStorage.removeItem("toast:message");
            sessionStorage.removeItem("toast:type");

            window.showToast(msg, type);
        }
    });

})();
