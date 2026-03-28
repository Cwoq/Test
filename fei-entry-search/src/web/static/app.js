// Auto-submit filters on change (optional enhancement)
document.querySelectorAll('.filters select').forEach(select => {
    select.addEventListener('change', () => {
        select.closest('form').submit();
    });
});

// Sortable table columns
document.querySelectorAll('.results-table th').forEach((th, index) => {
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => {
        const table = th.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const isNumeric = ['5', '6', '7', '8', '9'].includes(String(index));
        const currentDir = th.dataset.sortDir === 'asc' ? 'desc' : 'asc';

        // Reset all headers
        table.querySelectorAll('th').forEach(h => delete h.dataset.sortDir);
        th.dataset.sortDir = currentDir;

        rows.sort((a, b) => {
            const aText = a.children[index]?.textContent.trim() || '';
            const bText = b.children[index]?.textContent.trim() || '';

            if (isNumeric) {
                const aNum = parseFloat(aText.replace(/[^0-9.-]/g, '')) || 0;
                const bNum = parseFloat(bText.replace(/[^0-9.-]/g, '')) || 0;
                return currentDir === 'asc' ? aNum - bNum : bNum - aNum;
            }
            return currentDir === 'asc'
                ? aText.localeCompare(bText)
                : bText.localeCompare(aText);
        });

        rows.forEach(row => tbody.appendChild(row));
    });
});
