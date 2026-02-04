// static/js/modals/takeover-teacher.js
(function () {
    document.addEventListener("DOMContentLoaded", () => {
        const modalEl = document.getElementById("takeoverTeacherModal");
        if (!modalEl) return;

        const loadingEl = modalEl.querySelector(".js-loading");
        const errorEl = modalEl.querySelector(".js-error");
        const teachersWrapEl = modalEl.querySelector(".js-teachers");
        const teachersListEl = modalEl.querySelector(".js-teachers-list");
        const emptyEl = modalEl.querySelector(".js-empty");

        const formEl = modalEl.querySelector("form");
        const submitBtn = formEl ? formEl.querySelector('[type="submit"]') : null;

        function resetUI() {
            if (errorEl) {
                errorEl.classList.add("d-none");
                errorEl.textContent = "";
            }
            if (teachersWrapEl) teachersWrapEl.classList.add("d-none");
            if (emptyEl) emptyEl.classList.add("d-none");
            if (teachersListEl) teachersListEl.innerHTML = "";
            if (loadingEl) loadingEl.classList.remove("d-none");
            if (submitBtn) submitBtn.disabled = true;
        }

        function renderTeacherItem(t) {
            const guestBadge = t.is_guest
                ? '<span class="badge bg-light text-muted border ms-2">host</span>'
                : "";

            const studentBadge = t.student_id
                ? '<span class="badge bg-info text-dark ms-2">student</span>'
                : "";

            return `
        <div class="list-group-item d-flex justify-content-between align-items-center">
          <div class="fw-semibold">${t.full_name || "—"}${guestBadge}${studentBadge}</div>
          <span class="text-muted small">${t.hour_donation}h</span>
        </div>
      `;
        }

        async function loadTeachers() {
            const ensembleId = modalEl.dataset.ensembleId;
            const prevSemesterId = modalEl.dataset.prevSemesterId;

            if (!ensembleId || !prevSemesterId) {
                throw new Error("Chybí ensemble_id nebo prev_semester_id na modalu.");
            }

            const url = `/api/ensemble/${ensembleId}/teachers/semester/${prevSemesterId}`;
            const resp = await fetch(url, {headers: {Accept: "application/json"}});
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        }

        modalEl.addEventListener("shown.bs.modal", async () => {
            resetUI();

            try {
                const data = await loadTeachers();
                const teachers = data.teachers || [];

                if (loadingEl) loadingEl.classList.add("d-none");

                if (!teachers.length) {
                    if (emptyEl) emptyEl.classList.remove("d-none");
                    if (submitBtn) submitBtn.disabled = true;
                    return;
                }

                if (teachersListEl) {
                    teachersListEl.innerHTML = teachers.map(renderTeacherItem).join("");
                }
                if (teachersWrapEl) teachersWrapEl.classList.remove("d-none");
                if (submitBtn) submitBtn.disabled = false;
            } catch (e) {
                if (loadingEl) loadingEl.classList.add("d-none");
                if (errorEl) {
                    errorEl.classList.remove("d-none");
                    errorEl.textContent = `Nepodařilo se načíst pedagogy. (${e.message})`;
                }
                if (submitBtn) submitBtn.disabled = true;
            }
        });
    });
})();
