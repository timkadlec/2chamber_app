self.addEventListener('push', function(event) {
    let data = {};
    if (event.data) {
        data = event.data.json();
    }

    const options = {
        body: data.body || 'Máš novou notifikaci!',
        icon: '/static/images/icon-192.png',
        badge: '/static/images/icon-192.png',
        data: data.url || '/',
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'Orchestrální Plánek', options)
    );
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data)
    );
});
