// Insights page: mood chart (Chart.js) and the Mood × Context filter.
(function () {
    const MOOD_NAMES = { 1: 'Very Low', 2: 'Low', 3: 'Okay', 4: 'Good', 5: 'Great' };
    const COLORS = { good: '#5fb895', okay: '#e7b84a', low: '#8f7ad8' };
    const groupOf = (v) => (v >= 3.5 ? 'good' : v >= 2.5 ? 'okay' : 'low');

    // --- Chart -----------------------------------------------------------------
    const dataEl = document.getElementById('mood-series');
    const canvas = document.getElementById('moodChart');
    if (dataEl && canvas) {
        const series = JSON.parse(dataEl.textContent);
        if (typeof window.Chart === 'undefined') {
            canvas.hidden = true;
            canvas.parentElement.querySelector('.in-chart-fallback').hidden = false;
        } else {
            const values = series.map((p) => p.value); // null = no check-in (left as a gap)
            const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
            new window.Chart(canvas, {
                type: 'line',
                data: {
                    labels: series.map((p) => p.short),
                    datasets: [{
                        label: 'Recorded mood',
                        data: values,
                        spanGaps: false,
                        tension: 0.3,
                        borderColor: '#a593e6',
                        borderWidth: 2.5,
                        pointRadius: values.map((v) => (v === null ? 0 : 6)),
                        pointHoverRadius: 8,
                        pointBorderWidth: 2,
                        pointBackgroundColor: '#fff',
                        pointBorderColor: values.map((v) => (v === null ? 'transparent' : COLORS[groupOf(v)])),
                        fill: { target: 'origin', above: 'rgba(165, 147, 230, 0.10)' },
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: reduce ? false : { duration: 400 },
                    scales: {
                        y: {
                            min: 0.6, max: 5.4,
                            ticks: { stepSize: 1, callback: (v) => MOOD_NAMES[v] || '', color: '#7a7899', font: { size: 12 } },
                            grid: { color: '#f0ecf7' },
                        },
                        x: { ticks: { color: '#7a7899', autoSkip: true, maxRotation: 0, font: { size: 12 } }, grid: { display: false } },
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#2f2a4a',
                            padding: 10,
                            callbacks: {
                                title: (items) => series[items[0].dataIndex].label,
                                label: (item) => {
                                    const p = series[item.dataIndex];
                                    const lines = [`Mood: ${p.moods.join(', ')}`];
                                    if (p.count > 1) lines.push(`${p.count} check-ins (average ${p.value})`);
                                    if (p.contexts.length) lines.push(`Contexts: ${p.contexts.join(', ')}`);
                                    return lines;
                                },
                            },
                        },
                    },
                },
            });
        }
    }

    // --- Mood × Context filter --------------------------------------------------
    const filter = document.querySelector('.mt-filter');
    if (filter) {
        const cards = [...document.querySelectorAll('.in-ctx')];
        const empty = document.querySelector('.in-matrix-empty');
        const names = { good: 'Good or Great', okay: 'Okay', low: 'Low or Very Low' };
        filter.addEventListener('click', (e) => {
            const btn = e.target.closest('button[data-filter]');
            if (!btn) return;
            const group = btn.dataset.filter;
            filter.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
            let visible = 0;
            cards.forEach((card) => {
                const show = group === 'all' || Number(card.dataset[group]) > 0;
                card.hidden = !show;
                if (show) visible += 1;
                card.querySelectorAll('.in-ctx-row').forEach((row) => {
                    row.classList.toggle('is-dim', group !== 'all' && row.dataset.group !== group);
                });
            });
            empty.hidden = visible > 0;
            empty.textContent = visible ? '' : `No entries with a context were recorded as ${names[group]} in this period.`;
        });
    }
})();
