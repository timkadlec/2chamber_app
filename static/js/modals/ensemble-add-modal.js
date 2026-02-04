// static/js/ensemble-add-modal.js
document.addEventListener("DOMContentLoaded", () => {
    const modalEl = document.getElementById("addEnsembleModal");
    if (!modalEl) return;

    const form = modalEl.querySelector(".js-ensemble-add-form");
    const input = modalEl.querySelector("input[name='name']");
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
            submitBtn.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>Vytvářím…`;
        } else if (submitBtn.dataset.originalHtml) {
            submitBtn.innerHTML = submitBtn.dataset.originalHtml;
            delete submitBtn.dataset.originalHtml;
        }
    };

    // Optional: focus input when modal opens
    modalEl.addEventListener("shown.bs.modal", () => {
        setError(null);
        form?.reset();
        input?.focus();
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        setError(null);

        const name = (input?.value || "").trim();
        if (!name) {
            setError("Název souboru je povinný.");
            input?.focus();
            return;
        }

        setBusy(true);

        try {
            const res = await fetch("/api/ensembles", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify({name}),
            });

            const payload = await res.json().catch(() => ({}));

            if (!res.ok || !payload.ok) {
                setError(payload.error || "Nepodařilo se vytvořit soubor.");
                setBusy(false);
                return;
            }

            const created = payload.ensemble || {};

            if (created.detail_url) {
                // store toast for the next page (detail)
                sessionStorage.setItem("toast:message", "Soubor byl úspěšně vytvořen.");
                sessionStorage.setItem("toast:type", "success");

                window.location.assign(created.detail_url);
                return;
            }

            // If you use TomSelect, this will inject + select the new option.
            const targetId = modalEl.dataset.selectTarget || "ensemble_id";
            const select = document.getElementById(targetId);

            if (select && select.tomselect) {
                select.tomselect.addOption({value: created.id, text: created.name});
                select.tomselect.addItem(created.id);
            } else if (select) {
                // Plain select fallback
                const opt = document.createElement("option");
                opt.value = created.id;
                opt.textContent = created.name;
                opt.selected = true;
                select.appendChild(opt);
                select.dispatchEvent(new Event("change", {bubbles: true}));
            } else {
                // Last resort: refresh
                // window.location.reload();
            }

            // Show toast
            window.showToast?.("Soubor byl úspěšně vytvořen.", "success");

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
