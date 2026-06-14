const state = { notices: [], query: "", section: "" };

const fmt = new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" });
const list = document.querySelector("#noticeList");
const stats = document.querySelector("#stats");
const sectionFilter = document.querySelector("#sectionFilter");
const search = document.querySelector("#search");

async function load() {
  const [noticesRes, metaRes] = await Promise.all([fetch("data/notices.json"), fetch("data/meta.json")]);
  state.notices = await noticesRes.json();
  const meta = await metaRes.json();
  document.querySelector("#totalCount").textContent = meta.total_notices;
  document.querySelector("#updatedAt").textContent = `更新于 ${fmt.format(new Date(meta.updated_at))}`;
  renderSections();
  render();
}

function renderSections() {
  const sections = [...new Set(state.notices.map(item => item.section))].sort();
  sectionFilter.innerHTML = `<option value="">全部栏目</option>` + sections.map(section => `<option>${section}</option>`).join("");
}

function filtered() {
  const q = state.query.trim().toLowerCase();
  return state.notices.filter(item => {
    const inSection = !state.section || item.section === state.section;
    const text = `${item.title} ${item.summary} ${item.section}`.toLowerCase();
    return inSection && (!q || text.includes(q));
  });
}

function render() {
  const rows = filtered();
  const sections = new Set(rows.map(item => item.section));
  const latest = rows[0]?.date || "-";
  stats.innerHTML = [
    ["筛选结果", rows.length],
    ["覆盖栏目", sections.size],
    ["最新日期", latest],
    ["历史总量", state.notices.length],
  ].map(([label, value]) => `<article class="stat"><span>${label}</span><strong>${value}</strong></article>`).join("");

  list.innerHTML = rows.map(item => `
    <article class="notice">
      <div class="date">${item.date}</div>
      <div>
        <h2><a href="${item.url}" target="_blank" rel="noreferrer">${item.title}</a></h2>
        <p>${item.summary || "暂无摘要"}</p>
        <div class="meta">
          <span class="pill">${item.section}</span>
          <span class="pill">首次发现 ${item.first_seen_at.slice(0, 10)}</span>
        </div>
      </div>
    </article>
  `).join("") || `<article class="notice"><div class="date">-</div><div><h2>没有匹配结果</h2><p>换一个关键词或栏目试试。</p></div></article>`;
}

search.addEventListener("input", event => { state.query = event.target.value; render(); });
sectionFilter.addEventListener("change", event => { state.section = event.target.value; render(); });

load().catch(error => {
  list.innerHTML = `<article class="notice"><div class="date">!</div><div><h2>数据加载失败</h2><p>${error.message}</p></div></article>`;
});
