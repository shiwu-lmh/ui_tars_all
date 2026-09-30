const state = { people: [] };

const byId = (id) => document.getElementById(id);

function showResults(query) {
  const normalized = query.trim().toLowerCase();
  const matches = state.people.filter((person) =>
    !normalized || person.name.toLowerCase().includes(normalized) || person.patient_id.toLowerCase().includes(normalized),
  );
  const results = byId('results');
  results.replaceChildren();
  if (!matches.length) {
    results.textContent = '没有找到演示数据。';
    return;
  }
  matches.forEach((person) => {
    const card = document.createElement('article');
    card.className = 'result-card';
    const text = document.createElement('div');
    const title = document.createElement('h3');
    title.textContent = person.name;
    const meta = document.createElement('p');
    meta.className = 'meta';
    meta.textContent = `${person.patient_id} · ${person.records.length} 份演示记录`;
    text.append(title, meta);
    const button = document.createElement('button');
    button.textContent = '打开记录';
    button.addEventListener('click', () => showDetails(person));
    card.append(text, button);
    results.append(card);
  });
}

function showDetails(person) {
  const details = byId('details');
  details.replaceChildren();
  details.classList.remove('hidden');
  const banner = document.createElement('p');
  banner.className = 'demo-banner';
  banner.textContent = '演示数据：以下内容全部虚构，仅用于本地测试。';
  const title = document.createElement('h2');
  title.textContent = `${person.name}（${person.patient_id}）`;
  const meta = document.createElement('p');
  meta.className = 'meta';
  meta.textContent = `出生日期：${person.birth_date}`;
  const list = document.createElement('div');
  list.className = 'record-list';
  person.records.forEach((record) => {
    const card = document.createElement('article');
    card.className = 'record-card';
    const heading = document.createElement('h3');
    heading.textContent = `${record.title} · ${record.date} · ${record.record_id}`;
    card.append(heading);
    record.sections.forEach((section) => {
      const paragraph = document.createElement('p');
      paragraph.textContent = section;
      card.append(paragraph);
    });
    list.append(card);
  });
  details.append(banner, title, meta, list);
  details.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

byId('login-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const valid = byId('username').value === 'demo' && byId('password').value === 'demo';
  byId('login-error').textContent = valid ? '' : '演示账号或密码错误。';
  if (valid) {
    byId('login-panel').classList.add('hidden');
    byId('app-panel').classList.remove('hidden');
    showResults('');
  }
});

byId('search-button').addEventListener('click', () => showResults(byId('search-input').value));
byId('search-input').addEventListener('keydown', (event) => {
  if (event.key === 'Enter') showResults(event.currentTarget.value);
});
byId('logout-button').addEventListener('click', () => window.location.reload());

fetch('data.json')
  .then((response) => response.json())
  .then((people) => { state.people = people; })
  .catch(() => { byId('login-error').textContent = '演示数据加载失败，请确认使用了启动脚本。'; });
