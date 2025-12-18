document.addEventListener("DOMContentLoaded", () => {
  const toggles = document.querySelectorAll("[data-toggle]");
  toggles.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.querySelector(btn.dataset.toggle);
      if (target) {
        target.classList.toggle("hidden");
        btn.querySelector(".icon").classList.toggle("rotate-90");
      }
    });
  });

  const editor = document.querySelector("#editor");
  const preview = document.querySelector("#preview");
  if (editor && preview && window.markdownit) {
    const md = window.markdownit({
      html: true,
      linkify: true,
      typographer: true,
    });
    const render = () => {
      preview.innerHTML = md.render(editor.value);
      if (window.mermaid) {
        window.mermaid.init(undefined, document.querySelectorAll(".language-mermaid"));
      }
      if (window.hljs) {
        document.querySelectorAll("pre code").forEach((block) => window.hljs.highlightElement(block));
      }
    };
    editor.addEventListener("input", render);
    render();
  }
});
