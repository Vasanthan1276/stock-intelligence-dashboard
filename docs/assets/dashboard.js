/* Presentation-only filtering. No requests, score calculations, or persistence. */
(() => {
  const root = document.getElementById('vstock-app');
  if (!root) return;
  const byId = id => document.getElementById(id);
  const company = byId('market-company');
  if (company) {
    const topic = byId('market-topic');
    const cards = Array.from(root.querySelectorAll('[data-market-card]'));
    const sections = Array.from(root.querySelectorAll('[data-topic]'));
    const coverage = Array.from(root.querySelectorAll('[data-coverage-ticker]'));
    function filterMarkets() {
      let visible = 0;
      cards.forEach(card => {
        const matchesCompany = !company.value || card.dataset.companies.split(' ').includes(company.value);
        const matchesTopic = !topic.value || card.closest('[data-topic]').dataset.topic === topic.value;
        card.hidden = !(matchesCompany && matchesTopic);
        if (!card.hidden) visible += 1;
      });
      sections.forEach(section => {
        section.hidden = !Array.from(section.querySelectorAll('[data-market-card]')).some(card => !card.hidden);
      });
      byId('market-count').textContent = `${visible} of ${cards.length} selected markets`;
      byId('market-empty').hidden = visible !== 0;
      const finding = coverage.find(row => row.dataset.coverageTicker === company.value);
      byId('selected-coverage').textContent = finding ? `${company.value}: ${finding.dataset.finding}. Coverage is across all event types.` : '';
    }
    company.addEventListener('change', filterMarkets);
    topic.addEventListener('change', filterMarkets);
    byId('market-reset').addEventListener('click', () => {
      company.value = '';
      topic.value = '';
      filterMarkets();
    });
    filterMarkets();
  }
  const search = byId('stock-search');
  if (search) {
    const market = byId('stock-market');
    const sector = byId('stock-sector');
    const sort = byId('stock-sort');
    const rows = Array.from(root.querySelectorAll('[data-stock-row]'));
    function filterStocks() {
      let visible = 0;
      const query = search.value.trim().toLowerCase();
      rows.forEach(row => {
        row.hidden = !((!query || row.dataset.search.toLowerCase().includes(query)) &&
          (!market.value || row.dataset.market === market.value) &&
          (!sector.value || row.dataset.sector === sector.value));
        if (!row.hidden) visible += 1;
      });
      const ordered = rows.slice().sort((a, b) => sort.value === 'ticker'
        ? a.dataset.ticker.localeCompare(b.dataset.ticker)
        : Number(b.dataset.score) - Number(a.dataset.score) || a.dataset.ticker.localeCompare(b.dataset.ticker));
      ordered.forEach(row => byId('stock-body').appendChild(row));
      byId('stock-count').textContent = visible ? `Showing ${visible} of ${rows.length} stocks` : 'No stocks match these filters.';
    }
    search.addEventListener('input', filterStocks);
    [market, sector, sort].forEach(control => control.addEventListener('change', filterStocks));
    byId('stock-reset').addEventListener('click', () => {
      search.value = market.value = sector.value = '';
      sort.value = 'score';
      filterStocks();
      search.focus();
    });
  }
})();
