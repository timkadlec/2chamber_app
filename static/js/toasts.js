window.showToast = function (message, type = "success") {
    const containerId = "globalToastContainer";

    let container = document.getElementById(containerId);
    if (!container) {
        container = document.createElement("div");
        container.id = containerId;
        container.className = "toast-container position-fixed bottom-0 end-0 p-3";
        container.style.zIndex = 1055;

        document.body.appendChild(container);
    }

    const id = "toast_" + Math.random().toString(36).slice(2);

    const html = `
    <div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert">
      <div class="d-flex">
        <div class="toast-body">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto"
                data-bs-dismiss="toast"></button>
      </div>
    </div>
  `;

    container.insertAdjacentHTML("beforeend", html);

    const el = document.getElementById(id);
    const toast = new bootstrap.Toast(el, {delay: 4000});
    toast.show();

    el.addEventListener("hidden.bs.toast", () => el.remove());
};
document.addEventListener("DOMContentLoaded", () => {
    const msg = sessionStorage.getItem("toast:message");
    const type = sessionStorage.getItem("toast:type") || "success";

    if (msg) {
        sessionStorage.removeItem("toast:message");
        sessionStorage.removeItem("toast:type");
        window.showToast(msg, type);
    }
});