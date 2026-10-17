/**
 * app.js - Client-Side Interactivity
 * Phase 3: Social Network Friend Recommendation System
 *
 * Provides:
 * 1. Confirmation Modal Handlers for safe deletions.
 * 2. Flash Alert Dismissal.
 * 3. Client-side Quick Search Filtering.
 * 4. Interactive SVG Graph Network Visualizer (Pure Vanilla JS, zero external dependencies).
 */

document.addEventListener("DOMContentLoaded", function () {
  // -------------------------------------------------------------
  // 1. Flash Alert Dismissal
  // -------------------------------------------------------------
  const alertCloseButtons = document.querySelectorAll(".alert-close");
  alertCloseButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const alert = this.closest(".alert");
      if (alert) {
        alert.style.opacity = "0";
        setTimeout(() => alert.remove(), 150);
      }
    });
  });

  // -------------------------------------------------------------
  // 2. Delete Confirmation Modal
  // -------------------------------------------------------------
  const deleteModal = document.getElementById("deleteConfirmModal");
  const deleteForm = document.getElementById("deleteConfirmForm");
  const deleteTargetName = document.getElementById("deleteTargetName");
  const modalCancelBtns = document.querySelectorAll(".modal-cancel-btn");

  document.querySelectorAll(".btn-trigger-delete").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const targetName = this.getAttribute("data-user-name") || "this item";
      const actionUrl = this.getAttribute("data-action-url");

      if (deleteTargetName) deleteTargetName.textContent = targetName;
      if (deleteForm && actionUrl) deleteForm.setAttribute("action", actionUrl);
      if (deleteModal) deleteModal.classList.add("active");
    });
  });

  modalCancelBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (deleteModal) deleteModal.classList.remove("active");
    });
  });

  // Close modal when clicking on overlay background
  if (deleteModal) {
    deleteModal.addEventListener("click", function (e) {
      if (e.target === deleteModal) {
        deleteModal.classList.remove("active");
      }
    });
  }

  // -------------------------------------------------------------
  // 3. Client-side Quick Search Filtering for Tables
  // -------------------------------------------------------------
  const tableSearchInput = document.getElementById("tableSearchInput");
  if (tableSearchInput) {
    tableSearchInput.addEventListener("input", function () {
      const query = this.value.toLowerCase().trim();
      const rows = document.querySelectorAll(".searchable-table tbody tr");
      rows.forEach(function (row) {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? "" : "none";
      });
    });
  }

  // -------------------------------------------------------------
  // 4. Interactive SVG Network Visualizer
  // -------------------------------------------------------------
  const svgContainer = document.getElementById("networkSvgContainer");
  if (svgContainer) {
    initSvgNetwork(svgContainer);
  }
});

/**
 * Initializes a responsive, interactive SVG graph visualization of the social network.
 */
