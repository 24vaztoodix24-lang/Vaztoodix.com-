(function () {
  const PAGE_SLUGS = {
    index: "index.html",
    accueil: "index.html",
    mods: "mods.html",
    outils: "outils.html",
    switch: "switch.html",
    "lua-cheats": "lua-cheats.html",
    termux: "termux.html",
    linux: "linux.html",
    ia: "ia.html",
    ides: "ides.html"
  };

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Nettoie l'URL dans la barre d'adresse pour masquer .html lors du filtrage
  function setCleanCategoryUrl(catLabel) {
    const url = new URL(window.location.href);
    url.pathname = url.pathname.replace(/\/[^/]*\.html$/i, "/");
    if (!catLabel || catLabel.toLowerCase() === "toutes") {
      url.searchParams.delete("cat");
    } else {
      url.searchParams.set("cat", catLabel);
    }
    window.history.pushState({ cat: catLabel || "Toutes" }, "", url.toString());
  }

  // Intercepte les liens internes *.html pour naviguer sans afficher .html si possible
  function bindCleanNavLinks() {
    document.querySelectorAll("a[href]").forEach((link) => {
      const href = link.getAttribute("href");
      if (!href || href.startsWith("http") || href.startsWith("#") || href.startsWith("mailto:")) {
        return;
      }
      const match = href.match(/^([a-z0-9-]+)\.html([?#].*)?$/i);
      if (match) {
        const slug = match[1].toLowerCase();
        if (PAGE_SLUGS[slug] && slug !== "index" && slug !== "accueil") {
          link.addEventListener("click", (e) => {
            // Si on est déjà sur la page avec le conteneur dynamique, on filtre sur place sans .html
            if (document.getElementById("dynamicModsContainer")) {
              e.preventDefault();
              const label = link.textContent.trim() || slug;
              setCleanCategoryUrl(label);
              window.renderDynamicMods({ filterCategory: label });
            }
          });
        }
      }
    });
  }

  function openModInRightPanel(mod) {
    const pub = mod.publication || {};
    const payload = {
      title: pub.titre || mod.jeu || mod.id || "Sans titre",
      description: mod.explication || "",
      wiki: mod.wiki || "",
      tags: [mod.categorie, mod.sous_categorie, mod.jeu, pub.type].filter(Boolean),
      url: pub.lien || "",
      date: pub.date_ajout || ""
    };

    if (typeof window.showDetail === "function") {
      window.showDetail(payload);
      return;
    }

    const panel = document.getElementById("rightPanel");
    const detailBox = document.getElementById("detailContent");
    if (panel) panel.classList.remove("collapsed");
    if (detailBox) {
      const tagsHtml = payload.tags
        .map(
          (t) =>
            `<span style="display:inline-block;padding:3px 8px;margin:0 6px 6px 0;border-radius:6px;background:rgba(255,215,0,0.12);border:1px solid rgba(255,215,0,0.35);color:#ffd700;font-size:12px;">${escapeHtml(t)}</span>`
        )
        .join("");

      detailBox.innerHTML = `
        <h2 style="margin-top:0;color:#ffd700;">${escapeHtml(payload.title)}</h2>
        <div style="margin-bottom:12px;">${tagsHtml}</div>
        <p style="line-height:1.55;">${escapeHtml(payload.description)}</p>
        ${
          payload.wiki
            ? `<div class="wiki-box" style="margin:14px 0;padding:12px;border-radius:8px;background:rgba(15,15,25,0.85);border:1px solid rgba(189,147,249,0.35);"><strong>Wiki &amp; Compatibilité :</strong><br>${escapeHtml(payload.wiki)}</div>`
            : ""
        }
        ${
          payload.date
            ? `<p style="font-size:12px;opacity:0.75;">Ajouté le : ${escapeHtml(payload.date)}</p>`
            : ""
        }
        ${
          payload.url
            ? `<a href="${escapeHtml(payload.url)}" target="_blank" rel="noopener noreferrer" style="display:inline-block;margin-top:10px;padding:10px 16px;border-radius:8px;background:linear-gradient(135deg,#ffd700,#ffb300);color:#0a0a0f;font-weight:700;text-decoration:none;">Ouvrir la ressource ↗</a>`
            : ""
        }
      `;
    }
  }

  window.renderDynamicMods = async function ({
    containerId = "dynamicModsContainer",
    filterCategory = null,
    showFilterBar = true
  } = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let items = [];
    try {
      const res = await fetch("data/mods.json?cb=" + Date.now());
      const json = await res.json();
      items = Array.isArray(json) ? json : json.mods || [];
    } catch (err) {
      console.error("Erreur chargement data/mods.json :", err);
      container.innerHTML = `<p style="color:#ff5555;">Impossible de charger data/mods.json.</p>`;
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const hashCat = window.location.hash ? decodeURIComponent(window.location.hash.slice(1)) : "";
    const activeCat = (filterCategory || params.get("cat") || hashCat || "Toutes").trim();

    container.innerHTML = "";

    // Barre de filtres par catégorie (sans .html dans l'URL)
    if (showFilterBar && items.length > 0) {
      const categories = ["Toutes", ...Array.from(new Set(items.map((m) => m.categorie).filter(Boolean)))];
      const navBar = document.createElement("div");
      navBar.style.cssText = "display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 18px 0;";

      categories.forEach((cat) => {
        const isActive = cat.toLowerCase() === activeCat.toLowerCase();
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = cat;
        btn.style.cssText = `
          padding: 6px 12px;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
          font-size: 13px;
          border: 1px solid ${isActive ? "#ffd700" : "rgba(255,215,0,0.3)"};
          background: ${isActive ? "rgba(255,215,0,0.18)" : "rgba(15,15,25,0.85)"};
          color: ${isActive ? "#ffd700" : "#e5e7eb"};
        `;
        btn.addEventListener("click", () => {
          setCleanCategoryUrl(cat);
          window.renderDynamicMods({ containerId, filterCategory: cat, showFilterBar });
        });
        navBar.appendChild(btn);
      });

      container.appendChild(navBar);
    }

    const filtered =
      !activeCat || activeCat.toLowerCase() === "toutes"
        ? items
        : items.filter((m) => (m.categorie || "").toLowerCase() === activeCat.toLowerCase());

    const listToDisplay = filtered.length > 0 ? filtered : items;

    const grid = document.createElement("div");
    grid.style.cssText = "display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;";

    listToDisplay.forEach((mod) => {
      const pub = mod.publication || {};
      const card = document.createElement("div");
      card.className = "card";
      card.style.cursor = "pointer";
      card.innerHTML = `
        <div class="card-meta" style="font-size:12px;color:#ffd700;margin-bottom:6px;">
          ${escapeHtml(mod.categorie || "Général")} • ${escapeHtml(mod.sous_categorie || "Ressource")} • ${escapeHtml(mod.jeu || "")}
        </div>
        <h3 style="margin:0 0 8px 0;">${escapeHtml(pub.titre || mod.jeu || mod.id || "Sans titre")}</h3>
        <p style="margin:0;opacity:0.88;font-size:14px;">${escapeHtml(mod.explication || "")}</p>
      `;
      card.addEventListener("click", () => openModInRightPanel(mod));
      grid.appendChild(card);
    });

    container.appendChild(grid);
  };

  window.addEventListener("popstate", () => {
    window.renderDynamicMods();
  });

  document.addEventListener("DOMContentLoaded", () => {
    bindCleanNavLinks();
    window.renderDynamicMods();
  });
})();
