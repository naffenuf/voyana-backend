import { useEffect } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

/**
 * ScrollRestoration component that implements proper scroll behavior:
 * - Forward navigation (PUSH/REPLACE): Scroll to top
 * - Back/forward navigation (POP): Restore previous scroll position
 */
export function ScrollRestoration() {
  const location = useLocation();
  const navigationType = useNavigationType();

  useEffect(() => {
    // Generate a unique key for this location
    const locationKey = location.key || 'default';

    if (navigationType === 'POP') {
      // Restore scroll position for back/forward navigation
      const savedPosition = sessionStorage.getItem(`scroll-${locationKey}`);
      if (savedPosition) {
        const { x, y } = JSON.parse(savedPosition);
        window.scrollTo(x, y);
      }
    } else {
      // Scroll to top for new navigation (PUSH/REPLACE)
      window.scrollTo(0, 0);
    }

    // Save scroll position before navigating away
    const saveScrollPosition = () => {
      sessionStorage.setItem(
        `scroll-${locationKey}`,
        JSON.stringify({ x: window.scrollX, y: window.scrollY })
      );
    };

    // Save scroll position on scroll events (debounced via timeout)
    let scrollTimeout: number;
    const handleScroll = () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = window.setTimeout(saveScrollPosition, 100);
    };

    window.addEventListener('scroll', handleScroll);

    // Cleanup
    return () => {
      window.removeEventListener('scroll', handleScroll);
      clearTimeout(scrollTimeout);
      saveScrollPosition(); // Save one final time on unmount
    };
  }, [location, navigationType]);

  return null;
}
