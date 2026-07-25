document.addEventListener('DOMContentLoaded', () => {
  const STORAGE_KEY_REPOS = 'gh_curator_repos_v2';
  const STORAGE_KEY_USER = 'gh_curator_user_v2';
  const STORAGE_KEY_PAT = 'gh_pat';

  let allRepos = [];
  let currentUser = null;
  let selectedRepos = new Set();
  let syncInProgress = false;

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
  const authCard = document.getElementById('authCard');
  const patInput = document.getElementById('patInput');
  const btnSavePat = document.getElementById('btnSavePat');

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

  // Bulk buttons
  const btnMakePublic = document.getElementById('btnMakePublic');
  const btnMakePrivate = document.getElementById('btnMakePrivate');
  const btnSetDesc = document.getElementById('btnSetDesc');
  const btnSetTopics = document.getElementById('btnSetTopics');
  const btnAddLicense = document.getElementById('btnAddLicense');
  const btnAddReadme = document.getElementById('btnAddReadme');
  const btnDelete = document.getElementById('btnDelete');

  // 1. Direct GitHub REST API & Local Token Helper
  function getToken() {
    return localStorage.getItem(STORAGE_KEY_PAT) || '';
  }

  async function ghFetch(endpoint, options = {}) {
    const token = getToken();
    if (!token) throw new Error('No GitHub token provided');

    const url = endpoint.startsWith('http') ? endpoint : `https://api.github.com${endpoint}`;
    const headers = {
      'Authorization': `Bearer ${token.trim()}`,
      'Accept': 'application/vnd.github+json',
      'User-Agent': 'GitHub-Repo-Curator-Client',
      ...(options.headers || {})
    };

    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
      authCard.classList.remove('hidden');
      throw new Error('Unauthorized');
    }
    if (res.status === 204) return {};
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.message || `HTTP ${res.status}`);
    }
    return res.json();
  }


  // 2. Initialization
  init();

  async function init() {
    loadCachedUser();
    loadCachedRepos();

    if (getToken()) {
      authCard.classList.add('hidden');
      syncUserData();
      smartSyncRepos(false);
    } else {
      // Check if backend Python server can provide user (local gh CLI fallback)
      try {
        const res = await fetch('/api/user');
        if (res.ok) {
          const user = await res.json();
          if (user.login) {
            authCard.classList.add('hidden');
            currentUser = user;
            updateUserUI();
            fetchReposFromBackend();
            return;
          }
        }
      } catch (e) {}
      authCard.classList.remove('hidden');
    }
  }

  // 3. User & Cache Management
  function loadCachedUser() {
    const raw = localStorage.getItem(STORAGE_KEY_USER);
    if (raw) {
      try {
        currentUser = JSON.parse(raw);
        updateUserUI();
      } catch (e) {}
    }
  }

  function updateUserUI() {
    if (!currentUser) return;
    userAvatar.src = currentUser.avatar_url || 'https://github.com/github.png';
    userName.textContent = currentUser.name || currentUser.login;
    userLogin.textContent = `@${currentUser.login}`;
  }

  async function syncUserData() {
    try {
      const user = await ghFetch('/user');
      currentUser = user;
      localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(user));
      updateUserUI();
    } catch (e) {
      console.error('Failed to sync user', e);
    }
  }

  function loadCachedRepos() {
    const raw = localStorage.getItem(STORAGE_KEY_REPOS);
    if (raw) {
      try {
        allRepos = JSON.parse(raw);
        updateStats();
        renderTable();
      } catch (e) {}
    }
  }

  function saveCachedRepos() {
    localStorage.setItem(STORAGE_KEY_REPOS, JSON.stringify(allRepos));
  }

  // 4. Smart Delta Sync Engine (Client-Side & LocalStorage)
  async function smartSyncRepos(force = false) {
    if (syncInProgress) return;
    syncInProgress = true;
    btnRefresh.textContent = '⏳ Syncing...';
    btnRefresh.disabled = true;

    try {
      // Fetch all surface repos owned by authenticated user
      let reposRaw = [];
      let page = 1;
      while (true) {
        const pageData = await ghFetch(`/user/repos?type=all&per_page=100&page=${page}`);
        if (!Array.isArray(pageData) || pageData.length === 0) break;
        reposRaw.push(...pageData);
        if (pageData.length < 100) break;
        page++;
      }

      if (!currentUser) await syncUserData();
      const owner = currentUser ? currentUser.login.toLowerCase() : '';
      const owned = reposRaw.filter(r => r.owner && r.owner.login.toLowerCase() === owner);

      const existingMap = new Map(allRepos.map(r => [r.name, r]));
      const newRepos = [];
      const toDeepFetch = [];

      for (const r of owned) {
        const name = r.name;
        const pushed_at = (r.pushed_at || r.pushedAt || '').substring(0, 10);
        const cached = existingMap.get(name);

        const is_private = Boolean(r.private);
        const visibility = (r.visibility || (is_private ? 'PRIVATE' : 'PUBLIC')).toUpperCase();
        const language = (r.primaryLanguage && r.primaryLanguage.name) || r.language || 'N/A';
        const homepage = r.homepage || r.homepageUrl || '';
        const topics = Array.isArray(r.topics) ? r.topics : [];

        const baseObj = {
          name: name,
          full_name: r.full_name,
          description: r.description || '',
          visibility: visibility,
          is_private: is_private,
          language: language,
          homepage: homepage,
          stargazers_count: r.stargazers_count || 0,
          forks_count: r.forks_count || 0,
          pushed_at: pushed_at,
          topics: topics,
          // Preserved or computed deep metrics
          commit_count: cached ? cached.commit_count : null,
          source_files: cached ? cached.source_files : null,
          total_files: cached ? cached.total_files : null,
          has_readme: cached ? cached.has_readme : null,
          has_license: Boolean(r.license) || (cached ? cached.has_license : null)
        };

        const needsDeep = force || !cached || cached.pushed_at !== pushed_at || cached.commit_count === null;
        if (needsDeep) {
          toDeepFetch.push(baseObj);
        }
        newRepos.push(baseObj);
      }

      allRepos = newRepos;
      saveCachedRepos();
      updateStats();
      renderTable();

      // Parallel background deep enrichment
      if (toDeepFetch.length > 0) {
        enrichDeepMetricsParallel(toDeepFetch);
      }

    } catch (e) {
      console.error('Smart sync error', e);
    } finally {
      btnRefresh.textContent = '🔄 Smart Sync';
      btnRefresh.disabled = false;
      syncInProgress = false;
    }
  }

  // Parallel enrichment (concurrency limit 6)
  async function enrichDeepMetricsParallel(targets) {
    const CONCURRENCY = 6;
    let index = 0;

    async function worker() {
      while (index < targets.length) {
        const item = targets[index++];
        try {
          // Fetch tree
          const treeData = await ghFetch(`/repos/${item.full_name}/git/trees/HEAD?recursive=1`).catch(() => null);
          const files = (treeData && Array.isArray(treeData.tree)) 
            ? treeData.tree.filter(f => f.type === 'blob').map(f => f.path) 
            : [];
          
          const codeFiles = files.filter(f => !['node_modules/', '.next/', 'vendor/', 'dist/', 'build/', '.git/'].some(x => f.includes(x)));
          const srcFiles = codeFiles.filter(f => ['.py','.js','.ts','.tsx','.jsx','.java','.go','.rs','.cpp','.c','.html','.css','.gd','.php','.typ'].some(ext => f.endswith(ext)));

          // Fetch commits
          const commits = await ghFetch(`/repos/${item.full_name}/commits?per_page=30`).catch(() => []);
          const commitCount = Array.isArray(commits) ? commits.length : 0;

          item.total_files = files.length;
          item.source_files = srcFiles.length;
          item.commit_count = commitCount;
          item.has_readme = files.some(f => f.toLowerCase().includes('readme'));
          item.has_license = files.some(f => f.toLowerCase().includes('license')) || item.has_license;

          saveCachedRepos();
          renderTable();
        } catch (e) {}
      }
    }

    const workers = Array.from({ length: Math.min(CONCURRENCY, targets.length) }, () => worker());
    await Promise.all(workers);
  }

  // Backend Fallback (Local gh CLI mode)
  async function fetchReposFromBackend() {
    try {
      const res = await fetch('/api/repos');
      const data = await res.json();
      allRepos = data.repos || [];
      saveCachedRepos();
      updateStats();
      renderTable();
    } catch (e) {}
  }

  // 5. Action Execution (Direct Client API + Local Cache Persistence)
  async function executeAction(endpoint, payload) {
    logOutput.innerHTML = `<div class="log-entry">⏳ Executing action on ${payload.repos.length} repositories...</div>`;
    modalLogs.classList.remove('hidden');

    const actionType = endpoint.split('/').pop();
    const logs = [];

    for (const repoName of payload.repos) {
      const target = allRepos.find(r => r.name === repoName);
      if (!target) continue;
      const fullName = target.full_name;

      try {
        if (actionType === 'visibility') {
          const isPriv = payload.visibility === 'private';
          await ghFetch(`/repos/${fullName}`, {
            method: 'PATCH',
            body: JSON.stringify({ private: isPriv })
          });
          target.visibility = isPriv ? 'PRIVATE' : 'PUBLIC';
          target.is_private = isPriv;
          logs.push({ repo: repoName, status: 'success', message: `Visibility set to ${target.visibility}` });

        } else if (actionType === 'description') {
          await ghFetch(`/repos/${fullName}`, {
            method: 'PATCH',
            body: JSON.stringify({ description: payload.description })
          });
          target.description = payload.description;
          logs.push({ repo: repoName, status: 'success', message: 'Description updated.' });

        } else if (actionType === 'topics') {
          await ghFetch(`/repos/${fullName}/topics`, {
            method: 'PUT',
            body: JSON.stringify({ names: payload.topics })
          });
          target.topics = payload.topics;
          logs.push({ repo: repoName, status: 'success', message: `Topics updated: #${payload.topics.join(', #')}` });

        } else if (actionType === 'license') {
          const content = btoa(`MIT License\n\nCopyright (c) 2026 ${currentUser ? currentUser.name || currentUser.login : ''}\n\nPermission is hereby granted, free of charge...`);
          await ghFetch(`/repos/${fullName}/contents/LICENSE`, {
            method: 'PUT',
            body: JSON.stringify({ message: 'docs: add MIT LICENSE', content })
          });
          target.has_license = true;
          logs.push({ repo: repoName, status: 'success', message: 'Created MIT LICENSE' });

        } else if (actionType === 'readme') {
          const content = btoa(`# ${repoName}\n\nOpen-source repository.\n`);
          await ghFetch(`/repos/${fullName}/contents/README.md`, {
            method: 'PUT',
            body: JSON.stringify({ message: 'docs: add initial README.md', content })
          });
          target.has_readme = true;
          logs.push({ repo: repoName, status: 'success', message: 'Created README.md' });

        } else if (actionType === 'delete') {
          await ghFetch(`/repos/${fullName}`, { method: 'DELETE' });
          allRepos = allRepos.filter(r => r.name !== repoName);
          logs.push({ repo: repoName, status: 'success', message: `Deleted repository ${fullName}` });
        }

      } catch (err) {
        // Fallback to backend API endpoint if direct call fails
        try {
          const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
          const data = await res.json();
          if (data.logs) logs.push(...data.logs);
        } catch (e2) {
          logs.push({ repo: repoName, status: 'error', message: err.message });
        }
      }
    }

    saveCachedRepos();
    updateStats();
    renderTable();

    logOutput.innerHTML = logs.map(l => `
      <div class="log-entry ${l.status}">
        <span>${l.status === 'success' ? '✅' : '❌'}</span>
        <strong>${l.repo}:</strong> ${l.message}
      </div>
    `).join('');

    selectedRepos.clear();
    updateSelectionUI();
  }

  // 6. UI & Filter Handlers
  btnSavePat.addEventListener('click', () => {
    const token = patInput.value.trim();
    if (token) {
      localStorage.setItem(STORAGE_KEY_PAT, token);
      authCard.classList.add('hidden');
      init();
    }
  });

  btnRefresh.addEventListener('click', () => { smartSyncRepos(true); });

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
    if (isChecked) visibleRepos.forEach(r => selectedRepos.add(r.name));
    else visibleRepos.forEach(r => selectedRepos.delete(r.name));
    updateSelectionUI();
    renderTable();
  });

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
  });

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

  function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' });
    } catch (e) {
      return dateStr;
    }
  }

  function isPrivateRepo(r) {
    return r.is_private === true || (r.visibility && r.visibility.toUpperCase() === 'PRIVATE');
  }

  function updateStats() {
    statTotal.textContent = allRepos.length;
    statPublic.textContent = allRepos.filter(r => !isPrivateRepo(r)).length;
    statPrivate.textContent = allRepos.filter(r => isPrivateRepo(r)).length;
    statDeployments.textContent = allRepos.filter(r => Boolean(r.homepage)).length;
  }

  function getFilteredRepos() {
    return allRepos.filter(r => {
      const priv = isPrivateRepo(r);

      if (filters.search) {
        const q = filters.search;
        const matchName = r.name.toLowerCase().includes(q);
        const matchDesc = (r.description || '').toLowerCase().includes(q);
        const matchLang = (r.language || '').toLowerCase().includes(q);
        const matchTopics = (r.topics || []).some(t => t.toLowerCase().includes(q));
        if (!matchName && !matchDesc && !matchLang && !matchTopics) return false;
      }

      if (filters.visibility === 'public' && priv) return false;
      if (filters.visibility === 'private' && !priv) return false;

      if (r.commit_count !== null && r.commit_count !== undefined) {
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
      const priv = isPrivateRepo(r);
      const visText = priv ? 'PRIVATE' : 'PUBLIC';
      const visClass = priv ? 'badge-private' : 'badge-public';

      const formattedDate = formatDate(r.pushed_at);
      const dateHtml = formattedDate ? `<span class="date-tag">📅 ${formattedDate}</span>` : '';
      const deployHtml = r.homepage ? `<a href="${r.homepage}" target="_blank" class="deploy-link">🔗 ${r.homepage}</a>` : '';
      
      const topicList = Array.isArray(r.topics) ? r.topics : [];
      const topicsHtml = topicList.map(t => `<span class="topic-tag">#${t}</span>`).join('');

      const commitCountText = (r.commit_count !== null && r.commit_count !== undefined) ? `${r.commit_count} commits` : '...';
      const filesCountText = (r.source_files !== null && r.source_files !== undefined) ? `${r.source_files}/${r.total_files} files` : '...';
      const metricsHtml = `<div class="metrics-inline"><span class="highlight">${commitCountText}</span> • <span>${filesCountText}</span></div>`;

      let docsHtml = '';
      const missing = [];
      if (r.has_readme === false) missing.push('<span class="badge-missing">⚠️ No README</span>');
      if (r.has_license === false) missing.push('<span class="badge-missing">⚠️ No License</span>');

      if (missing.length === 0) {
        docsHtml = `<span class="badge-ok">✓ Complete</span>`;
      } else {
        docsHtml = `<div class="missing-docs-list">${missing.join('')}</div>`;
      }

      return `
        <tr>
          <td><input type="checkbox" class="repo-select" data-name="${r.name}" ${isChecked ? 'checked' : ''} /></td>
          <td>
            <div class="repo-main-info">
              <a href="https://github.com/${r.full_name}" target="_blank" class="repo-title">${r.name}</a>
              <div class="subsecondary-row">
                <div class="repo-desc">${r.description || '<em>No description provided</em>'}</div>
                <div class="meta-pills">
                  ${dateHtml}
                  ${deployHtml}
                  ${topicsHtml}
                </div>
              </div>
            </div>
          </td>
          <td><span class="badge ${visClass}">${visText}</span></td>
          <td><span class="badge badge-lang">${r.language}</span></td>
          <td>${metricsHtml}</td>
          <td>${docsHtml}</td>
        </tr>
      `;
    }).join('');

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
    if (count > 0) bulkBar.classList.remove('hidden');
    else bulkBar.classList.add('hidden');
  }
});
