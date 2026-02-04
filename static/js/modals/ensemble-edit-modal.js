// static/js/ensemble-edit-modal.js
document.addEventListener("DOMContentLoaded", () => {
    const modalEl = document.getElementById("editEnsembleModal");
    if (!modalEl) return;

    const form = modalEl.querySelector(".js-ensemble-edit-form");
    const input = modalEl.querySelector("input[name='name']");
    const idInput = modalEl.querySelector("input[name='ensemble_id']");
    const errorBox = modalEl.querySelector(".js-error");
    const submitBtn = modalEl.querySelector(".js-submit");

    const setError = (msg) => {
        if (!errorBox) return;
        if (!msg) {
            errorBox.classList.add("d-none");
            errorBox.textContent = "";
        } else {
            errorBox.textContent = msg;
            errorBox.classList.remove("d-none");
        }
    };

    const setBusy = (busy) => {
        if (!submitBtn) return;
        submitBtn.disabled = !!busy;
        if (busy) {
            submitBtn.dataset.originalHtml = submitBtn.innerHTML;
            submitBtn.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>Ukládám…`;
        } else if (submitBtn.dataset.originalHtml) {
            submitBtn.innerHTML = submitBtn.dataset.originalHtml;
            delete submitBtn.dataset.originalHtml;
        }
    };

    modalEl.addEventListener("shown.bs.modal", () => {
        setError(null);
        input?.focus();
        input?.select?.();
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        setError(null);

        const ensembleId = (idInput?.value || "").trim();
        const name = (input?.value || "").trim();

        if (!ensembleId) {
            setError("Chybí ID souboru.");
            return;
        }
        if (!name) {
            setError("Název souboru je povinný.");
            input?.focus();
            return;
        }

        setBusy(true);

        try {
            const res = await fetch(`/api/ensembles/${encodeURIComponent(ensembleId)}`, {
                method: "PATCH",
                headers: {
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({name}),
            });

            const payload = await res.json().catch(() => ({}));

            if (!res.ok || !payload.ok) {
                setError(payload.error || "Nepodařilo se uložit změny.");
                return;
            }

            const updated = payload.ensemble || {};
            const after = modalEl.dataset.after || "redirect";

            if (after === "redirect" && updated.detail_url) {
                sessionStorage.setItem("toast:message", "Soubor byl úspěšně upraven.");
                sessionStorage.setItem("toast:type", "success");

                window.location.assign(updated.detail_url);
                return;
            }

// Optional in-place updates:
            const titleHook = document.querySelector("[data-role='ensemble-name']");
            if (titleHook && updated.name) {
                titleHook.textContent = updated.name;
            }

// toast for non-redirect case
            window.showToast?.("Soubor byl úspěšně upraven.", "success");

// Close modal
            const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            modal.hide();

        } catch (err) {
            setError("Síťová chyba. Zkuste to znovu.");
        } finally {
            setBusy(false);
        }
    });
});
