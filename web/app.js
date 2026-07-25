document.addEventListener('DOMContentLoaded', () => {
  let allRepos = [];
  let repoDetailsCache = new Map();
  let selectedRepos = new Set();
  
  let filters = {
    search: '',
    visibility: 'all',
    commits: 'all',
    quick: 'all'
  };

  // DOM Elements
  const userAvatar = document.getElementById('userAvatar');
  const userName = document.getElementById('userName');
  const userLogin = document.getElementById('userLogin');

  const statTotal = document.getElementById('statTotal');
  const statPublic = document.getElementById('statPublic');
  const statPrivate = document.getElementById('statPrivate');
  const statDeployments = document.getElementById('statDeployments');

  const repoTableBody = document.getElementById('repoTableBody');
  const selectAll = document.getElementById('selectAll');
  const bulkBar = document.getElementById('bulkBar');
  const selectedBadge = document.getElementById('selectedBadge');

  const searchInput = document.getElementById('searchInput');
  const btnRefresh = document.getElementById('btnRefresh');

  // Modals
  const modalDesc = document.getElementById('modalDesc');
  const descInput = document.getElementById('descInput');
  const btnCancelDesc = document.getElementById('btnCancelDesc');
  const btnSaveDesc = document.getElementById('btnSaveDesc');

  const modalTopics = document.getElementById('modalTopics');
  const topicsInput = document.getElementById('topicsInput');
  const btnCancelTopics = document.getElementById('btnCancelTopics');
  const btnSaveTopics = document.getElementById('btnSaveTopics');

  const modalDelete = document.getElementById('modalDelete');
  const deleteRepoList = document.getElementById('deleteRepoList');
  const deleteConfirmInput = document.getElementById('deleteConfirmInput');
  const btnCancelDelete = document.getElementById('btnCancelDelete');
  const btnConfirmDelete = document.getElementById('btnConfirmDelete');

  const modalLogs = document.getElementById('modalLogs');
  const logOutput = document.getElementById('logOutput');
  const btnCloseLogs = document.getElementById('btnCloseLogs');

  // Bulk action buttons
  const btnMakePublic = document.getElementById('btnMakePublic');
  const btnMakePrivate = document.getElementById('btnMakePrivate');
  const btnSetDesc = document.getElementById('btnSetDesc');
  const btnSetTopics = document.getElementById('btnSetTopics');
  const btnAddLicense = document.getElementById('btnAddLicense');
  const btnAddReadme = document.getElementById('btnAddReadme');
  const btnDelete = document.getElementById('btnDelete');

  // Initialization
  fetchUser();
  fetchRepos();

  // Listeners
  btnRefresh.addEventListener('click', () => { fetchUser(); fetchRepos(); });

  searchInput.addEventListener('input', (e) => {
    filters.search = e.target.value.toLowerCase();
    renderTable();
  });

  setupPillGroup('filterVisibility', (val) => { filters.visibility = val; renderTable(); });
  setupPillGroup('filterCommits', (val) => { filters.commits = val; renderTable(); });
  setupPillGroup('filterQuick', (val) => { filters.quick = val; renderTable(); });

  selectAll.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    const visibleRepos = getFilteredRepos();
    if (isChecked) {
      visibleRepos.forEach(r => selectedRepos.add(r.name));
    } else {
      visibleRepos.forEach(r => selectedRepos.delete(r.name));
    }
    updateSelectionUI();
    renderTable();
  });

  // Modal Handlers
  btnSetDesc.addEventListener('click', () => { modalDesc.classList.remove('hidden'); });
  btnCancelDesc.addEventListener('click', () => { modalDesc.classList.add('hidden'); });
  btnSaveDesc.addEventListener('click', () => {
    const desc = descInput.value.trim();
    modalDesc.classList.add('hidden');
    descInput.value = '';
    executeAction('/api/actions/description', { repos: Array.from(selectedRepos), description: desc });
  });

  btnSetTopics.addEventListener('click', () => { modalTopics.classList.remove('hidden'); });
  btnCancelTopics.addEventListener('click', () => { modalTopics.classList.add('hidden'); });
  btnSaveTopics.addEventListener('click', () => {
    const raw = topicsInput.value.trim();
    const topics = raw.split(',').map(t => t.trim().toLowerCase()).filter(Boolean);
    modalTopics.classList.add('hidden');
    topicsInput.value = '';
    executeAction('/api/actions/topics', { repos: Array.from(selectedRepos), topics });
  });

  btnMakePublic.addEventListener('click', () => {
    executeAction('/api/actions/visibility', { repos: Array.from(selectedRepos), visibility: 'public' });
  });

  btnMakePrivate.addEventListener('click', () => {
    executeAction('/api/actions/visibility', { repos: Array.from(selectedRepos), visibility: 'private' });
  });

  btnAddLicense.addEventListener('click', () => {
    executeAction('/api/actions/license', { repos: Array.from(selectedRepos) });
  });

  btnAddReadme.addEventListener('click', () => {
    executeAction('/api/actions/readme', { repos: Array.from(selectedRepos) });
  });

  // Delete Handlers
  btnDelete.addEventListener('click', () => {
    deleteRepoList.innerHTML = Array.from(selectedRepos).map(r => `<li>${r}</li>`).join('');
    deleteConfirmInput.value = '';
    btnConfirmDelete.disabled = true;
    modalDelete.classList.remove('hidden');
  });

  deleteConfirmInput.addEventListener('input', (e) => {
    btnConfirmDelete.disabled = e.target.value.trim() !== 'DELETE';
  });

  btnCancelDelete.addEventListener('click', () => { modalDelete.classList.add('hidden'); });

  btnConfirmDelete.addEventListener('click', () => {
    modalDelete.classList.add('hidden');
    executeAction('/api/actions/delete', { repos: Array.from(selectedRepos), confirm: true });
  });

  btnCloseLogs.addEventListener('click', () => {
    modalLogs.classList.add('hidden');
    fetchRepos();
  });

  // Helper Functions
  function setupPillGroup(groupId, callback) {
    const container = document.getElementById(groupId);
    container.addEventListener('click', (e) => {
      if (e.target.tagName === 'BUTTON') {
        container.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        e.target.classList.add('active');
        callback(e.target.dataset.value);
      }
    });
  }

  async function fetchUser() {
    try {
      const res = await fetch('/api/user');
      const user = await res.json();
      if (user.login) {
        userAvatar.src = user.avatar_url || 'https://github.com/github.png';
        userName.textContent = user.name || user.login;
        userLogin.textContent = `@${user.login}`;
      }
    } catch (e) {
      console.error('Failed to fetch user', e);
    }
  }

  async function fetchRepos() {
    repoTableBody.innerHTML = `
      <tr><td colspan="6" class="text-center py-8">
        <p style="text-align:center; padding: 20px; color:#9ca3af;">Loading repositories...</p>
      </td></tr>`;

    try {
      const res = await fetch('/api/repos');
      const data = await res.json();
      allRepos = data.repos || [];
      updateStats();
      renderTable();
      
      // Background progressive fetch for details
      fetchProgressiveDetails();
    } catch (e) {
      repoTableBody.innerHTML = `<tr><td colspan="6" style="color:#ef4444; text-align:center; padding: 20px;">Failed to load repositories.</td></tr>`;
    }
  }

  async function fetchProgressiveDetails() {
    for (const r of allRepos) {
      if (repoDetailsCache.has(r.name)) {
        Object.assign(r, repoDetailsCache.get(r.name));
      } else {
        try {
          const res = await fetch(`/api/repo-details?repo=${r.name}`);
          if (res.ok) {
            const details = await res.json();
            repoDetailsCache.set(r.name, details);
            Object.assign(r, details);
            // Re-render row metrics dynamically
            updateRowMetrics(r.name);
          }
        } catch (e) {}
      }
    }
  }

  function updateRowMetrics(repoName) {
    const r = allRepos.find(item => item.name === repoName);
    if (!r) return;
    
    const commitEl = document.getElementById(`commits-${r.name}`);
    if (commitEl && r.commit_count !== null) {
      commitEl.className = 'badge badge-amber';
      commitEl.textContent = `${r.commit_count} commits`;
    }

    const filesEl = document.getElementById(`files-${r.name}`);
    if (filesEl && r.source_files !== null) {
      filesEl.innerHTML = `<span title="${r.source_files} source files out of ${r.total_files} total workspace files">${r.source_files} / ${r.total_files} files</span>`;
    }

    const docsEl = document.getElementById(`docs-${r.name}`);
    if (docsEl && r.has_readme !== null) {
      docsEl.innerHTML = `
        <span style="color:${r.has_license ? '#34d399' : '#9ca3af'}">📜 ${r.has_license ? 'Yes' : 'No'}</span> | 
        <span style="color:${r.has_readme ? '#34d399' : '#9ca3af'}">📄 ${r.has_readme ? 'Yes' : 'No'}</span>
      `;
    }
  }

  function updateStats() {
    statTotal.textContent = allRepos.length;
    statPublic.textContent = allRepos.filter(r => r.visibility === 'PUBLIC').length;
    statPrivate.textContent = allRepos.filter(r => r.visibility === 'PRIVATE').length;
    statDeployments.textContent = allRepos.filter(r => Boolean(r.homepage)).length;
  }

  function getFilteredRepos() {
    return allRepos.filter(r => {
      if (filters.search) {
        const q = filters.search;
        const matchName = r.name.toLowerCase().includes(q);
        const matchDesc = r.description.toLowerCase().includes(q);
        const matchLang = r.language.toLowerCase().includes(q);
        const matchTopics = (r.topics || []).some(t => t.toLowerCase().includes(q));
        if (!matchName && !matchDesc && !matchLang && !matchTopics) return false;
      }

      if (filters.visibility === 'public' && r.visibility !== 'PUBLIC') return false;
      if (filters.visibility === 'private' && r.visibility !== 'PRIVATE') return false;

      if (r.commit_count !== null) {
        if (filters.commits === 'lt5' && r.commit_count >= 5) return false;
        if (filters.commits === '5to20' && (r.commit_count < 5 || r.commit_count > 20)) return false;
        if (filters.commits === 'gt20' && r.commit_count <= 20) return false;
      }

      if (filters.quick === 'hasDeployment' && !r.homepage) return false;
      if (filters.quick === 'missingReadme' && r.has_readme === true) return false;
      if (filters.quick === 'missingLicense' && r.has_license === true) return false;

      return true;
    });
  }

  function renderTable() {
    const repos = getFilteredRepos();
    if (repos.length === 0) {
      repoTableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#9ca3af; padding: 32px;">No repositories match the selected filters.</td></tr>`;
      return;
    }

    repoTableBody.innerHTML = repos.map(r => {
      const isChecked = selectedRepos.has(r.name);
      const visClass = r.visibility === 'PUBLIC' ? 'badge-public' : 'badge-private';
      const topicsHtml = (r.topics || []).map(t => `<span class="topic-tag">#${t}</span>`).join('');
      const deployHtml = r.homepage ? `<a href="${r.homepage}" target="_blank" class="deploy-link">🔗 ${r.homepage}</a>` : '';
      const dateHtml = r.pushed_at ? `<span class="date-tag">📅 ${r.pushed_at}</span>` : '';

      const commitBadge = r.commit_count !== null 
        ? `<span id="commits-${r.name}" class="badge badge-amber">${r.commit_count} commits</span>`
        : `<span id="commits-${r.name}" class="badge badge-gray">...</span>`;

      const filesInfo = r.source_files !== null
        ? `<span id="files-${r.name}" style="color:#9ca3af" title="${r.source_files} source files out of ${r.total_files} workspace files">${r.source_files} / ${r.total_files} files</span>`
        : `<span id="files-${r.name}" style="color:#9ca3af">...</span>`;

      const docsInfo = r.has_readme !== null
        ? `<span id="docs-${r.name}"><span style="color:${r.has_license ? '#34d399' : '#9ca3af'}">📜 ${r.has_license ? 'Yes' : 'No'}</span> | <span style="color:${r.has_readme ? '#34d399' : '#9ca3af'}">📄 ${r.has_readme ? 'Yes' : 'No'}</span></span>`
        : `<span id="docs-${r.name}"><span style="color:${r.has_license ? '#34d399' : '#9ca3af'}">📜 ${r.has_license ? 'Yes' : 'No'}</span> | <span style="color:#9ca3af">📄 ...</span></span>`;

      return `
        <tr>
          <td><input type="checkbox" class="repo-select" data-name="${r.name}" ${isChecked ? 'checked' : ''} /></td>
          <td>
            <div class="repo-main-info">
              <div class="repo-title-wrapper">
                <a href="https://github.com/${r.full_name}" target="_blank" class="repo-title">${r.name}</a>
              </div>
              <div class="subsecondary-row">
                <div class="repo-desc">${r.description || '<em>No description provided</em>'}</div>
                <div class="meta-pills">
                  ${deployHtml}
                  ${topicsHtml}
                  ${dateHtml}
                </div>
              </div>
            </div>
          </td>
          <td><span class="badge ${visClass}">${r.visibility}</span></td>
          <td><span class="badge badge-lang">${r.language}</span></td>
          <td>
            <div style="display:flex; flex-direction:column; gap:4px;">
              ${commitBadge}
              ${filesInfo}
            </div>
          </td>
          <td>${docsInfo}</td>
        </tr>
      `;
    }).join('');

    // Attach row select listeners
    document.querySelectorAll('.repo-select').forEach(cb => {
      cb.addEventListener('change', (e) => {
        const name = e.target.dataset.name;
        if (e.target.checked) selectedRepos.add(name);
        else selectedRepos.delete(name);
        updateSelectionUI();
      });
    });

    updateSelectionUI();
  }

  function updateSelectionUI() {
    const count = selectedRepos.size;
    selectedBadge.textContent = `${count} selected`;
    if (count > 0) {
      bulkBar.classList.remove('hidden');
    } else {
      bulkBar.classList.add('hidden');
    }
  }

  async function executeAction(endpoint, payload) {
    logOutput.innerHTML = `<div class="log-entry">⏳ Initiating action for ${payload.repos.length} repositories...</div>`;
    modalLogs.classList.remove('hidden');

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      
      const logs = data.logs || [];
      logOutput.innerHTML = logs.map(l => `
        <div class="log-entry ${l.status}">
          <span>${l.status === 'success' ? '✅' : '❌'}</span>
          <strong>${l.repo}:</strong> ${l.message}
        </div>
      `).join('');

      selectedRepos.clear();
      updateSelectionUI();

    } catch (e) {
      logOutput.innerHTML = `<div class="log-entry error">❌ Server error during action execution.</div>`;
    }
  }
});
