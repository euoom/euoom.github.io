document.addEventListener("DOMContentLoaded", async () => {
  const root = document.documentElement;
  const toggle = document.querySelector("#theme-toggle");

  function setTheme(theme) {
    root.dataset.theme = theme;
    if (toggle) {
      toggle.textContent = theme === "dark" ? "☀" : "☾";
      toggle.setAttribute("aria-label", theme === "dark" ? "라이트 테마로 변경" : "다크 테마로 변경");
    }
    localStorage.setItem("theme", theme);
  }

  const preferred = localStorage.getItem("theme") || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
  setTheme(preferred);
  toggle?.addEventListener("click", () => setTheme(root.dataset.theme === "dark" ? "light" : "dark"));

  if (window.Prism) Prism.highlightAll();
  if (window.mermaid) {
    mermaid.initialize({ startOnLoad: false, theme: root.dataset.theme === "dark" ? "dark" : "default" });
    const nodes = document.querySelectorAll(".mermaid");
    if (nodes.length) await mermaid.run({ nodes });
  }
});
