document.addEventListener("DOMContentLoaded", () => {
    const el = document.querySelector("#teacher_id");
    if (!el) return; // page doesn't have the select

    // Avoid double-initialization (e.g., if you ever re-run scripts)
    if (el.tomselect) return;

    const ts = new TomSelect(el, {
        placeholder: "— Vyberte pedagoga —",
        plugins: {remove_button: {title: "Odebrat"}},
        maxItems: 1,
        allowEmptyOption: true,
        sortField: {field: "text", direction: "asc"},
    });

    ts.clear();
});