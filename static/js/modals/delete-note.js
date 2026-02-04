document.addEventListener("DOMContentLoaded", () => {
    const modalEl = document.getElementById("deleteNoteModal");
    if (!modalEl) return;

    modalEl.addEventListener("show.bs.modal", (event) => {
        const btn = event.relatedTarget; // the clicked delete button
        if (!btn) return;

        const noteText = btn.getAttribute("data-note-text") || "";
        const deleteUrl = btn.getAttribute("data-delete-url") || "";

        modalEl.querySelector("#deleteNoteText").textContent = noteText;
        modalEl.querySelector("#deleteNoteForm").setAttribute("action", deleteUrl);
    });
});