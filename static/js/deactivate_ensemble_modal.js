// static/js/deactivate_ensemble_modal.js
(function () {
    function init(modalEl) {
        const nameEl = modalEl.querySelector('.js-ensemble-name');
        const errorEl = modalEl.querySelector('.js-error');
        const successEl = modalEl.querySelector('.js-success');
        const submitBtn = modalEl.querySelector('.js-submit');
        const statusEl = modalEl.querySelector('.js-action-status');

        let busy = false;

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
            if (successEl) successEl.classList.add('d-none');
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

        function setSuccess(msg) {
            if (errorEl) errorEl.classList.add('d-none');
            if (successEl) {
                successEl.classList.remove('d-none');
                successEl.textContent = msg;
            }
        }

        function removeRow(ensembleId) {
            const btn = document.querySelector(`.js-deactivate-ensemble[data-ensemble-id="${ensembleId}"]`);
            const row = btn ? btn.closest('tr') : null;
            if (row) row.remove();
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
            if (successEl) successEl.classList.add('d-none');
            setBusy(false);
        });

        submitBtn?.addEventListener('click', async () => {
            if (busy) return;

            const ensembleId = modalEl.dataset.ensembleId;
            if (!ensembleId) {
                setError('Chybí ensemble_id.');
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

                setSuccess(data.message || 'Soubor byl deaktivován.');
                removeRow(ensembleId);

                // close modal after a short moment (optional)
                // const instance = bootstrap.Modal.getInstance(modalEl);
                // instance?.hide();

                setBusy(false);
                if (submitBtn) submitBtn.disabled = true; // prevent double click after success

            } catch (e) {
                setError(`Nepodařilo se deaktivovat soubor. (${e.message})`);
                setBusy(false);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.js-deactivate-ensemble-modal').forEach(init);
    });
})();
