(function () {
  "use strict";

  let catalogData = null;
  let activeCategory = "all";
  let activeLanguage = "all";
  let sortMode = "updated";
  let viewMode = "cards";
  let searchQuery = "";

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function initTheme() {
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;
    toggle.addEventListener("click", function () {
      const next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
      localStorage.setItem("sv-theme", next);
      document.documentElement.setAttribute("data-theme", next);
    });
  }

  function renderStats(data) {
    const s = data.stats || {};
    const setText = function (id, val) {
      const el = document.getElementById(id);
      if (el) el.textContent = String(val);
    };

    setText("stat-total", s.total_repos || 0);
    setText("stat-stars", s.total_stars || 0);
    setText("stat-langs", s.total_languages || 0);
    setText("stat-demos", s.live_demos || 0);
    setText("stat-updated", data.updated_date || "-");

    const langs = data.languages || [];
    const bar = document.getElementById("lang-bar");
    const legend = document.getElementById("lang-legend");
    const select = document.getElementById("lang-select");

    if (bar) {
      bar.innerHTML = langs
        .map(function (l) {
          return (
            '<span class="lang-seg" style="width:' +
            l.percentage +
            "%;background:" +
            escapeHtml(l.color) +
            '" title="' +
            escapeHtml(l.language) +
            " (" +
            l.count +
            " repos, " +
            l.percentage +
            '%)"></span>'
          );
        })
        .join("");
    }

    if (legend) {
      legend.innerHTML = langs
        .slice(0, 8)
        .map(function (l) {
          return (
            '<button class="lang-chip" type="button" data-lang="' +
            escapeHtml(l.language) +
            '" aria-pressed="false">' +
            '<span class="lang-dot" style="background:' +
            escapeHtml(l.color) +
            '"></span>' +
            "<span>" +
            escapeHtml(l.language) +
            "</span>" +
            '<span class="lang-pct">' +
            escapeHtml(l.count) +
            "</span>" +
            "</button>"
          );
        })
        .join("");

      legend.querySelectorAll(".lang-chip").forEach(function (btn) {
        btn.addEventListener("click", function () {
          const lang = btn.getAttribute("data-lang");
          activeLanguage = activeLanguage === lang ? "all" : lang;
          syncLanguageUI();
          renderRepos();
        });
      });
    }

    if (select) {
      select.innerHTML =
        '<option value="all">All languages</option>' +
        langs
          .map(function (l) {
            return (
              '<option value="' +
              escapeHtml(l.language) +
              '">' +
              escapeHtml(l.language) +
              " (" +
              l.count +
              ")</option>"
            );
          })
          .join("");
    }
  }

  function syncLanguageUI() {
    const select = document.getElementById("lang-select");
    if (select) select.value = activeLanguage;
    document.querySelectorAll(".lang-chip").forEach(function (chip) {
      chip.setAttribute("aria-pressed", String(chip.getAttribute("data-lang") === activeLanguage));
    });
  }

  function renderCategories(data) {
    const row = document.getElementById("category-row");
    if (!row) return;

    const total = (data.repos || []).length;
    const demoCount = (data.repos || []).filter(function (r) {
      return Boolean(r.demo);
    }).length;

    const buttons = [
      { id: "all", label: "All (" + total + ")" },
      { id: "demos", label: "Live Demos (" + demoCount + ")" }
    ].concat(
      (data.categories || []).map(function (c) {
        return { id: c.name, label: c.name + " (" + c.count + ")" };
      })
    );

    row.innerHTML = buttons
      .map(function (b) {
        return (
          '<button class="cat-btn" type="button" data-cat="' +
          escapeHtml(b.id) +
          '" aria-pressed="' +
          String(b.id === activeCategory) +
          '">' +
          escapeHtml(b.label) +
          "</button>"
        );
      })
      .join("");

    row.querySelectorAll(".cat-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeCategory = btn.getAttribute("data-cat") || "all";
        row.querySelectorAll(".cat-btn").forEach(function (b) {
          b.setAttribute("aria-pressed", String(b === btn));
        });
        renderRepos();
      });
    });
  }

  function getFilteredRepos() {
    const repos = (catalogData && catalogData.repos) || [];
    const q = searchQuery.trim().toLowerCase();

    const filtered = repos.filter(function (repo) {
      if (activeCategory === "demos" && !repo.demo) return false;
      if (activeCategory !== "all" && activeCategory !== "demos" && repo.category !== activeCategory) {
        return false;
      }
      if (activeLanguage !== "all" && repo.language !== activeLanguage) {
        return false;
      }
      if (!q) return true;
      const hay = [
        repo.name,
        repo.description,
        repo.language,
        repo.category,
        (repo.topics || []).join(" ")
      ]
        .join(" ")
        .toLowerCase();
      return hay.indexOf(q) !== -1;
    });

    filtered.sort(function (a, b) {
      if (sortMode === "stars") {
        if (b.stars !== a.stars) return b.stars - a.stars;
        return (b.pushed_at || "").localeCompare(a.pushed_at || "");
      }
      if (sortMode === "name") {
        return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
      }
      const dateCmp = (b.pushed_at || "").localeCompare(a.pushed_at || "");
      if (dateCmp !== 0) return dateCmp;
      return b.stars - a.stars;
    });

    return filtered;
  }

  function renderRepos() {
    const out = document.getElementById("catalog-output");
    const countEl = document.getElementById("results-count");
    const resetBtn = document.getElementById("reset-filters");
    if (!out || !catalogData) return;

    const total = (catalogData.repos || []).length;
    const repos = getFilteredRepos();
    const isFiltered = activeCategory !== "all" || activeLanguage !== "all" || searchQuery.trim() !== "";

    if (countEl) {
      countEl.textContent =
        repos.length === total
          ? "Showing all " + total + " public repositories"
          : "Showing " + repos.length + " of " + total + " repositories";
    }
    if (resetBtn) {
      resetBtn.hidden = !isFiltered;
    }

    if (!repos.length) {
      out.innerHTML =
        '<div class="empty-state">No repositories matched your filters. Try clearing search or resetting filters.</div>';
      return;
    }

    if (viewMode === "table") {
      out.innerHTML =
        '<div class="table-wrap"><table class="repos-table">' +
        "<thead><tr><th>Repository</th><th>Description</th><th>Language</th><th>Category</th><th>Stars</th><th>Updated</th><th>Links</th></tr></thead>" +
        "<tbody>" +
        repos
          .map(function (r) {
            const desc = r.description ? escapeHtml(r.description) : '<span style="color:var(--text-muted)">No description</span>';
            const demo = r.demo
              ? '<a href="' + escapeHtml(r.demo) + '" target="_blank" rel="noopener noreferrer">Demo</a> &middot; '
              : "";
            return (
              "<tr>" +
              '<td><a class="table-repo-link" href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(r.name) + "</a></td>" +
              "<td>" + desc + "</td>" +
              '<td><span class="repo-lang"><span class="lang-dot" style="background:' + escapeHtml(r.language_color) + '"></span>' + escapeHtml(r.language) + "</span></td>" +
              '<td><span class="cat-pill">' + escapeHtml(r.category) + "</span></td>" +
              '<td class="table-num">' + escapeHtml(r.stars) + "</td>" +
              '<td class="table-num">' + escapeHtml(r.pushed_at || "-") + "</td>" +
              '<td class="table-num">' + demo + '<a href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener noreferrer">Code</a></td>' +
              "</tr>"
            );
          })
          .join("") +
        "</tbody></table></div>";
      return;
    }

    out.innerHTML =
      '<div class="repos-grid">' +
      repos
        .map(function (r) {
          const desc = r.description || "Public repository on GitHub.";
          const topicsHtml =
            r.topics && r.topics.length
              ? '<div class="repo-topics">' +
                r.topics
                  .slice(0, 5)
                  .map(function (t) {
                    return '<span class="topic-tag">' + escapeHtml(t) + "</span>";
                  })
                  .join("") +
                "</div>"
              : "";
          const starsHtml = r.stars > 0 ? "<span>&#9733; " + escapeHtml(r.stars) + "</span>" : "";
          const updatedHtml = r.pushed_at ? "<span>" + escapeHtml(r.pushed_at) + "</span>" : "";
          const demoLink = r.demo
            ? '<a href="' + escapeHtml(r.demo) + '" target="_blank" rel="noopener noreferrer">Live Demo &rarr;</a>'
            : "";

          return (
            '<article class="repo-card">' +
            "<div>" +
            '<div class="repo-top">' +
            '<h2 class="repo-name"><a href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(r.name) + "</a></h2>" +
            '<span class="cat-pill">' + escapeHtml(r.category) + "</span>" +
            "</div>" +
            '<p class="repo-desc">' + escapeHtml(desc) + "</p>" +
            topicsHtml +
            "</div>" +
            '<div class="repo-footer">' +
            '<div class="repo-meta">' +
            '<span class="repo-lang"><span class="lang-dot" style="background:' + escapeHtml(r.language_color) + '"></span>' + escapeHtml(r.language) + "</span>" +
            starsHtml +
            updatedHtml +
            "</div>" +
            '<div class="repo-actions">' +
            demoLink +
            '<a href="' + escapeHtml(r.url) + '" target="_blank" rel="noopener noreferrer">Source</a>' +
            "</div>" +
            "</div>" +
            "</article>"
          );
        })
        .join("") +
      "</div>";
  }

  function initControls() {
    const search = document.getElementById("repo-search");
    const langSelect = document.getElementById("lang-select");
    const sortSelect = document.getElementById("sort-select");
    const cardsBtn = document.getElementById("view-cards");
    const tableBtn = document.getElementById("view-table");
    const resetBtn = document.getElementById("reset-filters");

    if (search) {
      search.addEventListener("input", function (e) {
        searchQuery = e.target.value || "";
        renderRepos();
      });
    }

    if (langSelect) {
      langSelect.addEventListener("change", function (e) {
        activeLanguage = e.target.value || "all";
        syncLanguageUI();
        renderRepos();
      });
    }

    if (sortSelect) {
      sortSelect.addEventListener("change", function (e) {
        sortMode = e.target.value || "updated";
        renderRepos();
      });
    }

    if (cardsBtn && tableBtn) {
      cardsBtn.addEventListener("click", function () {
        viewMode = "cards";
        cardsBtn.setAttribute("aria-pressed", "true");
        tableBtn.setAttribute("aria-pressed", "false");
        renderRepos();
      });
      tableBtn.addEventListener("click", function () {
        viewMode = "table";
        cardsBtn.setAttribute("aria-pressed", "false");
        tableBtn.setAttribute("aria-pressed", "true");
        renderRepos();
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        activeCategory = "all";
        activeLanguage = "all";
        searchQuery = "";
        if (search) search.value = "";
        syncLanguageUI();
        document.querySelectorAll(".cat-btn").forEach(function (b) {
          b.setAttribute("aria-pressed", String(b.getAttribute("data-cat") === "all"));
        });
        renderRepos();
      });
    }
  }

  async function init() {
    initTheme();
    initControls();
    try {
      const resp = await fetch("./data/repos.json", { cache: "no-cache" });
      if (!resp.ok) throw new Error("Failed to load data/repos.json");
      catalogData = await resp.json();
      renderStats(catalogData);
      renderCategories(catalogData);
      renderRepos();
    } catch (_err) {
      const out = document.getElementById("catalog-output");
      if (out) {
        out.innerHTML =
          '<div class="empty-state">Unable to load repository data. View directly on <a href="https://github.com/sandeepkv93?tab=repositories">GitHub</a>.</div>';
      }
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
