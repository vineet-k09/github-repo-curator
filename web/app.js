document.addEventListener('DOMContentLoaded', () => {
  let allRepos = [];
  let selectedRepos = new Set();
  let filters = {
    search: '',
    visibility: 'all',
    commits: 'all',
    scale: 'all'
  };

  // DOM Elements
  const userAvatar = document.getElementById('userAvatar');
  const userName = document.getElementById('userName');
  const userLogin = document.getElementById('userLogin');

  const statTotal = document.getElementById('statTotal');
  const statPublic = document.getElementById('statPublic');
  const statPrivate = document.getElementById('statPrivate');
  const statFewCommits = document.getElementById('statFewCommits');

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

  // Bulk buttons
  const btnMakePublic = document.getElementById('btnMakePublic');
  const btnMakePrivate = document.getElementById('btnMakePrivate');
  const btnSetDesc = document.getElementById('btnSetDesc');
  const btnSetTopics = document.getElementById('btnSetTopics');
  const btnAddLicense = document.getElementById('btnAddLicense');
  const btnAddReadme = document.getElementById('btnAddReadme');
  const btnDelete = document.getElementById('btnDelete');

  // Init
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
  setupPillGroup('filterScale', (val) => { filters.scale = val; renderTable(); });

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

  // Functions
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
      <tr><td colspan="8" class="text-center py-8">
        <div class="spinner"></div>
        <p style="text-align:center; padding: 20px; color:#9ca3af;">Auditing repositories...</p>
      </td></tr>`;

    try {
      const res = await fetch('/api/repos');
      const data = await res.json();
      allRepos = data.repos || [];
      updateStats();
      renderTable();
    } catch (e) {
      repoTableBody.innerHTML = `<tr><td colspan="8" style="color:#ef4444; text-align:center; padding: 20px;">Failed to load repositories.</td></tr>`;
    }
  }

  function updateStats() {
    statTotal.textContent = allRepos.length;
    statPublic.textContent = allRepos.filter(r => r.visibility === 'PUBLIC').length;
    statPrivate.textContent = allRepos.filter(r => r.visibility === 'PRIVATE').length;
    statFewCommits.textContent = allRepos.filter(r => r.commit_count < 5).length;
  }

  function getFilteredRepos() {
    return allRepos.filter(r => {
      // Search
      if (filters.search) {
        const q = filters.search;
        const matchName = r.name.toLowerCase().includes(q);
        const matchDesc = r.description.toLowerCase().includes(q);
        const matchLang = r.language.toLowerCase().includes(q);
        if (!matchName && !matchDesc && !matchLang) return false;
      }
      // Visibility
      if (filters.visibility === 'public' && r.visibility !== 'PUBLIC') return false;
      if (filters.visibility === 'private' && r.visibility !== 'PRIVATE') return false;

      // Commits
      if (filters.commits === 'lt5' && r.commit_count >= 5) return false;
      if (filters.commits === '5to20' && (r.commit_count < 5 || r.commit_count > 20)) return false;
      if (filters.commits === 'gt20' && r.commit_count <= 20) return false;

      // Scale
      if (filters.scale === 'scaffolding' && !r.scale.includes('Scaffolding')) return false;
      if (filters.scale === 'small' && !r.scale.includes('Small App')) return false;
      if (filters.scale === 'full' && !r.scale.includes('Full Application')) return false;

      return true;
    });
  }

  function renderTable() {
    const repos = getFilteredRepos();
    if (repos.length === 0) {
      repoTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:#9ca3af; padding: 24px;">No repositories match the selected filters.</td></tr>`;
      return;
    }

    repoTableBody.innerHTML = repos.map(r => {
      const isChecked = selectedRepos.has(r.name);
      const visClass = r.visibility === 'PUBLIC' ? 'badge-public' : 'badge-private';
      const topicsHtml = (r.topics || []).map(t => `<span class="topic-tag">${t}</span>`).join('');

      return `
        <tr>
          <td><input type="checkbox" class="repo-select" data-name="${r.name}" ${isChecked ? 'checked' : ''} /></td>
          <td>
            <a href="https://github.com/${r.full_name}" target="_blank" class="repo-title">${r.name}</a>
            <div class="tag-list">${topicsHtml}</div>
          </td>
          <td><span class="badge ${visClass}">${r.visibility}</span></td>
          <td><span class="badge badge-gray">${r.scale}</span></td>
          <td><span class="badge badge-amber">${r.commit_count} commits</span></td>
          <td><span style="color:#9ca3af">${r.source_files} / ${r.total_files}</span></td>
          <td>
            <span style="color:${r.has_license ? '#34d399' : '#9ca3af'}">📜 ${r.has_license ? 'Yes' : 'No'}</span> | 
            <span style="color:${r.has_readme ? '#34d399' : '#9ca3af'}">📄 ${r.has_readme ? 'Yes' : 'No'}</span>
          </td>
          <td style="color:#9ca3af; font-size:13px;">${r.description || '<em>No description</em>'}</td>
        </tr>
      `;
    }).join('');

    // Attach row select handlers
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
