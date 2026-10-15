// Dashboard daily photo: pick the image for the visitor's LOCAL calendar date.
// Same formula as app/services/inspiration_service.py:
//   index = (days since 0001-01-01) % number_of_images
// so the photo is stable all day and changes at local midnight.
(function () {
    const img = document.querySelector('[data-daily-photo]');
    if (!img) return;

    const DAYS_0001_TO_1970 = 719163; // date(1970, 1, 1).toordinal()

    function dayOrdinal(d) {
        return Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000) + DAYS_0001_TO_1970;
    }

    function useFallback() {
        if (img.dataset.failed) {
            img.remove(); // fallback failed too: the card's soft gradient background shows instead
            return;
        }
        img.dataset.failed = '1';
        img.src = img.dataset.fallback;
    }

    img.addEventListener('error', useFallback);
    if (img.complete && img.naturalWidth === 0 && img.getAttribute('src')) useFallback();

    let options = [];
    try { options = JSON.parse(img.dataset.options || '[]'); } catch (e) { return; }
    if (!options.length) return;

    const wanted = img.dataset.staticBase + options[dayOrdinal(new Date()) % options.length];
    if (new URL(wanted, window.location.href).href !== img.src) img.src = wanted;

    // Exposed for testing other dates from the console: MindTrackDailyPhoto.pick(new Date(2026, 0, 1))
    window.MindTrackDailyPhoto = { pick: (d) => options[dayOrdinal(d) % options.length], dayOrdinal };
})();
