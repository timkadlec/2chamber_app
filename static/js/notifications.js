document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.mark-as-read-btn').forEach(button => {
        button.addEventListener('click', () => {
            const notifId = button.getAttribute('data-id');
            fetch('/api/mark-read', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notif_id: notifId })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const notifElement = document.getElementById('notif-' + notifId);
                        if (notifElement) {
                            notifElement.remove();
                        }
                    }
                })
                .catch(error => console.error('Error:', error));
        });
    });
});
