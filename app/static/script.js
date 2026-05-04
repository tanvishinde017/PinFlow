/* ════════════════════════════════════════════════════════════════════
   PinFlow AI — Dashboard Script
   Handles all UI interactions: fetch → generate → post flow
   ════════════════════════════════════════════════════════════════════ */

"use strict";

// ── Toast Notification System ─────────────────────────────────────────────────

const Toast = {
  container: null,

  init() {
    this.container = document.getElementById("toast-container");
    // Show any server-side flash messages
    if (window.__flashMessages) {
      window.__flashMessages.forEach(([cat, msg]) => {
        const type = { success: "success", danger: "error", warning: "warning", info: "info" }[cat] || "info";
        this.show(msg, type);
      });
    }
  },

  show(message, type = "info", duration = 4000) {
    const icons = { success: "✓", error: "✕", warning: "⚠", info: "ℹ" };
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || "ℹ"}</span>
      <span class="toast-msg">${message}</span>
    `;
    this.container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add("fade-out");
      toast.addEventListener("animationend", () => toast.remove());
    }, duration);
  },
};


// ── API Helper ───────────────────────────────────────────────────────────────

async function api(endpoint, options = {}) {
  const defaults = {
    headers: { "Content-Type": "application/json" },
    ...options,
  };
  const res = await fetch(endpoint, defaults);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}


// ── Panel Navigation ──────────────────────────────────────────────────────────

function initNavigation() {
  document.querySelectorAll(".nav-item[data-panel]").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const panelId = link.dataset.panel;

      document.querySelectorAll(".nav-item").forEach((el) => el.classList.remove("active"));
      link.classList.add("active");

      document.querySelectorAll(".panel").forEach((p) => {
        p.classList.remove("active");
        p.classList.add("hidden");
      });

      const target = document.getElementById(`panel-${panelId}`);
      if (target) {
        target.classList.remove("hidden");
        target.classList.add("active");
      }

      if (panelId === "history") loadHistory();
    });
  });
}


// ── Step 1: Fetch Product ─────────────────────────────────────────────────────

function initFetch() {
  const btn       = document.getElementById("btn-fetch");
  const urlInput  = document.getElementById("amazon-url");
  const stepProd  = document.getElementById("step-product");
  const stepGen   = document.getElementById("step-generate");
  const stepPost  = document.getElementById("step-post");

  btn.addEventListener("click", async () => {
    const link = urlInput.value.trim();
    if (!link) { Toast.show("Paste an Amazon link first.", "warning"); return; }

    btn.classList.add("loading");
    btn.querySelector("span").textContent = "Fetching…";

    try {
      const data = await api("/api/fetch", {
        method: "POST",
        body: JSON.stringify({ link }),
      });

      window.PF.productData = data;
      window.PF.selectedImage = data.product_image || (data.images && data.images[0]);

      renderProductInfo(data);
      renderImageGrid(data.images, data.product_image);

      stepProd.classList.remove("hidden");
      stepGen.classList.remove("hidden");
      stepPost.classList.add("hidden");  // reset if re-fetching

      Toast.show("Product fetched! Select an image.", "success");
    } catch (err) {
      Toast.show(err.message || "Failed to fetch product.", "error");
    } finally {
      btn.classList.remove("loading");
      btn.querySelector("span").textContent = "Fetch Product";
    }
  });
}


function renderProductInfo(data) {
  const el = document.getElementById("product-info");
  el.innerHTML = `
    ${data.product_image
      ? `<img class="product-thumb" src="${data.product_image}" alt="" loading="lazy" onerror="this.style.display='none'" />`
      : ""}
    <div class="product-meta">
      <p class="product-title">${escHtml(data.title)}</p>
      <p class="product-price">${escHtml(data.price)}</p>
    </div>
  `;
}


function renderImageGrid(images = [], productImage = null) {
  const grid = document.getElementById("image-grid");
  grid.innerHTML = "";

  const all = productImage ? [productImage, ...images.filter((u) => u !== productImage)] : images;

  all.slice(0, 9).forEach((url, idx) => {
    const div = document.createElement("div");
    div.className = "image-option" + (idx === 0 ? " selected" : "");
    div.innerHTML = `<img src="${url}" alt="Option ${idx + 1}" loading="lazy" />`;
    div.addEventListener("click", () => {
      document.querySelectorAll(".image-option").forEach((el) => el.classList.remove("selected"));
      div.classList.add("selected");
      window.PF.selectedImage = url;
      updatePreviewImage(url);
    });
    grid.appendChild(div);
  });

  if (all.length === 0) {
    grid.innerHTML = `<p style="color:var(--text-muted);font-size:.85rem;grid-column:1/-1">No images found. The product image will be used.</p>`;
  }
}


// ── Step 2: Tone + Generate ───────────────────────────────────────────────────

function initGenerate() {
  // Tone selector
  document.querySelectorAll(".tone-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tone-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      window.PF.selectedTone = btn.dataset.tone;
    });
  });

  // Generate button
  document.getElementById("btn-generate").addEventListener("click", async () => {
    if (!window.PF.productData) { Toast.show("Fetch a product first.", "warning"); return; }

    const btn = document.getElementById("btn-generate");
    btn.classList.add("loading");
    btn.querySelector("span").textContent = "Generating…";

    try {
      const content = await api("/api/generate", {
        method: "POST",
        body: JSON.stringify({
          title: window.PF.productData.title,
          price: window.PF.productData.price,
          tone:  window.PF.selectedTone,
        }),
      });

      window.PF.generatedContent = content;
      renderContentEditor(content);
      document.getElementById("step-post").classList.remove("hidden");
      loadBoards();
      Toast.show("AI content generated! Review and post.", "success");
    } catch (err) {
      Toast.show(err.message || "AI generation failed.", "error");
    } finally {
      btn.classList.remove("loading");
      btn.querySelector("span").textContent = "Generate with AI";
    }
  });
}


function renderContentEditor(content) {
  // Titles
  const titlesList = document.getElementById("titles-list");
  titlesList.innerHTML = "";
  (content.titles || []).forEach((t, i) => {
    const div = createVariantItem(t, i === 0, () => {
      document.getElementById("selected-title").value = t;
      updatePreviewTitle(t);
    });
    titlesList.appendChild(div);
  });

  // Descriptions
  const descList = document.getElementById("descriptions-list");
  descList.innerHTML = "";
  (content.descriptions || []).forEach((d, i) => {
    const div = createVariantItem(d, i === 0, () => {
      document.getElementById("selected-description").value = d;
      updatePreviewDesc(d);
    });
    descList.appendChild(div);
  });

  // Pre-fill fields with first option
  const firstTitle = (content.titles || [])[0] || "";
  const firstDesc  = (content.descriptions || [])[0] || "";
  document.getElementById("selected-title").value       = firstTitle;
  document.getElementById("selected-description").value = firstDesc;
  document.getElementById("selected-hashtags").value    = content.hashtags || "";

  // Live preview updates
  document.getElementById("selected-title").addEventListener("input", (e) => updatePreviewTitle(e.target.value));
  document.getElementById("selected-description").addEventListener("input", (e) => updatePreviewDesc(e.target.value));
  document.getElementById("selected-hashtags").addEventListener("input", (e) => updatePreviewTags(e.target.value));

  // Initial preview
  updatePreviewTitle(firstTitle);
  updatePreviewDesc(firstDesc);
  updatePreviewTags(content.hashtags || "");
  updatePreviewImage(window.PF.selectedImage || "");
}


function createVariantItem(text, selectedByDefault, onSelect) {
  const div = document.createElement("div");
  div.className = "variant-item" + (selectedByDefault ? " selected" : "");
  div.textContent = text;
  div.addEventListener("click", () => {
    div.closest(".variant-list").querySelectorAll(".variant-item").forEach((el) => el.classList.remove("selected"));
    div.classList.add("selected");
    onSelect();
  });
  return div;
}


// ── Preview ────────────────────────────────────────────────────────────────────

function updatePreviewImage(url) {
  const img = document.getElementById("preview-image");
  if (img && url) img.src = url;
}

function updatePreviewTitle(text) {
  const el = document.getElementById("preview-title");
  if (el) el.textContent = text;
}

function updatePreviewDesc(text) {
  const el = document.getElementById("preview-desc");
  if (el) el.textContent = text;
}

function updatePreviewTags(text) {
  const el = document.getElementById("preview-tags");
  if (el) el.textContent = text;
}


// ── Boards ────────────────────────────────────────────────────────────────────

async function loadBoards() {
  if (!window.PF.pinterestConnected) return;

  const sel = document.getElementById("board-select");
  sel.innerHTML = `<option value="">Loading boards…</option>`;

  try {
    const data = await api("/api/boards");
    sel.innerHTML = `<option value="">— Select a board —</option>`;
    (data.boards || []).forEach((b) => {
      const opt = document.createElement("option");
      opt.value       = b.id;
      opt.textContent = `${b.name} (${b.pin_count || 0} pins)`;
      sel.appendChild(opt);
    });
  } catch (err) {
    sel.innerHTML = `<option value="">Failed to load boards</option>`;
    Toast.show("Could not load boards: " + err.message, "error");
  }
}


function initBoardRefresh() {
  document.getElementById("btn-refresh-boards")?.addEventListener("click", async () => {
    try {
      await api("/api/boards/refresh", { method: "POST" });
      await loadBoards();
      Toast.show("Boards refreshed!", "success");
    } catch (err) {
      Toast.show("Refresh failed: " + err.message, "error");
    }
  });
}


// ── Step 3: Post Pin ─────────────────────────────────────────────────────────

function initPost() {
  document.getElementById("btn-post").addEventListener("click", async () => {
    if (!window.PF.pinterestConnected) {
      Toast.show("Connect your Pinterest account first.", "warning");
      return;
    }

    const boardId = document.getElementById("board-select").value;
    const boardName = document.getElementById("board-select").selectedOptions[0]?.text || "";
    const title       = document.getElementById("selected-title").value.trim();
    const description = document.getElementById("selected-description").value.trim();
    const hashtags    = document.getElementById("selected-hashtags").value.trim();
    const imageUrl    = window.PF.selectedImage;

    if (!title)   { Toast.show("Please enter a title.", "warning"); return; }
    if (!boardId) { Toast.show("Please select a Pinterest board.", "warning"); return; }
    if (!imageUrl){ Toast.show("Please select an image.", "warning"); return; }

    const btn = document.getElementById("btn-post");
    btn.classList.add("loading");
    btn.querySelector("span").textContent = "Posting…";

    try {
      const result = await api("/api/post-pin", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          hashtags,
          tone:           window.PF.selectedTone,
          image_url:      imageUrl,
          affiliate_link: window.PF.productData?.link || "",
          board_id:       boardId,
          board_name:     boardName.split(" (")[0],
          product_title:  window.PF.productData?.title || "",
          product_price:  window.PF.productData?.price || "",
        }),
      });

      Toast.show("🎉 Pin queued for posting!", "success");
    } catch (err) {
      Toast.show(err.message || "Post failed.", "error");
    } finally {
      btn.classList.remove("loading");
      btn.querySelector("span").textContent = "Post to Pinterest";
    }
  });
}


// ── History ──────────────────────────────────────────────────────────────────

async function loadHistory() {
  const grid = document.getElementById("history-grid");
  grid.innerHTML = `<div class="loading-state"><span class="spinner"></span>Loading…</div>`;

  try {
    const data = await api("/api/history");
    const pins = data.pins || [];

    if (pins.length === 0) {
      grid.innerHTML = `<div class="empty-state">No pins yet. Create your first one!</div>`;
      return;
    }

    grid.innerHTML = "";
    pins.forEach((pin) => {
      const card = createHistoryCard(pin);
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<div class="empty-state">Failed to load history.</div>`;
  }
}


