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

  const body = document.body;
  const currentPath = body.dataset.currentPath || "";
  const currentType = body.dataset.currentType || "root";
  const menuBtn = document.getElementById("create-menu-btn");
  const menu = document.getElementById("create-menu");
  const modalBackdrop = document.getElementById("modal-backdrop");
  const modalCreate = document.getElementById("modal-create");
  const modalUpload = document.getElementById("modal-upload");
  const createForm = document.getElementById("create-form");
  const uploadForm = document.getElementById("upload-form");
  const createParent = document.getElementById("create-parent");
  const createTitle = document.getElementById("create-title");
  const createName = document.getElementById("create-name");
  const createType = document.getElementById("create-type");
  const createError = document.getElementById("create-error");
  const createGenerate = document.getElementById("create-generate");
  const createNameHint = document.getElementById("create-name-hint");
  const parentSelect = document.getElementById("parent-select");
  const uploadParent = document.getElementById("upload-parent");
  const uploadFile = document.getElementById("upload-file");

  const mdTypes = new Set(["document", "service", "server", "network"]);
  const nameRegex = /^[a-zA-Z0-9_-]+$/;
  const allowedByParent = {
    root: ["company"],
    company: ["dc"],
    dc: ["section", "document", "service", "server", "network"],
    section: ["section", "document", "service", "server", "network"],
  };
  const getDefaultParent = () => {
    if (["document", "service", "server", "network"].includes(currentType) && currentPath.includes("/")) {
      return currentPath.split("/").slice(0, -1).join("/");
    }
    if (["company", "dc", "section"].includes(currentType)) return currentPath;
    return "";
  };

  const hideMenu = () => menu && menu.classList.add("hidden");

  const openModal = (type) => {
    if (!modalBackdrop) return;
    modalBackdrop.classList.remove("hidden");
    modalBackdrop.classList.add("flex");
    if (type === "upload") {
      modalCreate.classList.add("hidden");
      modalUpload.classList.remove("hidden");
    } else {
      modalUpload.classList.add("hidden");
      modalCreate.classList.remove("hidden");
    }
  };

  const closeModal = () => {
    if (!modalBackdrop) return;
    modalBackdrop.classList.add("hidden");
    modalBackdrop.classList.remove("flex");
  };

  const slugify = (text) => {
    if (!text) return "";
    const translitMap = {
      а: "a",
      б: "b",
      в: "v",
      г: "g",
      д: "d",
      е: "e",
      ё: "e",
      ж: "zh",
      з: "z",
      и: "i",
      й: "y",
      к: "k",
      л: "l",
      м: "m",
      н: "n",
      о: "o",
      п: "p",
      р: "r",
      с: "s",
      т: "t",
      у: "u",
      ф: "f",
      х: "h",
      ц: "c",
      ч: "ch",
      ш: "sh",
      щ: "shch",
      ы: "y",
      э: "e",
      ю: "yu",
      я: "ya",
    };
    return text
      .trim()
      .toLowerCase()
      .split("")
      .map((ch) => translitMap[ch] || ch)
      .join("")
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9_-]/g, "")
      .replace(/-+/g, "-");
  };

  const setError = (msg) => {
    if (createError) {
      createError.textContent = msg || "";
      createError.classList.toggle("hidden", !msg);
    }
  };

  const setNameHint = (slug) => {
    if (createNameHint) {
      createNameHint.textContent = slug ? `Будет создано как: ${slug}` : "";
    }
  };

  const applyAllowedTypes = (contextType) => {
    const allowed = allowedByParent[contextType] || [];
    const options = Array.from(createType.options);
    options.forEach((opt) => {
      opt.disabled = !allowed.includes(opt.value);
      opt.classList.toggle("text-slate-600", opt.disabled);
    });
    if (!allowed.includes(createType.value)) {
      createType.value = allowed[0] || "";
    }
    return allowed;
  };

  let currentTree = [];
  let pathTypeMap = new Map();

  const renderSidebar = async () => {
    const container = document.getElementById("sidebar-tree");
    if (!container) return;
    container.innerHTML = '<div class="text-slate-500 text-xs">Загрузка...</div>';
    try {
      const res = await fetch("/api/tree");
      const data = await res.json();
      if (!data.ok) throw new Error("tree fetch error");
      currentTree = data.tree || [];
      pathTypeMap = new Map();
      const renderNodes = (nodes, level = 0) => {
        const items = nodes
          .map((n) => {
            pathTypeMap.set(n.path, n.type);
            const children = n.children && n.children.length ? renderNodes(n.children, level + 1) : "";
            const iconMap = {
              company: "building-2",
              dc: "server",
              section: "folder",
              document: "file-text",
              service: "layers",
              server: "cpu",
              network: "network",
            };
            const icon = iconMap[n.type] || "file-text";
            return `
              <div class="mt-1">
                <a href="/view/${n.path}" class="flex items-center gap-2 px-${level > 0 ? 2 : 0} py-1 rounded hover:bg-slate-900/60">
                  <i data-lucide="${icon}" class="w-4 h-4 text-accent"></i>
                  <span>${n.title}</span>
                  <span class="text-[10px] uppercase text-slate-500 border border-slate-800 px-1 rounded">${n.type}</span>
                </a>
                ${children}
              </div>
            `;
          })
          .join("");
        return `<div class="${level > 0 ? "pl-4 border-l border-slate-800" : ""}">${items}</div>`;
      };
      container.innerHTML = renderNodes(data.tree || []);
      lucide.createIcons();
      buildParentOptions();
    } catch (err) {
      console.error(err);
      container.innerHTML = '<div class="text-rose-400 text-xs">Ошибка загрузки дерева</div>';
    }
  };
  const buildParentOptions = () => {
    if (!parentSelect) return;
    const options = ['<option value="">/ (root)</option>'];
    const walk = (nodes, prefix = "") => {
      nodes.forEach((n) => {
        options.push(`<option value="${n.path}">${prefix}/${n.title}</option>`);
        if (n.children) walk(n.children, `${prefix}/${n.title}`);
      });
    };
    walk(currentTree || []);
    parentSelect.innerHTML = options.join("");
    const def = getDefaultParent();
    parentSelect.value = def;
    createParent.value = def;
  };

  if (menuBtn && menu) {
    menuBtn.addEventListener("click", () => {
      menu.classList.toggle("hidden");
    });
    document.addEventListener("click", (e) => {
      if (!menu.contains(e.target) && e.target !== menuBtn) {
        hideMenu();
      }
    });
  }

  renderSidebar();

  if (createTitle && createName) {
    createTitle.addEventListener("input", () => {
      const slug = slugify(createTitle.value);
      createName.value = slug;
      setNameHint(slug);
    });
    createName.addEventListener("input", () => {
      createName.value = createName.value.replace(/\s+/g, "-");
      setNameHint(createName.value);
    });
  }

  if (createGenerate && createTitle && createName) {
    createGenerate.addEventListener("click", (e) => {
      e.preventDefault();
      const slug = slugify(createTitle.value || createName.value);
      createName.value = slug;
      setNameHint(slug);
      setError("");
    });
  }

  if (parentSelect) {
    parentSelect.addEventListener("change", () => {
      createParent.value = parentSelect.value;
      contextAllowedTypes(parentSelect.value);
    });
  }

  const contextAllowedTypes = (parentPath) => {
    if (!parentPath) return applyAllowedTypes("root");
    const parentType = pathTypeMap.get(parentPath) || (parentPath === currentPath ? currentType : "section");
    return applyAllowedTypes(parentType);
  };

  document.querySelectorAll("[data-create-type]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const type = btn.dataset.createType;
      const defParent = getDefaultParent();
      createParent.value = defParent;
      if (parentSelect) parentSelect.value = defParent;
      createName.value = "";
      createTitle.value = "";
      const allowed = contextAllowedTypes(defParent);
      if (!allowed.includes(type)) {
        setError("Тип недоступен для выбранного узла");
        createType.value = allowed[0] || "";
        openModal("create");
        return;
      }
      createType.value = type;
      setError("");
      hideMenu();
      openModal("create");
    });
  });

  document.querySelectorAll("[data-open-create]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const parentPath = btn.dataset.parent || currentPath;
      const desired = btn.dataset.openCreate || "section";
      createParent.value = parentPath;
      if (parentSelect) parentSelect.value = parentPath;
      createName.value = "";
      createTitle.value = "";
      const allowed = contextAllowedTypes(parentPath);
      if (!allowed.includes(desired)) {
        setError("Тип недоступен для выбранного узла");
        createType.value = allowed[0] || "";
      } else {
        createType.value = desired;
        setError("");
      }
      openModal("create");
    });
  });

  document.querySelectorAll("[data-open-upload]").forEach((btn) => {
    btn.addEventListener("click", () => {
      uploadParent.value = btn.dataset.parent || currentPath;
      uploadFile.value = "";
      openModal("upload");
    });
  });

  document.querySelectorAll("[data-modal-close]").forEach((btn) => btn.addEventListener("click", closeModal));
  const modalClose = document.getElementById("modal-close");
  if (modalClose) modalClose.addEventListener("click", closeModal);

  // Markdown editor preview
  const mdEditor = document.getElementById("editor");
  const mdPreview = document.getElementById("preview");
  if (mdEditor && mdPreview && window.markdownit) {
    const md = window.markdownit({
      html: true,
      linkify: true,
      typographer: true,
    });
    const renderMd = () => {
      mdPreview.innerHTML = md.render(mdEditor.value);
      if (window.mermaid) {
        window.mermaid.init(undefined, mdPreview.querySelectorAll(".language-mermaid"));
      }
      if (window.hljs) {
        mdPreview.querySelectorAll("pre code").forEach((block) => window.hljs.highlightElement(block));
      }
    };
    mdEditor.addEventListener("input", renderMd);
    renderMd();
  }

  if (createForm) {
    createForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      setError("");
      const allowed = contextAllowedTypes(createParent.value);
      if (!createName.value) {
        createName.value = slugify(createTitle.value || "node");
      }
      const nameValue = createName.value.trim();
      if (!nameRegex.test(nameValue)) {
        setError("Используйте латиницу, цифры, - или _ (без пробелов)");
        return;
      }
      if (allowed.length && !allowed.includes(createType.value)) {
        setError("Тип недоступен для выбранного родителя");
        return;
      }
      const typeValue = createType.value;
      const payload = {
        parent: createParent.value || "",
        name: nameValue,
        title: createTitle.value.trim() || nameValue,
        type: typeValue,
      };
      const endpoint = mdTypes.has(typeValue) ? "/api/create-page" : "/api/mkdir";
      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          if (data.detail && typeof data.detail === "object") {
            const msg = data.detail.error || data.detail.message || JSON.stringify(data.detail);
            setError(msg);
          } else if (data.detail) {
            setError(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
          } else if (data.error) {
            setError(data.error);
          } else {
            setError("Ошибка сохранения");
          }
          return;
        }
        closeModal();
        if (data.ok && data.view_url) {
          window.location.href = data.view_url;
        } else {
          window.location.href = data.path ? `/view/${data.path}` : window.location.href;
        }
        renderSidebar();
      } catch (err) {
        console.error(err);
        setError("Ошибка сети. Проверьте подключение.");
      }
    });
  }

  if (uploadForm) {
    uploadForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData();
      formData.append("path", uploadParent.value || currentPath);
      if (uploadFile.files.length === 0) {
        alert("Выберите файл");
        return;
      }
      formData.append("file", uploadFile.files[0]);
      try {
        const res = await fetch("/api/upload", { method: "POST", body: formData });
        if (!res.ok) {
          const data = await res.json();
          alert(data.detail || "Ошибка загрузки");
          return;
        }
        closeModal();
        window.location.reload();
      } catch (err) {
        console.error(err);
        alert("Ошибка сети");
      }
    });
  }

  document.querySelectorAll("[data-trash]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const targetPath = btn.dataset.trash;
      if (!confirm("Переместить в корзину?")) return;
      try {
        const res = await fetch("/api/trash", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: targetPath }),
        });
        if (!res.ok) {
          const data = await res.json();
          alert(data.detail || "Ошибка удаления");
          return;
        }
        window.location.href = "/";
      } catch (err) {
        console.error(err);
        alert("Ошибка сети");
      }
    });
  });

  const snContainer = document.getElementById("service-network");
  if (snContainer) {
    const rowsHolder = document.getElementById("sn-rows");
    const addRowBtn = document.getElementById("add-row");
    const saveBtn = document.getElementById("save-sn");
    const errBox = document.getElementById("sn-error");
    const path = snContainer.dataset.path;
    const renderRows = (rows) => {
      rowsHolder.innerHTML = "";
      rows.forEach((row, idx) => {
        const div = document.createElement("div");
        div.className = "grid grid-cols-6 gap-2 items-center";
        div.innerHTML = `
          <input data-field="name" data-idx="${idx}" value="${row.name || ""}" class="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-sm">
          <input data-field="ip" data-idx="${idx}" value="${row.ip || ""}" class="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-sm">
          <input data-field="mask" data-idx="${idx}" value="${row.mask || ""}" class="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-sm">
          <input data-field="gateway" data-idx="${idx}" value="${row.gateway || ""}" class="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-sm">
          <input data-field="dns" data-idx="${idx}" value="${row.dns || ""}" class="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-sm">
          <button type="button" data-remove="${idx}" class="px-2 py-1 text-xs rounded bg-slate-800 border border-slate-700 text-rose-300 hover:border-rose-400">-</button>
        `;
        rowsHolder.appendChild(div);
      });
      rowsHolder.querySelectorAll("[data-remove]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const idx = Number(btn.dataset.remove);
          rows.splice(idx, 1);
          if (!rows.length) rows.push({ name: "", ip: "", mask: "", gateway: "", dns: "" });
          renderRows(rows);
        });
      });
    };
    let rows = [];
    try {
      rows = JSON.parse(rowsHolder.dataset.rows || "[]");
    } catch {
      rows = [];
    }
    if (!rows.length) rows = [{ name: "", ip: "", mask: "", gateway: "", dns: "" }];
    renderRows(rows);
    addRowBtn.addEventListener("click", () => {
      rows.push({ name: "", ip: "", mask: "", gateway: "", dns: "" });
      renderRows(rows);
    });
    saveBtn.addEventListener("click", async () => {
      errBox.classList.add("hidden");
      const inputs = rowsHolder.querySelectorAll("input");
      const collated = [];
      inputs.forEach((inp) => {
        const idx = Number(inp.dataset.idx);
        const field = inp.dataset.field;
        collated[idx] = collated[idx] || { name: "", ip: "", mask: "", gateway: "", dns: "" };
        collated[idx][field] = inp.value;
      });
      try {
        const res = await fetch("/api/service-network/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path, items: collated }),
        });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          errBox.textContent = data.error || "Не удалось сохранить";
          errBox.classList.remove("hidden");
          return;
        }
        window.location.reload();
      } catch (err) {
        console.error(err);
        errBox.textContent = "Ошибка сети";
        errBox.classList.remove("hidden");
      }
    });
  }
});
