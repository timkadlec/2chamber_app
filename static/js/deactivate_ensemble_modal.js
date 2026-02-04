// static/js/deactivate_ensemble_modal.js
(function () {
    function init(modalEl) {
        const nameEl = modalEl.querySelector('.js-ensemble-name');
        const errorEl = modalEl.querySelector('.js-error');
        const submitBtn = modalEl.querySelector('.js-submit');
        const statusEl = modalEl.querySelector('.js-action-status');

        let busy = false;

        function toast(message, type = 'info') {
            if (typeof window.showToast === 'function') {
                window.showToast(message, type);
            }
        }

        function toastAfterReload(message, type = 'success') {
            // your toasts.js reads these on DOMContentLoaded
            sessionStorage.setItem("toast:message", message);
            sessionStorage.setItem("toast:type", type);
        }

        function hideModal() {
            const instance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            instance.hide();
        }

        function csrfHeaders() {
            const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            return token ? {'X-CSRFToken': token} : {};
        }

        function setBusy(state) {
            busy = state;
            if (statusEl) statusEl.classList.toggle('d-none', !state);
            if (submitBtn) submitBtn.disabled = state;
        }

        function setError(msg) {
            if (errorEl) {
                errorEl.classList.remove('d-none');
                errorEl.textContent = msg;
            }
        }

        function clearError() {
            if (errorEl) {
                errorEl.classList.add('d-none');
                errorEl.textContent = '';
            }
        }

        // Pull ensemble info from the clicked button
        modalEl.addEventListener('show.bs.modal', (event) => {
            const btn = event.relatedTarget;
            const ensembleId = btn?.dataset?.ensembleId || '';
            const ensembleName = btn?.dataset?.ensembleName || '—';

            modalEl.dataset.ensembleId = ensembleId;
            modalEl.dataset.ensembleName = ensembleName;

            if (nameEl) nameEl.textContent = ensembleName;

            clearError();

            // allow repeated use: re-enable button each open
            if (submitBtn) submitBtn.disabled = false;

            setBusy(false);
        });

        submitBtn?.addEventListener('click', async () => {
            if (busy) return;

            const ensembleId = modalEl.dataset.ensembleId;
            if (!ensembleId) {
                const msg = 'Chybí ensemble_id.';
                setError(msg);
                toast(msg, 'danger');
                return;
            }

            clearError();
            setBusy(true);

            try {
                const resp = await fetch(`/api/ensemble/${ensembleId}/deactivate`, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        ...csrfHeaders()
                    }
                });

                const data = await resp.json().catch(() => ({}));
                if (!resp.ok || data.success === false) {
                    throw new Error(data.message || `HTTP ${resp.status}`);
                }

                const msg = data.message || 'Soubor byl deaktivován.';

                // persist toast across reload
                toastAfterReload(msg, 'success');

                // optional: close modal so it doesn't flash during reload
                hideModal();

                // reload to reflect changes everywhere
                window.location.reload();

            } catch (e) {
                const msg = `Nepodařilo se deaktivovat soubor. (${e.message})`;
                setError(msg);
                toast(msg, 'danger');
                setBusy(false);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.js-deactivate-ensemble-modal').forEach(init);
    });
})();
