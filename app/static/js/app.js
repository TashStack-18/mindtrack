// Share the browser's UTC offset (minutes) so the server can group entries by
// the user's local calendar day. Contains no personal data.
(function () {
    const offset = -new Date().getTimezoneOffset();
    try {
        document.cookie = 'mt_tz=' + offset + '; path=/; max-age=31536000; samesite=lax';
    } catch (e) { /* cookies disabled: server falls back to UTC */ }
    // Behind Firebase Hosting only the __session cookie reaches the server, so
    // also store the offset in the session once (or when it changes, e.g. travel).
    const known = document.querySelector('meta[name="mt-tz"]')?.content;
    const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
    if (csrf && known !== String(offset) && window.fetch) {
        fetch('/tz', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ offset: offset }),
        }).catch(() => { /* non-essential */ });
    }
})();

document.addEventListener('DOMContentLoaded', () => {
    // Public navbar menu toggle (logged-out pages, small screens)
    const navToggle = document.querySelector('.unauth-nav-toggle');
    const navLinks = document.getElementById('unauth-nav-links');
    if (navToggle && navLinks) {
        const setOpen = (open) => {
            navLinks.classList.toggle('is-open', open);
            navToggle.setAttribute('aria-expanded', String(open));
            navToggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
        };
        navToggle.addEventListener('click', () => setOpen(!navLinks.classList.contains('is-open')));
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && navLinks.classList.contains('is-open')) {
                setOpen(false);
                navToggle.focus();
            }
        });
    }

    // Profile dropdown (logged-in pages). Opening it never navigates anywhere;
    // only the "Log Out" item links to the logout route.
    const profileMenu = document.querySelector('[data-profile-menu]');
    if (profileMenu) {
        const trigger = profileMenu.querySelector('.profile-button');
        const menu = profileMenu.querySelector('.profile-dropdown');
        const items = () => [...menu.querySelectorAll('[role="menuitem"]')];
        const isOpen = () => !menu.hidden;
        const setMenu = (open, focus) => {
            menu.hidden = !open;
            trigger.setAttribute('aria-expanded', String(open));
            if (open && focus) items()[focus === 'last' ? items().length - 1 : 0]?.focus();
        };

        trigger.addEventListener('click', () => setMenu(!isOpen()));
        trigger.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                setMenu(true, e.key === 'ArrowUp' ? 'last' : 'first');
            }
        });
        menu.addEventListener('keydown', (e) => {
            const list = items();
            const i = list.indexOf(document.activeElement);
            if (e.key === 'ArrowDown') { e.preventDefault(); list[(i + 1) % list.length].focus(); }
            if (e.key === 'ArrowUp') { e.preventDefault(); list[(i - 1 + list.length) % list.length].focus(); }
            if (e.key === 'Home') { e.preventDefault(); list[0].focus(); }
            if (e.key === 'End') { e.preventDefault(); list[list.length - 1].focus(); }
            if (e.key === 'Tab') setMenu(false);
        });
        menu.addEventListener('click', (e) => {
            if (e.target.closest('[role="menuitem"]')) setMenu(false);
        });
        document.addEventListener('click', (e) => {
            if (isOpen() && !profileMenu.contains(e.target)) setMenu(false);
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isOpen()) {
                setMenu(false);
                trigger.focus();
            }
        });
    }
});
