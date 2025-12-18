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
  const uploadParent = document.getElementById("upload-parent");
  const uploadFile = document.getElementById("upload-file");

  const mdTypes = new Set(["document", "service", "server", "network"]);
  const nameRegex = /^[a-zA-Z0-9_-]+$/;

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

  if (createTitle && createName) {
    createTitle.addEventListener("input", () => {
      if (!createName.value) {
        createName.value = slugify(createTitle.value);
      }
    });
    createName.addEventListener("input", () => {
      createName.value = createName.value.replace(/\s+/g, "-");
    });
  }

  if (createGenerate && createTitle && createName) {
    createGenerate.addEventListener("click", (e) => {
      e.preventDefault();
      createName.value = slugify(createTitle.value || createName.value);
      setError("");
    });
  }

  document.querySelectorAll("[data-create-type]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const type = btn.dataset.createType;
      createType.value = type;
      createParent.value = currentPath;
      createName.value = "";
      createTitle.value = "";
      setError("");
      hideMenu();
      openModal("create");
    });
  });

  document.querySelectorAll("[data-open-create]").forEach((btn) => {
    btn.addEventListener("click", () => {
      createType.value = btn.dataset.openCreate || "section";
      createParent.value = btn.dataset.parent || currentPath;
      createName.value = "";
      createTitle.value = "";
      setError("");
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

  if (createForm) {
    createForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      setError("");
      const nameValue = createName.value.trim();
      if (!nameRegex.test(nameValue)) {
        setError("Используйте латиницу, цифры, - или _ (без пробелов)");
        return;
      }
      const typeValue = createType.value;
      const payload = {
        parent: createParent.value || "",
        name: nameValue,
        title: createTitle.value.trim() || nameValue,
        type_value: typeValue,
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
});
