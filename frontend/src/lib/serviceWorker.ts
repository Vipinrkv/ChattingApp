export function registerServiceWorker() {
  if (!('serviceWorker' in navigator) || !import.meta.env.PROD) return;

  const notifyUpdateAvailable = (registration: ServiceWorkerRegistration) => {
    if (registration.waiting) {
      window.dispatchEvent(new CustomEvent('pwa:update-ready'));
    }
  };

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js')
      .then((registration) => {
        notifyUpdateAvailable(registration);

        registration.addEventListener('updatefound', () => {
          const installing = registration.installing;
          installing?.addEventListener('statechange', () => {
            if (installing.state === 'installed' && navigator.serviceWorker.controller) {
              window.dispatchEvent(new CustomEvent('pwa:update-ready'));
            }
          });
        });
      })
      .catch(() => {
        // The app remains usable without service worker support.
      });

    navigator.serviceWorker.addEventListener('message', (event) => {
      if (event.data?.type === 'BACKGROUND_SYNC_READY') {
        window.dispatchEvent(new CustomEvent('pwa:background-sync-ready'));
      }
    });

    navigator.serviceWorker.addEventListener('controllerchange', () => {
      window.location.reload();
    });
  });
}