function initSvgNetwork(container) {
  fetch("/api/graph")
    .then((res) => res.json())
    .then((data) => {
      const nodes = data.nodes || [];
      const edges = data.edges || [];

      if (nodes.length === 0) {
        container.innerHTML =
          '<div class="empty-state"><p>No network members to display.</p></div>';
        return;
      }

      const width = container.clientWidth || 800;
      const height = container.clientHeight || 480;
      const centerX = width / 2;
      const centerY = height / 2;
      const radius = Math.min(width, height) * 0.38;

      // Position nodes in a circular layout
      const nodeMap = {};
      const total = nodes.length;

      nodes.forEach((node, index) => {
        const angle = (2 * Math.PI * index) / total;
        const x = centerX + radius * Math.cos(angle);
        const y = centerY + radius * Math.sin(angle);
        nodeMap[node.id] = { ...node, x, y };
      });

      // Construct SVG DOM elements
      let svgHtml = `<svg width="100%" height="100%" viewBox="0 0 ${width} ${height}" style="user-select: none;">`;

      // Draw Edges
      svgHtml += `<g id="svg-edges">`;
      edges.forEach((edge) => {
        const s = nodeMap[edge.source];
        const t = nodeMap[edge.target];
        if (s && t) {
          svgHtml += `<line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" stroke="#cbd5e1" stroke-width="2" class="graph-edge" data-source="${s.id}" data-target="${t.id}" />`;
        }
      });
      svgHtml += `</g>`;

      // Draw Nodes
      svgHtml += `<g id="svg-nodes">`;
      nodes.forEach((node) => {
        const pos = nodeMap[node.id];
        const initials = node.name
          .split(" ")
          .map((n) => n[0])
          .slice(0, 2)
          .join("")
          .toUpperCase();

        svgHtml += `
          <g class="graph-node-group" data-id="${node.id}" style="cursor: pointer;">
            <circle cx="${pos.x}" cy="${pos.y}" r="22" fill="#eef2ff" stroke="#4f46e5" stroke-width="2.5" class="node-circle" id="circle-${node.id}" />
            <text x="${pos.x}" y="${pos.y + 5}" text-anchor="middle" font-size="11" font-weight="700" fill="#4f46e5" pointer-events="none">${initials}</text>
            <text x="${pos.x}" y="${pos.y + 36}" text-anchor="middle" font-size="12" font-weight="600" fill="#1e293b" pointer-events="none">${escapeHtml(node.name)}</text>
          </g>
        `;
      });
      svgHtml += `</g></svg>`;

      container.innerHTML = svgHtml;

      // Interactivity: Click on node to highlight neighbors & show info
      const infoBox = document.getElementById("networkNodeInfo");
      const nodeGroups = container.querySelectorAll(".graph-node-group");
      const edgeLines = container.querySelectorAll(".graph-edge");

      nodeGroups.forEach((group) => {
        group.addEventListener("click", function () {
          const selectedId = this.getAttribute("data-id");
          const selectedNode = nodeMap[selectedId];

          // Reset all highlights
          container.querySelectorAll(".node-circle").forEach((c) => {
            c.setAttribute("fill", "#eef2ff");
            c.setAttribute("stroke", "#4f46e5");
            c.setAttribute("stroke-width", "2.5");
          });
          edgeLines.forEach((l) => {
            l.setAttribute("stroke", "#cbd5e1");
            l.setAttribute("stroke-width", "2");
          });

          // Highlight selected node
          const circle = container.querySelector(`#circle-${selectedId}`);
          if (circle) {
            circle.setAttribute("fill", "#4f46e5");
            circle.setAttribute("stroke", "#312e81");
            circle.setAttribute("stroke-width", "3.5");
          }

          // Highlight connected edges and direct friends
          const friendIds = new Set();
          edgeLines.forEach((l) => {
            const s = l.getAttribute("data-source");
            const t = l.getAttribute("data-target");
            if (s === selectedId || t === selectedId) {
              l.setAttribute("stroke", "#4f46e5");
              l.setAttribute("stroke-width", "3.5");
              const friendId = s === selectedId ? t : s;
              friendIds.add(friendId);
              const friendCircle = container.querySelector(`#circle-${friendId}`);
              if (friendCircle) {
                friendCircle.setAttribute("fill", "#dcfce7");
                friendCircle.setAttribute("stroke", "#16a34a");
              }
            }
          });

          // Update info display panel
          if (infoBox && selectedNode) {
            infoBox.innerHTML = `
              <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem;">
                <div class="avatar-pill" style="width: 44px; height: 44px; font-size: 1.1rem;">
                  ${selectedNode.name.charAt(0)}
                </div>
                <div>
                  <h4 style="margin: 0; font-size: 1.05rem;">${escapeHtml(selectedNode.name)}</h4>
                  <p style="margin: 0; font-size: 0.85rem; color: #64748b;">${escapeHtml(selectedNode.bio)}</p>
                </div>
              </div>
              <p style="margin: 0 0 0.5rem 0; font-size: 0.88rem;">
                <strong>Direct Connections:</strong> ${selectedNode.degree} friend(s)
              </p>
              <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                <a href="/users/${selectedNode.id}" class="btn btn-primary btn-sm">View Profile</a>
                <a href="/recommendations?user_id=${selectedNode.id}" class="btn btn-secondary btn-sm">View Recommendations</a>
              </div>
            `;
          }
        });
      });
    })
    .catch((err) => {
      console.error("Failed to load graph data:", err);
      container.innerHTML =
        '<div class="empty-state"><p>Unable to load graph data.</p></div>';
    });
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
