// static/js/move_semester_modal.js
(function () {
    function init(modalEl) {
        const loadingEl = modalEl.querySelector('.js-loading');
        const errorEl = modalEl.querySelector('.js-error');
        const contentEl = modalEl.querySelector('.js-content');

        const curSemEl = modalEl.querySelector('.js-current-semester');
        const upSemEl = modalEl.querySelector('.js-upcoming-semester');

        const notInCurrentEl = modalEl.querySelector('.js-not-in-current');
        const noUpcomingEl = modalEl.querySelector('.js-no-upcoming');

        const playersListEl = modalEl.querySelector('.js-players-list');
        const emptyEl = modalEl.querySelector('.js-empty');
        const playerCountEl = modalEl.querySelector('.js-player-count');
        const summaryEl = modalEl.querySelector('.js-summary');

        const submitBtn = modalEl.querySelector('.js-submit');
        const actionStatusEl = modalEl.querySelector('.js-action-status');

        const optCopyTeachersEl = modalEl.querySelector('.js-opt-copy-teachers');
        const optCarryStudentsEl = modalEl.querySelector('.js-opt-carry-students');
        const optCarryGuestsEl = modalEl.querySelector('.js-opt-carry-guests');

        let latestInfo = null;
        let isBusy = false;

        function toast(message, type = 'info') {
            if (typeof window.showToast === 'function') {
                window.showToast(message, type); // success|danger|warning|info|...
            }
        }

        function getEnsembleId() {
            return modalEl.dataset.ensembleId;
        }

        function setBusy(state) {
            isBusy = state;
            if (actionStatusEl) actionStatusEl.classList.toggle('d-none', !state);
            if (submitBtn) submitBtn.disabled = state || !canSubmit();
        }

        function showError(msg) {
            if (!errorEl) return;
            errorEl.classList.remove('d-none');
            errorEl.textContent = msg;
        }

        function clearError() {
            if (!errorEl) return;
            errorEl.classList.add('d-none');
            errorEl.textContent = '';
        }

        function resetUI() {
            latestInfo = null;
            clearError();

            if (loadingEl) loadingEl.classList.remove('d-none');
            if (contentEl) contentEl.classList.add('d-none');

            if (playersListEl) playersListEl.innerHTML = '';
            if (emptyEl) emptyEl.classList.add('d-none');

            if (playerCountEl) playerCountEl.textContent = '0';
            if (summaryEl) summaryEl.textContent = '—';

            if (notInCurrentEl) notInCurrentEl.classList.add('d-none');
            if (noUpcomingEl) noUpcomingEl.classList.add('d-none');

            if (curSemEl) curSemEl.textContent = '—';
            if (upSemEl) upSemEl.textContent = '—';

            if (submitBtn) submitBtn.disabled = true;
            setBusy(false);
        }

        function canSubmit() {
            return !!(latestInfo && latestInfo.upcoming_semester && latestInfo.ensemble_is_in_current_semester);
        }

        function escapeHtml(s) {
            if (s === null || s === undefined) return '';
            return String(s)
                .replaceAll('&', '&amp;')
                .replaceAll('<', '&lt;')
                .replaceAll('>', '&gt;')
                .replaceAll('"', '&quot;')
                .replaceAll("'", '&#039;');
        }

        function renderPlayerRow(p) {
            const isGuest = !!p.is_guest;
            const isStudent = !!p.student_id;
            const fullName = escapeHtml(p.full_name || '—');

            const instrName = p.instrument ? escapeHtml(p.instrument.name) : '—';
            const section = p.instrument && p.instrument.section ? escapeHtml(p.instrument.section.name) : null;
            const group = p.instrument && p.instrument.group ? escapeHtml(p.instrument.group.name) : null;

            const badges = [
                isGuest ? `<span class="badge bg-light text-muted border ms-2">host</span>` : '',
                isStudent ? `<span class="badge bg-info text-dark ms-2">student</span>` : '',
                p.has_active_subject_in_upcoming_semester
                    ? `<span class="badge bg-success ms-2">má předmět</span>`
                    : (isStudent ? `<span class="badge bg-warning text-dark ms-2">bez předmětu</span>` : '')
            ].join('');

            const meta = [group, section, instrName].filter(Boolean).join(' · ');

            return `
        <div class="list-group-item d-flex justify-content-between align-items-center">
          <div>
            <div class="fw-semibold">${fullName}${badges}</div>
            <div class="text-muted small">${escapeHtml(meta || '')}</div>
          </div>
        </div>
      `;
        }

        function computeSummary(players) {
            const students = players.filter(x => !!x.student_id).length;
            const guests = players.filter(x => !!x.is_guest).length;
            const okUpcoming = players.filter(x => !!x.has_active_subject_in_upcoming_semester).length;
            return `studentů: ${students}, hostů: ${guests}, studentů s předmětem v příštím semestru: ${okUpcoming}/${students}`;
        }

        async function loadMoveInfo() {
            const ensembleId = getEnsembleId();
            const url = `/api/ensemble/${ensembleId}/get-semester-move-info`;
            const resp = await fetch(url, {headers: {'Accept': 'application/json'}});
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        }

        async function doMove() {
            const ensembleId = getEnsembleId();
            const url = `/api/ensemble/${ensembleId}/move-to-upcoming-semester`;

            const payload = {
                copy_teachers: !!optCopyTeachersEl?.checked,
                carry_students: !!optCarryStudentsEl?.checked,
                carry_guests: !!optCarryGuestsEl?.checked,
            };

            const resp = await fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
                body: JSON.stringify(payload),
            });

            const data = await resp.json().catch(() => ({}));
            if (!resp.ok || data.success === false) throw new Error(data.message || `HTTP ${resp.status}`);
            return data;
        }

        // capture ensemble_id from the clicked button
        modalEl.addEventListener('show.bs.modal', (event) => {
            const btn = event.relatedTarget;
            const ensembleId = btn?.dataset?.ensembleId;
            modalEl.dataset.ensembleId = ensembleId || '';
        });

        modalEl.addEventListener('shown.bs.modal', async () => {
            resetUI();

            const ensembleId = getEnsembleId();
            if (!ensembleId) {
                const msg = 'Chybí ensemble_id (data-ensemble-id na tlačítku).';
                showError(msg);
                toast(msg, 'danger');
                if (loadingEl) loadingEl.classList.add('d-none');
                return;
            }

            try {
                const info = await loadMoveInfo();
                latestInfo = info;

                if (loadingEl) loadingEl.classList.add('d-none');
                if (contentEl) contentEl.classList.remove('d-none');

                const cur = info.current_semester ? `${info.current_semester.name} (ID ${info.current_semester.id})` : '—';
                const up = info.upcoming_semester ? `${info.upcoming_semester.name} (ID ${info.upcoming_semester.id})` : '—';

                if (curSemEl) curSemEl.textContent = cur;
                if (upSemEl) upSemEl.textContent = up;

                if (!info.ensemble_is_in_current_semester && notInCurrentEl) notInCurrentEl.classList.remove('d-none');
                if (!info.upcoming_semester && noUpcomingEl) noUpcomingEl.classList.remove('d-none');

                const players = info.players || [];
                if (playerCountEl) playerCountEl.textContent = String(players.length);
                if (summaryEl) summaryEl.textContent = computeSummary(players);

                if (!players.length) {
                    if (emptyEl) emptyEl.classList.remove('d-none');
                } else if (playersListEl) {
                    playersListEl.innerHTML = players.map(renderPlayerRow).join('');
                }

                if (submitBtn) submitBtn.disabled = !canSubmit();
            } catch (e) {
                if (loadingEl) loadingEl.classList.add('d-none');
                if (contentEl) contentEl.classList.add('d-none');

                const msg = `Nepodařilo se načíst informace o převodu. (${e.message})`;
                showError(msg);
                toast(msg, 'danger');

                if (submitBtn) submitBtn.disabled = true;
            }
        });

        submitBtn?.addEventListener('click', async () => {
            if (!canSubmit() || isBusy) return;

            clearError();
            setBusy(true);

            try {
                const data = await doMove();

                // show toast before reload (if you later redirect instead, it still shows)
                const msg = data.message || 'Soubor byl převeden do příštího semestru.';
                sessionStorage.setItem("toast:message", msg);
                sessionStorage.setItem("toast:type", "success");
                window.location.reload();
            } catch (e) {
                const msg = `Nepodařilo se provést převod. (${e.message})`;
                showError(msg);
                toast(msg, 'danger');
                setBusy(false);
            }
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.js-move-semester-modal').forEach(init);
    });
})();
