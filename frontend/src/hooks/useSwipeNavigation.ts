import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const ROUTES = ['/', '/feed', '/chat', '/groups', '/search', '/friends', '/profile'];

function isInteractiveTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest('input, textarea, select, button, a, [role="button"], [contenteditable="true"]'));
}

export function useSwipeNavigation(enabled: boolean) {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!enabled) return;
    let startX = 0;
    let startY = 0;
    let tracking = false;

    const onTouchStart = (event: TouchEvent) => {
      if (isInteractiveTarget(event.target) || event.touches.length !== 1) return;
      startX = event.touches[0].clientX;
      startY = event.touches[0].clientY;
      tracking = true;
    };

    const onTouchEnd = (event: TouchEvent) => {
      if (!tracking) return;
      tracking = false;
      const touch = event.changedTouches[0];
      const dx = touch.clientX - startX;
      const dy = touch.clientY - startY;
      if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 1.4) return;

      const currentIndex = Math.max(0, ROUTES.indexOf(location.pathname));
      const nextIndex = dx < 0 ? Math.min(ROUTES.length - 1, currentIndex + 1) : Math.max(0, currentIndex - 1);
      const nextPath = ROUTES[nextIndex];
      if (nextPath && nextPath !== location.pathname) {
        navigate(nextPath);
      }
    };

    window.addEventListener('touchstart', onTouchStart, { passive: true });
    window.addEventListener('touchend', onTouchEnd, { passive: true });
    return () => {
      window.removeEventListener('touchstart', onTouchStart);
      window.removeEventListener('touchend', onTouchEnd);
    };
  }, [enabled, location.pathname, navigate]);
}
