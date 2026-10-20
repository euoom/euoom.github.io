document.addEventListener("DOMContentLoaded", () => {
  const state = { posts: [], query: "" };
  const $ = (selector) => document.querySelector(selector);
  const els = {
    search: $("#search-input"), count: $("#post-count"), theme: $("#theme-toggle"),
    groups: { projects: $("#projects-grid"), weekly: $("#weekly-grid"), notes: $("#notes-grid") },
    groupCounts: { projects: $("#projects-count"), weekly: $("#weekly-count"), notes: $("#notes-count") }
  };

  const escapeHtml = (value = "") => String(value).replace(/[&<>'\"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '\"': "&quot;"
  })[char]);

  const formatDate = (value) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return value || "";
    return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(`${value}T00:00:00`));
  };

  function setTheme(theme) {
    document.documentElement.dataset.theme = theme;
    els.theme.textContent = theme === "dark" ? "☀" : "☾";
    els.theme.setAttribute("aria-label", theme === "dark" ? "라이트 테마로 변경" : "다크 테마로 변경");
    localStorage.setItem("theme", theme);
  }

  const preferred = localStorage.getItem("theme") || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  setTheme(preferred);
  els.theme.addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));
  $("#current-year").textContent = new Date().getFullYear();

  function categoryFor(post) {
    if ((post.tags || []).includes("주간회고")) return "weekly";
    if (post.project_url || (post.tags || []).includes("Project")) return "projects";
    return "notes";
  }

  function filteredPosts() {
    const query = state.query.toLocaleLowerCase();
    return state.posts.filter((post) => !query ||
      [post.title, post.summary, ...(post.tags || [])].some((value) =>
        String(value || "").toLocaleLowerCase().includes(query)));
  }

  function postCard(post) {
    return `
      <a class="post-card" href="./post/${post.route.split("/").map(encodeURIComponent).join("/")}/" aria-label="${escapeHtml(post.title)} 읽기">
        <time class="card-date" datetime="${escapeHtml(post.date)}">${escapeHtml(formatDate(post.date))}</time>
        <div>
          <h4 class="card-title">${escapeHtml(post.title)}</h4>
          <p class="card-summary">${escapeHtml(post.summary || "")}</p>
          <div class="card-tags">${(post.tags || []).map((tag) => `<span class="tag-badge">#${escapeHtml(tag)}</span>`).join("")}</div>
        </div>
        <span class="card-arrow" aria-hidden="true">→</span>
      </a>`;
  }

  function renderPosts() {
    const posts = filteredPosts();
    els.count.textContent = `${posts.length} / ${state.posts.length}`;
    for (const category of ["projects", "weekly", "notes"]) {
      const matches = posts.filter((post) => categoryFor(post) === category);
      els.groupCounts[category].textContent = `${matches.length}개`;
      els.groups[category].innerHTML = matches.length
        ? matches.map(postCard).join("")
        : `<div class="empty-state">${state.query ? "검색 결과가 없습니다." : "아직 등록된 글이 없습니다."}</div>`;
    }
  }

  els.search.addEventListener("input", () => { state.query = els.search.value.trim(); renderPosts(); });

  async function init() {
    try {
      const response = await fetch("./posts.json", { cache: "no-cache" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      state.posts = Array.isArray(data) ? data : [];
    } catch (error) {
      console.error("Could not load posts index", error);
      state.posts = [];
    }
    renderPosts();
  }

  init();
});
