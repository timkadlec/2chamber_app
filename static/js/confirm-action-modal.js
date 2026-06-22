// Generic confirmation modal for fetch-based POST actions.
// Reads data-action-* attributes from the trigger button.
(function () {
    function csrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    function toastAfterReload(message, type) {
        sessionStorage.setItem('toast:message', message);
        sessionStorage.setItem('toast:type', type || 'success');
    }

    document.addEventListener('DOMContentLoaded', () => {
        const modalEl = document.getElementById('confirmActionModal');
        if (!modalEl) return;

        const titleEl    = modalEl.querySelector('.js-confirm-title');
        const messageEl  = modalEl.querySelector('.js-confirm-message');
        const errorEl    = modalEl.querySelector('.js-confirm-error');
        const spinnerEl  = modalEl.querySelector('.js-confirm-spinner');
        const submitBtn  = modalEl.querySelector('.js-confirm-submit');

        let actionUrl   = null;
        let toastMsg    = null;
        let busy        = false;

        modalEl.addEventListener('show.bs.modal', (event) => {
            const trigger = event.relatedTarget;
            if (!trigger) return;

            actionUrl = trigger.dataset.actionUrl || null;
            toastMsg  = trigger.dataset.actionToast || null;

            if (titleEl)   titleEl.textContent  = trigger.dataset.actionTitle   || 'Potvrdit akci';
            if (messageEl) messageEl.innerHTML  = trigger.dataset.actionMessage || 'Opravdu chcete provést tuto akci?';

            const btnLabel = trigger.dataset.actionBtnLabel || 'Potvrdit';
            const btnClass = trigger.dataset.actionBtnClass || 'btn-danger';
            if (submitBtn) {
                submitBtn.textContent = btnLabel;
                submitBtn.className   = `btn btn-sm js-confirm-submit ${btnClass}`;
                submitBtn.disabled    = false;
            }

            if (errorEl)   { errorEl.classList.add('d-none');   errorEl.textContent = ''; }
            if (spinnerEl) { spinnerEl.classList.add('d-none'); }
            busy = false;
        });

        submitBtn?.addEventListener('click', async () => {
            if (busy || !actionUrl) return;
            busy = true;

            if (submitBtn) submitBtn.disabled = true;
            if (spinnerEl) spinnerEl.classList.remove('d-none');
            if (errorEl)   { errorEl.classList.add('d-none'); errorEl.textContent = ''; }

            try {
                const resp = await fetch(actionUrl, {
                    method: 'POST',
                    headers: { 'Accept': 'application/json', 'X-CSRFToken': csrfToken() }
                });
                const data = await resp.json().catch(() => ({}));
                if (!resp.ok || data.success === false) {
                    throw new Error(data.message || `HTTP ${resp.status}`);
                }

                toastAfterReload(toastMsg || data.message || 'Hotovo.', 'success');
                bootstrap.Modal.getInstance(modalEl)?.hide();
                window.location.reload();

            } catch (e) {
                if (errorEl) { errorEl.textContent = e.message; errorEl.classList.remove('d-none'); }
                if (spinnerEl) spinnerEl.classList.add('d-none');
                if (submitBtn) submitBtn.disabled = false;
                busy = false;
            }
        });
    });
})();