function createHistoryCard(pin) {
  const card = document.createElement("div");
  card.className = "history-card";

  const imgSrc   = pin.image_url || "https://picsum.photos/seed/42/600/800";
  const date     = pin.created_at ? new Date(pin.created_at).toLocaleDateString() : "";
  const badgeCls = { posted: "badge-posted", draft: "badge-draft", failed: "badge-failed" }[pin.status] || "badge-draft";

  card.innerHTML = `
    <img src="${escHtml(imgSrc)}" alt="" loading="lazy" onerror="this.src='https://picsum.photos/seed/42/600/800'" />
    <div class="history-card-body">
      <p class="history-card-title">${escHtml(pin.title || "Untitled")}</p>
      <p class="history-card-desc">${escHtml((pin.description || "").substring(0, 80))}…</p>
      <div class="history-card-meta">
        <span class="badge ${badgeCls}">${pin.status || "draft"}</span>
        <span class="history-date">${date}</span>
      </div>
    </div>
  `;
  return card;
}


// ── Utils ─────────────────────────────────────────────────────────────────────

function escHtml(str) {
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(String(str || "")));
  return d.innerHTML;
}


// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  Toast.init();
  initNavigation();
  initFetch();
  initGenerate();
  initPost();
  initBoardRefresh();
});
