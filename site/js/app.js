/**
 * Akamonkai Japanese — Offline Course App
 * All modules: Navigation, Progress, Theme, Search, Quiz, Video, Sync
 */
(function () {
  'use strict';

  // ═══════════════════════════════════════════
  // Status UI Module
  // ═══════════════════════════════════════════
  const StatusUI = {
    init() {
      this.node = document.getElementById('syncStatus');
      this.set('idle', 'Status: Ready');
    },

    set(state, text) {
      if (!this.node) return;
      this.node.dataset.state = state;
      this.node.textContent = text;
    },
  };

  // ═══════════════════════════════════════════
  // Theme Module
  // ═══════════════════════════════════════════
  const Theme = {
    init() {
      const saved = localStorage.getItem('theme');
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const theme = saved || (prefersDark ? 'dark' : 'light');
      this.set(theme);

      const toggle = document.getElementById('themeToggle');
      if (toggle) {
        toggle.addEventListener('click', () => {
          const current = document.documentElement.getAttribute('data-theme');
          this.set(current === 'dark' ? 'light' : 'dark');
        });
      }
    },

    set(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
      const toggle = document.getElementById('themeToggle');
      if (toggle) toggle.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
  };

  // ═══════════════════════════════════════════
  // Navigation Module
  // ═══════════════════════════════════════════
  const Nav = {
    init() {
      this.sidebar = document.getElementById('sidebar');
      this.hamburger = document.getElementById('hamburger');
      this.closeBtn = document.getElementById('sidebarClose');

      if (this.hamburger) {
        this.hamburger.addEventListener('click', () => this.toggle());
      }
      if (this.closeBtn) {
        this.closeBtn.addEventListener('click', () => this.close());
      }

      // Close sidebar on overlay click (mobile)
      this.sidebar?.addEventListener('click', (e) => {
        if (e.target === this.sidebar) this.close();
      });

      // Section toggles
      document.querySelectorAll('.nav-section-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
          const section = btn.dataset.section;
          const content = document.querySelector(`[data-section-content="${section}"]`);
          btn.classList.toggle('open');
          content?.classList.toggle('open');
        });
      });

      document.querySelectorAll('.nav-day-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
          const day = btn.dataset.day;
          const content = document.querySelector(`[data-day-content="${day}"]`);
          btn.classList.toggle('open');
          content?.classList.toggle('open');
        });
      });

      // Highlight current lesson & expand its section
      this.highlightCurrent();

      // Keyboard shortcuts
      document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 'ArrowLeft') {
          const prev = document.getElementById('prevLesson');
          if (prev && !prev.classList.contains('disabled')) prev.click();
        } else if (e.key === 'ArrowRight') {
          const next = document.getElementById('nextLesson');
          if (next && !next.classList.contains('disabled')) next.click();
        }
      });

      // Auto-complete on Next click
      const nextBtn = document.getElementById('nextLesson');
      if (nextBtn) {
        nextBtn.addEventListener('click', () => {
          const lesson = document.querySelector('.lesson[data-lesson-id]');
          if (lesson && !Progress.isComplete(lesson.dataset.lessonId)) {
            Progress.toggle(lesson.dataset.lessonId);
          }
        });
      }
    },

    toggle() {
      this.sidebar?.classList.toggle('open');
    },

    close() {
      this.sidebar?.classList.remove('open');
    },

    highlightCurrent() {
      const lesson = document.querySelector('.lesson[data-lesson-id]');
      if (!lesson) return;
      const id = lesson.dataset.lessonId;
      const link = document.querySelector(`.nav-link[data-lesson="${id}"]`);
      if (!link) return;
      link.classList.add('active');

      // Expand parent sections
      let parent = link.parentElement;
      while (parent) {
        if (parent.classList.contains('nav-section-items') ||
            parent.classList.contains('nav-day-items')) {
          parent.classList.add('open');
          const toggle = parent.previousElementSibling;
          if (toggle) toggle.classList.add('open');
        }
        parent = parent.parentElement;
      }

      // Scroll into view
      setTimeout(() => link.scrollIntoView({ block: 'center', behavior: 'smooth' }), 100);
    }
  };

  // ═══════════════════════════════════════════
  // Progress Module
  // ═══════════════════════════════════════════
  const Progress = {
    KEY: 'akamonkai_progress',

    init() {
      this.data = this.load();
      this.bindCheckboxes();
      this.updateUI();
      this.updateSidebarMarks();

      // Try to sync with server
      Sync.pull();
    },

    load() {
      try {
        return JSON.parse(localStorage.getItem(this.KEY)) || {};
      } catch {
        return {};
      }
    },

    save() {
      localStorage.setItem(this.KEY, JSON.stringify(this.data));
      // Push to server (async, non-blocking)
      Sync.push(this.data);
    },

    isComplete(lessonId) {
      return !!this.data[lessonId]?.completed;
    },

    toggle(lessonId) {
      if (!this.data[lessonId]) {
        this.data[lessonId] = {};
      }
      this.data[lessonId].completed = !this.data[lessonId].completed;
      this.data[lessonId].timestamp = Date.now();
      this.save();
      this.updateUI();
      this.updateSidebarMarks();
    },

    getCompletedCount() {
      return Object.values(this.data).filter(v => v.completed).length;
    },

    bindCheckboxes() {
      document.querySelectorAll('.lesson-complete-check').forEach(cb => {
        const id = cb.dataset.lesson;
        cb.checked = this.isComplete(id);
        cb.addEventListener('change', () => this.toggle(id));
      });
    },

    updateUI() {
      const completed = this.getCompletedCount();
      const bar = document.getElementById('progressBar');
      const text = document.getElementById('progressText');

      if (bar && text) {
        // Load lesson count from data attribute or fetch
        const root = window.location.pathname.includes('/lessons/') ? '../' : '';
        fetch(root + 'lesson-data.json').then(r => r.json()).then(lessons => {
          const total = lessons.length;
          const pct = total > 0 ? ((completed / total) * 100).toFixed(1) : 0;
          bar.style.width = pct + '%';
          text.textContent = `${completed} / ${total} lessons completed (${pct}%)`;
        }).catch(() => {});
      }

      // Update section counts
      this.updateSectionCounts();
      // Update dashboard card progress
      this.updateCardProgress();
    },

    updateSectionCounts() {
      document.querySelectorAll('.nav-section-count[data-section-ids]').forEach(el => {
        const ids = el.dataset.sectionIds.split(',').filter(Boolean);
        const done = ids.filter(id => this.isComplete(id)).length;
        el.textContent = `${done}/${ids.length}`;
      });
      document.querySelectorAll('.nav-day-count[data-day-ids]').forEach(el => {
        const ids = el.dataset.dayIds.split(',').filter(Boolean);
        const done = ids.filter(id => this.isComplete(id)).length;
        el.textContent = `${done}/${ids.length}`;
      });
    },

    updateCardProgress() {
      document.querySelectorAll('[data-card-progress]').forEach(bar => {
        const ids = bar.dataset.cardProgress.split(',').filter(Boolean);
        const done = ids.filter(id => this.isComplete(id)).length;
        const pct = ids.length > 0 ? ((done / ids.length) * 100).toFixed(0) : 0;
        bar.style.width = pct + '%';
      });
      document.querySelectorAll('[data-card-ptext]').forEach(el => {
        const ids = el.dataset.cardPtext.split(',').filter(Boolean);
        const done = ids.filter(id => this.isComplete(id)).length;
        el.textContent = `${done}/${ids.length} complete`;
      });
    },

    updateSidebarMarks() {
      document.querySelectorAll('.nav-link[data-lesson]').forEach(link => {
        const id = link.dataset.lesson;
        if (this.isComplete(id)) {
          link.classList.add('completed');
        } else {
          link.classList.remove('completed');
        }
      });
    }
  };

  // ═══════════════════════════════════════════
  // Search Module
  // ═══════════════════════════════════════════
  const Search = {
    lessons: [],

    init() {
      const input = document.getElementById('searchInput');
      if (!input) return;

      fetch(this.getRoot() + 'lesson-data.json')
        .then(r => r.json())
        .then(data => { this.lessons = data; })
        .catch(() => {});

      let timeout;
      input.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => this.search(input.value), 200);
      });
    },

    getRoot() {
      // Detect if we're in a subdirectory
      const path = window.location.pathname;
      return path.includes('/lessons/') ? '../' : '';
    },

    search(query) {
      const nav = document.getElementById('sidebarNav');
      if (!nav) return;

      if (!query.trim()) {
        // Show all
        nav.querySelectorAll('.nav-section, .nav-link, .nav-day').forEach(el => {
          el.style.display = '';
        });
        return;
      }

      const q = query.toLowerCase();
      const root = this.getRoot();

      // Find matching lesson IDs
      const matches = new Set(
        this.lessons
          .filter(l => l.title.toLowerCase().includes(q))
          .map(l => l.id)
      );

      // Show/hide nav links
      nav.querySelectorAll('.nav-link[data-lesson]').forEach(link => {
        const id = link.dataset.lesson;
        link.style.display = matches.has(id) ? '' : 'none';
      });

      // Show sections that have visible children
      nav.querySelectorAll('.nav-section').forEach(section => {
        const hasVisible = section.querySelector('.nav-link[data-lesson]:not([style*="none"])');
        section.style.display = hasVisible ? '' : 'none';
        if (hasVisible) {
          section.querySelector('.nav-section-items')?.classList.add('open');
          section.querySelector('.nav-section-toggle')?.classList.add('open');
        }
      });

      nav.querySelectorAll('.nav-day').forEach(day => {
        const hasVisible = day.querySelector('.nav-link[data-lesson]:not([style*="none"])');
        day.style.display = hasVisible ? '' : 'none';
        if (hasVisible) {
          day.querySelector('.nav-day-items')?.classList.add('open');
          day.querySelector('.nav-day-toggle')?.classList.add('open');
        }
      });
    }
  };

  // ═══════════════════════════════════════════
  // Quiz Module
  // ═══════════════════════════════════════════
  const Quiz = {
    init() {
      const container = document.getElementById('quizContainer');
      if (!container) return;

      let answered = 0;
      let correct = 0;
      const questions = container.querySelectorAll('.quiz-question');
      const total = questions.length;

      container.addEventListener('click', (e) => {
        const btn = e.target.closest('.q-option');
        if (!btn || btn.classList.contains('disabled')) return;

        const question = btn.closest('.quiz-question');
        const options = question.querySelectorAll('.q-option');
        const feedback = question.querySelector('.q-feedback');
        const isCorrect = btn.dataset.correct === 'true';

        // Disable all options
        options.forEach(o => o.classList.add('disabled'));

        if (isCorrect) {
          btn.classList.add('correct');
          correct++;
          if (feedback) {
            feedback.textContent = '✓ Correct!';
            feedback.style.color = 'var(--success)';
            feedback.classList.add('show');
          }
        } else {
          btn.classList.add('incorrect');
          // Highlight the correct one
          options.forEach(o => {
            if (o.dataset.correct === 'true') o.classList.add('correct');
          });
          if (feedback) {
            feedback.textContent = '✗ Incorrect';
            feedback.style.color = 'var(--accent)';
            feedback.classList.add('show');
          }
        }

        answered++;
        if (answered === total) {
          const results = document.getElementById('quizResults');
          if (results) {
            results.textContent = `Quiz complete: ${correct} / ${total} correct (${Math.round(correct / total * 100)}%)`;
            results.classList.add('show');
          }
        }
      });
    }
  };

  // ═══════════════════════════════════════════
  // Notes Module
  // ═══════════════════════════════════════════
  const Notes = {
    KEY_PREFIX: 'akamonkai_note_',

    init() {
      document.querySelectorAll('.notes-textarea').forEach(ta => {
        const id = ta.dataset.lesson;
        const saved = localStorage.getItem(this.KEY_PREFIX + id);
        if (saved) ta.value = saved;

        let timeout;
        ta.addEventListener('input', () => {
          clearTimeout(timeout);
          timeout = setTimeout(() => {
            localStorage.setItem(this.KEY_PREFIX + id, ta.value);
            const msg = ta.parentElement.querySelector('.notes-saved-msg');
            if (msg) {
              msg.style.display = 'block';
              setTimeout(() => { msg.style.display = 'none'; }, 1500);
            }
          }, 500);
        });
      });
    }
  };

  // ═══════════════════════════════════════════
  // Bookmarks Module
  // ═══════════════════════════════════════════
  const Bookmarks = {
    KEY: 'akamonkai_bookmarks',

    init() {
      this.data = this.load();
      this.bindToggles();
      this.renderDashboard();
    },

    load() {
      try {
        return JSON.parse(localStorage.getItem(this.KEY)) || {};
      } catch { return {}; }
    },

    save() {
      localStorage.setItem(this.KEY, JSON.stringify(this.data));
    },

    toggle(id) {
      if (this.data[id]) {
        delete this.data[id];
      } else {
        this.data[id] = { timestamp: Date.now() };
      }
      this.save();
    },

    isBookmarked(id) {
      return !!this.data[id];
    },

    bindToggles() {
      document.querySelectorAll('.bookmark-toggle').forEach(btn => {
        const id = btn.dataset.lesson;
        if (this.isBookmarked(id)) {
          btn.textContent = '★';
          btn.classList.add('active');
        }
        btn.addEventListener('click', () => {
          this.toggle(id);
          if (this.isBookmarked(id)) {
            btn.textContent = '★';
            btn.classList.add('active');
          } else {
            btn.textContent = '☆';
            btn.classList.remove('active');
          }
        });
      });
    },

    renderDashboard() {
      const section = document.getElementById('bookmarksSection');
      const list = document.getElementById('bookmarksList');
      if (!section || !list) return;

      const ids = Object.keys(this.data);
      if (ids.length === 0) return;

      const root = window.location.pathname.includes('/lessons/') ? '../' : '';
      fetch(root + 'lesson-data.json').then(r => r.json()).then(lessons => {
        const map = {};
        lessons.forEach(l => { map[l.id] = l; });
        const items = ids.map(id => map[id]).filter(Boolean);
        if (items.length === 0) return;

        section.style.display = 'block';
        list.innerHTML = items.map(l =>
          `<a href="lessons/${l.id}.html" class="bookmark-item">⭐ ${l.title}</a>`
        ).join('');
      }).catch(() => {});
    }
  };

  // ═══════════════════════════════════════════
  // Resume Module
  // ═══════════════════════════════════════════
  const Resume = {
    KEY: 'akamonkai_last_lesson',

    init() {
      // Record current lesson visit
      const lesson = document.querySelector('.lesson[data-lesson-id]');
      if (lesson) {
        const id = lesson.dataset.lessonId;
        localStorage.setItem(this.KEY, JSON.stringify({ id, timestamp: Date.now() }));
      }

      // Render resume on dashboard
      this.renderDashboard();
    },

    renderDashboard() {
      const section = document.getElementById('resumeSection');
      const link = document.getElementById('resumeLink');
      if (!section || !link) return;

      try {
        const data = JSON.parse(localStorage.getItem(this.KEY));
        if (data && data.id) {
          link.href = `lessons/${data.id}.html`;
          section.style.display = 'block';
        }
      } catch {}
    }
  };

  // ═══════════════════════════════════════════
  // Service Worker Registration
  // ═══════════════════════════════════════════
  const Sync = {
    // Will attempt to find the server on the same network
    endpoint: null,
    QUEUE_KEY: 'akamonkai_sync_queue',
    isFlushing: false,

    init() {
      window.addEventListener('online', () => {
        StatusUI.set('warn', 'Status: Reconnecting...');
        this.flushQueue();
      });

      window.addEventListener('offline', () => {
        const queued = this.loadQueue().length;
        const text = queued > 0
          ? `Status: Offline (${queued} pending)`
          : 'Status: Offline';
        StatusUI.set('error', text);
      });

      // Try to find server
      const saved = localStorage.getItem('sync_server');
      if (saved) {
        this.endpoint = saved;
      } else {
        // Try common local addresses
        this.discover();
      }

      if (!navigator.onLine) {
        StatusUI.set('error', 'Status: Offline');
      } else if (this.endpoint) {
        StatusUI.set('warn', 'Status: Sync server ready');
      } else {
        StatusUI.set('warn', 'Status: Searching for sync server');
      }
    },

    loadQueue() {
      try {
        const queue = JSON.parse(localStorage.getItem(this.QUEUE_KEY));
        if (!Array.isArray(queue)) return [];
        return queue;
      } catch {
        return [];
      }
    },

    saveQueue(queue) {
      localStorage.setItem(this.QUEUE_KEY, JSON.stringify(queue));
    },

    enqueue(data, operationId) {
      const queue = this.loadQueue();
      // Keep queue compact: only the most recent snapshot is needed.
      queue.push({
        id: operationId || crypto.randomUUID(),
        timestamp: Date.now(),
        payload: data,
      });
      const compact = queue.slice(-1);
      this.saveQueue(compact);
      StatusUI.set('warn', `Status: Pending sync (${compact.length})`);
    },

    async discover() {
      // Try the page origin first (if served by our server)
      const origin = window.location.origin;
      try {
        const res = await fetch(origin + '/api/progress', { method: 'GET', signal: AbortSignal.timeout(2000) });
        if (res.ok) {
          this.endpoint = origin + '/api/progress';
          localStorage.setItem('sync_server', this.endpoint);
          StatusUI.set('ok', 'Status: Sync connected');
          this.flushQueue();
          return;
        }
      } catch {
        if (navigator.onLine) {
          StatusUI.set('warn', 'Status: Sync unavailable');
        }
      }
    },

    async postPayload(payload, operationId) {
      await fetch(this.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Operation-Id': operationId,
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(5000),
      });
    },

    async flushQueue() {
      if (this.isFlushing || !navigator.onLine) return;

      if (!this.endpoint) {
        await this.discover();
        if (!this.endpoint) return;
      }

      this.isFlushing = true;
      try {
        let queue = this.loadQueue();
        while (queue.length > 0) {
          const item = queue[0];
          await this.postPayload(item.payload, item.id);
          queue.shift();
          this.saveQueue(queue);
        }
        StatusUI.set('ok', 'Status: Synced');
      } catch {
        const queue = this.loadQueue();
        StatusUI.set('warn', `Status: Pending sync (${queue.length})`);
      } finally {
        this.isFlushing = false;
      }
    },

    async push(data) {
      const operationId = crypto.randomUUID();

      if (!navigator.onLine) {
        this.enqueue(data, operationId);
        return;
      }

      if (!this.endpoint) {
        await this.discover();
      }

      if (!this.endpoint) {
        this.enqueue(data, operationId);
        return;
      }

      try {
        await this.postPayload(data, operationId);
        StatusUI.set('ok', 'Status: Synced');
        this.flushQueue();
      } catch {
        this.enqueue(data, operationId);
      }
    },

    async pull() {
      if (!navigator.onLine) {
        const queued = this.loadQueue().length;
        const text = queued > 0
          ? `Status: Offline (${queued} pending)`
          : 'Status: Offline';
        StatusUI.set('error', text);
        return;
      }

      if (!this.endpoint) {
        await this.discover();
      }

      if (!this.endpoint) {
        StatusUI.set('warn', 'Status: Sync unavailable');
        return;
      }

      try {
        const res = await fetch(this.endpoint, { signal: AbortSignal.timeout(5000) });
        if (!res.ok) return;
        const serverData = await res.json();
        const localData = Progress.load();

        // Merge: most recent timestamp wins per lesson
        let updated = false;
        for (const [id, sv] of Object.entries(serverData)) {
          const lv = localData[id];
          if (!lv || (sv.timestamp || 0) > (lv.timestamp || 0)) {
            localData[id] = sv;
            updated = true;
          }
        }

        if (updated) {
          Progress.data = localData;
          localStorage.setItem(Progress.KEY, JSON.stringify(localData));
          Progress.updateUI();
          Progress.updateSidebarMarks();
          Progress.bindCheckboxes();
        }
        StatusUI.set('ok', 'Status: Synced');
        this.flushQueue();
      } catch {
        StatusUI.set('warn', 'Status: Sync read failed');
      }
    }
  };

  // ═══════════════════════════════════════════
  // Service Worker Registration
  // ═══════════════════════════════════════════
  function registerSW() {
    if ('serviceWorker' in navigator) {
      const root = window.location.pathname.includes('/lessons/') ? '../' : '';
      navigator.serviceWorker.register(root + 'sw.js').catch(() => {});
    }
  }

  // ═══════════════════════════════════════════
  // Init
  // ═══════════════════════════════════════════
  document.addEventListener('DOMContentLoaded', () => {
    StatusUI.init();
    Theme.init();
    Nav.init();
    Sync.init();
    Progress.init();
    Search.init();
    Quiz.init();
    Notes.init();
    Bookmarks.init();
    Resume.init();
    registerSW();
  });
})();
