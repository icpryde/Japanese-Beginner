/**
 * Akamonkai Japanese — Offline Course App
 * All modules: Navigation, Progress, Theme, Search, Quiz, Video, Sync
 */
(function () {
  'use strict';

  function getRootPath() {
    return window.location.pathname.includes('/lessons/') ? '../' : '';
  }

  function ensureBrandIcons() {
    const root = getRootPath();
    const icon192 = root + 'icons/icon-192.png';

    const ensureLink = (rel, href) => {
      let node = document.querySelector(`link[rel="${rel}"]`);
      if (!node) {
        node = document.createElement('link');
        node.rel = rel;
        document.head.appendChild(node);
      }
      node.href = href;
    };

    ensureLink('icon', icon192);
    ensureLink('shortcut icon', icon192);
    ensureLink('apple-touch-icon', icon192);
  }

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
    currentIndex: 0,
    total: 0,
    correct: 0,
    topicScores: {},
    container: null,
    questions: null,
    testId: null,

    init() {
      this.container = document.getElementById('quizContainer');
      if (!this.container) return;

      const testWrapper = document.querySelector('.weekly-test[data-test-id]');
      this.testId = testWrapper ? testWrapper.dataset.testId : null;

      this.questions = Array.from(this.container.querySelectorAll('.quiz-question'));
      this.total = this.questions.length;

      this.showPreviousResult();

      // Answer click handler
      this.container.addEventListener('click', (e) => {
        const btn = e.target.closest('.q-option');
        if (!btn) return;
        const question = btn.closest('.quiz-question');
        if (this.questions.indexOf(question) !== this.currentIndex) return;
        if (question.dataset.submitted || btn.classList.contains('disabled')) return;
        this.handleAnswer(btn);
      });

      document.getElementById('quizBackBtn')?.addEventListener('click', () => this.goBack());
      document.getElementById('quizSubmitBtn')?.addEventListener('click', () => this.submitAnswer());

      this.showQuestion(0);
    },

    showQuestion(index) {
      this.currentIndex = index;
      this.questions.forEach((q, i) => q.classList.toggle('active', i === index));
      this.updateProgressBar();
      this.updateNav();
      // Scroll sticky bar into view on navigation
      const sticky = document.getElementById('testProgressSticky');
      if (sticky) sticky.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },

    updateNav() {
      const backBtn = document.getElementById('quizBackBtn');
      const submitBtn = document.getElementById('quizSubmitBtn');
      const question = this.questions[this.currentIndex];
      const isSubmitted = question?.dataset.submitted === 'true';
      const hasSelection = !!question?.querySelector('.q-option.selected');
      const isLast = this.currentIndex === this.total - 1;

      if (backBtn) backBtn.disabled = this.currentIndex === 0;

      if (submitBtn) {
        if (isSubmitted) {
          submitBtn.textContent = isLast ? 'See Results' : 'Next →';
          submitBtn.disabled = false;
          submitBtn.classList.add('ready');
        } else {
          submitBtn.textContent = 'Submit Answer';
          submitBtn.disabled = !hasSelection;
          submitBtn.classList.toggle('ready', hasSelection);
        }
      }
    },

    updateProgressBar() {
      const bar = document.getElementById('quizProgressFill');
      const text = document.getElementById('quizProgressText');
      const answered = this.questions ? this.questions.filter(q => q.dataset.submitted === 'true').length : 0;
      const pct = this.total > 0 ? Math.round((answered / this.total) * 100) : 0;
      if (bar) bar.style.width = pct + '%';
      if (text) text.textContent = 'Question ' + (this.currentIndex + 1) + ' of ' + this.total;
    },

    handleAnswer(btn) {
      const question = this.questions[this.currentIndex];
      const prev = question.querySelector('.q-option.selected');
      if (prev) prev.classList.remove('selected');
      btn.classList.add('selected');
      this.updateNav();
    },

    submitAnswer() {
      const question = this.questions[this.currentIndex];
      const isSubmitted = question?.dataset.submitted === 'true';

      if (isSubmitted) {
        if (this.currentIndex < this.total - 1) {
          this.showQuestion(this.currentIndex + 1);
        } else {
          this.showResults();
          this.saveResult();
          const nav = document.getElementById('testNav');
          if (nav) nav.style.display = 'none';
        }
        return;
      }

      const selected = question.querySelector('.q-option.selected');
      if (!selected) return;

      const isCorrect = selected.dataset.correct === 'true';
      const topic = question.dataset.topic || 'General';
      const explanation = question.dataset.explanation || '';

      if (!this.topicScores[topic]) this.topicScores[topic] = { correct: 0, total: 0 };
      this.topicScores[topic].total++;
      if (isCorrect) {
        this.correct++;
        this.topicScores[topic].correct++;
      }

      // Lock options and reveal correct/incorrect
      question.querySelectorAll('.q-option').forEach(o => {
        o.classList.add('disabled');
        if (o.dataset.correct === 'true') o.classList.add('correct');
      });
      if (!isCorrect) selected.classList.add('incorrect');

      // Show feedback
      const feedback = question.querySelector('.q-feedback');
      if (feedback) {
        if (isCorrect) {
          feedback.innerHTML = '✓ Correct!' + (explanation ? ' <span class="q-explanation">' + explanation + '</span>' : '');
          feedback.className = 'q-feedback show feedback-correct';
        } else {
          const correctBtn = question.querySelector('.q-option[data-correct="true"]');
          const correctText = correctBtn ? correctBtn.textContent : '';
          feedback.innerHTML = '✗ The answer is <strong>' + correctText + '</strong>' + (explanation ? '<br><span class="q-explanation">' + explanation + '</span>' : '');
          feedback.className = 'q-feedback show feedback-incorrect';
        }
      }

      question.dataset.submitted = 'true';
      this.updateProgressBar();
      this.updateNav();
    },

    goBack() {
      if (this.currentIndex > 0) this.showQuestion(this.currentIndex - 1);
    },

    showResults() {
      const panel = document.getElementById('quizResults');
      if (!panel) return;

        // Get review link metadata from page header (or default to Week 1)
        const breadcrumb = document.evaluate("//a[contains(text(), 'Review')]", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        const reviewLink = breadcrumb ? breadcrumb.href : '../lessons/12645437.html';
        const reviewLabel = breadcrumb ? breadcrumb.textContent.trim() : 'Week 1 Review';

      let grade, gradeLabel;
      if (pct >= 90) { grade = 'A'; gradeLabel = 'Excellent!'; }
      else if (pct >= 80) { grade = 'B'; gradeLabel = 'Great work!'; }
      else if (pct >= 70) { grade = 'C'; gradeLabel = 'Good effort!'; }
      else if (pct >= 60) { grade = 'D'; gradeLabel = 'Keep studying!'; }
      else { grade = 'F'; gradeLabel = 'Review and try again'; }

      const gradeClass = pct >= 70 ? 'grade-pass' : 'grade-fail';

      let html = '<div class="test-results-inner">';

      html += '<div class="test-results-header">';
      html += '<h2>Test Results</h2>';
      html += '<div class="test-results-grade-row">';
      html += '<div class="quiz-grade ' + gradeClass + '">' + grade + '</div>';
      html += '<div class="quiz-score-detail">';
      html += '<div class="quiz-score-big">' + this.correct + ' / ' + this.total + '</div>';
      html += '<div class="quiz-score-pct">' + pct + '% · ' + gradeLabel + '</div>';
      html += '</div></div></div>';

      // Topic breakdown
      html += '<div class="quiz-topic-breakdown"><h4>Score by Topic</h4><div class="topic-bars">';
      const topicOrder = ['Hiragana', 'Particles', 'Grammar', 'Vocabulary', 'Numbers & Counting'];
      for (const topic of topicOrder) {
        const s = this.topicScores[topic];
        if (!s) continue;
        const tpct = Math.round((s.correct / s.total) * 100);
        const barClass = tpct >= 70 ? 'bar-pass' : 'bar-fail';
        html += '<div class="topic-row">';
        html += '<span class="topic-label">' + topic + '</span>';
        html += '<div class="topic-bar-track"><div class="topic-bar-fill ' + barClass + '" style="width:' + tpct + '%"></div></div>';
        html += '<span class="topic-score">' + s.correct + '/' + s.total + '</span>';
        html += '</div>';
      }
      html += '</div></div>';

      // Full question review
      html += '<div class="test-full-review"><h4>Question Review</h4>';
      this.questions.forEach(q => {
        const num = q.dataset.qnum;
        const topic = q.dataset.topic || '';
        const text = q.querySelector('.q-text')?.textContent || '';
        const selected = q.querySelector('.q-option.selected');
        const correctBtn = q.querySelector('.q-option[data-correct="true"]');
        const isCorrect = selected && selected.dataset.correct === 'true';
        const explanation = q.dataset.explanation || '';

        html += '<div class="review-item ' + (isCorrect ? 'review-correct' : 'review-incorrect') + '">';
        html += '<div class="review-header">';
        html += '<span class="review-num">Q' + num + '</span>';
        html += '<span class="review-status">' + (isCorrect ? '✓' : '✗') + '</span>';
        html += '<span class="review-topic-tag">' + topic + '</span>';
        html += '</div>';
        html += '<div class="review-question">' + text + '</div>';
        if (!isCorrect) {
          html += '<div class="review-answer-row">';
          html += '<span class="wrong-yours">Your answer: ' + (selected ? selected.textContent : 'none') + '</span>';
          html += '<span class="wrong-correct">Correct: ' + (correctBtn ? correctBtn.textContent : '') + '</span>';
          html += '</div>';
        }
        if (explanation) html += '<div class="review-explanation">' + explanation + '</div>';
        html += '</div>';
      });
      html += '</div>';

      html += '<div class="test-result-actions">';
      html += '<button id="quizRetakeBtn" class="quiz-retake-btn">↻ Retake Test</button>';
      html += '<a href="' + reviewLink + '" class="test-back-link">← Back to ' + reviewLabel + '</a>';
      html += '</div>';

      html += '</div>';

      panel.innerHTML = html;
      panel.classList.add('show');
      panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

      document.getElementById('quizRetakeBtn')?.addEventListener('click', () => this.retake());
    },

    saveResult() {
      if (!this.testId) return;
      const pct = Math.round((this.correct / this.total) * 100);
      const key = 'akamonkai_test_' + this.testId;
      let prev;
      try { prev = JSON.parse(localStorage.getItem(key)); } catch { prev = null; }

      const result = {
        score: this.correct,
        total: this.total,
        percentage: pct,
        bestPercentage: prev ? Math.max(prev.bestPercentage || 0, pct) : pct,
        timestamp: Date.now(),
        attempts: (prev?.attempts || 0) + 1
      };
      localStorage.setItem(key, JSON.stringify(result));

      if (!Progress.data['__tests__']) Progress.data['__tests__'] = {};
      Progress.data['__tests__'][this.testId] = result;
      Progress.save();
    },

    showPreviousResult() {
      if (!this.testId) return;
      const key = 'akamonkai_test_' + this.testId;
      let prev;
      try { prev = JSON.parse(localStorage.getItem(key)); } catch { prev = null; }
      if (!prev) return;

      const banner = document.getElementById('quizPreviousBanner');
      if (banner) {
        const d = new Date(prev.timestamp);
        banner.innerHTML = '<strong>Previous result:</strong> ' + prev.score + '/' + prev.total +
          ' (' + prev.percentage + '%)' +
          (prev.bestPercentage > prev.percentage ? ' · Best: ' + prev.bestPercentage + '%' : '') +
          ' · Attempts: ' + prev.attempts +
          ' · ' + d.toLocaleDateString();
        banner.classList.add('show');
      }
    },

    retake() {
      if (!this.container) return;
      this.currentIndex = 0;
      this.correct = 0;
      this.topicScores = {};

      this.questions.forEach(q => { delete q.dataset.submitted; });
      this.container.querySelectorAll('.q-option').forEach(o => {
        o.classList.remove('disabled', 'correct', 'incorrect', 'selected');
      });
      this.container.querySelectorAll('.q-feedback').forEach(f => {
        f.className = 'q-feedback';
        f.innerHTML = '';
      });

      const results = document.getElementById('quizResults');
      if (results) { results.classList.remove('show'); results.innerHTML = ''; }

      if (this.container) this.container.style.display = '';
      const nav = document.getElementById('testNav');
      if (nav) nav.style.display = '';

      this.showQuestion(0);
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
    // Cloud or local sync endpoint
    endpoint: null,
    syncKey: null,
    QUEUE_KEY: 'akamonkai_sync_queue',
    isFlushing: false,
    CONFIG_ENDPOINT_KEY: 'akamonkai_sync_endpoint',
    CONFIG_KEY_KEY: 'akamonkai_sync_user_key',
    DEFAULT_CLOUD_ENDPOINT: 'https://akamonkai-progress-sync.icpryde-akamonkai-sync.workers.dev/api/progress',

    isHostedStatic() {
      return window.location.hostname.endsWith('github.io');
    },

    normalizeEndpoint(value) {
      const trimmed = (value || '').trim();
      if (!trimmed) return '';
      const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
      const noTrailing = withProtocol.replace(/\/+$/, '');
      if (noTrailing.endsWith('/api/progress')) return noTrailing;
      return `${noTrailing}/api/progress`;
    },

    getConfiguredEndpoint() {
      const stored = localStorage.getItem(this.CONFIG_ENDPOINT_KEY) || '';
      return this.normalizeEndpoint(stored || this.DEFAULT_CLOUD_ENDPOINT);
    },

    getConfiguredSyncKey() {
      return (localStorage.getItem(this.CONFIG_KEY_KEY) || '').trim();
    },

    hasCloudConfig() {
      return !!this.getConfiguredEndpoint() && !!this.getConfiguredSyncKey();
    },

    endpointWithKey() {
      if (!this.endpoint) return null;
      const url = new URL(this.endpoint);
      if (this.syncKey) url.searchParams.set('sync_key', this.syncKey);
      return url.toString();
    },

    setLocalModeStatus(text) {
      StatusUI.set('ok', text || 'Status: Local progress (tap to setup sync)');
    },

    bindStatusClick() {
      const node = document.getElementById('syncStatus');
      if (!node) return;
      node.title = 'Tap to configure cloud sync';
      node.style.cursor = 'pointer';
      node.addEventListener('click', () => this.configureCloudSync());
    },

    configureCloudSync() {
      const currentEndpoint = this.getConfiguredEndpoint();
      const endpointInput = window.prompt(
        'Cloud sync endpoint URL (Cloudflare Worker domain). Leave blank to disable cloud sync.',
        currentEndpoint ? currentEndpoint.replace(/\/api\/progress$/, '') : ''
      );
      if (endpointInput === null) return;

      const normalized = this.normalizeEndpoint(endpointInput);
      if (!normalized) {
        localStorage.removeItem(this.CONFIG_ENDPOINT_KEY);
        localStorage.removeItem(this.CONFIG_KEY_KEY);
        this.endpoint = null;
        this.syncKey = null;
        this.setLocalModeStatus();
        return;
      }

      const currentKey = this.getConfiguredSyncKey();
      const keyInput = window.prompt(
        'Sync key (use the same key on Mac and iPad).',
        currentKey
      );
      if (keyInput === null) return;

      const syncKey = keyInput.trim();
      if (!syncKey) {
        window.alert('Sync key is required to enable cloud sync. Keeping local-only mode.');
        this.setLocalModeStatus();
        return;
      }

      localStorage.setItem(this.CONFIG_ENDPOINT_KEY, normalized);
      localStorage.setItem(this.CONFIG_KEY_KEY, syncKey);
      this.endpoint = normalized;
      this.syncKey = syncKey;
      StatusUI.set('warn', 'Status: Connecting sync...');
      this.pull();
    },

    init() {
      this.bindStatusClick();

      window.addEventListener('online', () => {
        if (this.isHostedStatic() && !this.hasCloudConfig()) {
          this.setLocalModeStatus();
          return;
        }
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
      if (this.hasCloudConfig()) {
        this.endpoint = this.getConfiguredEndpoint();
        this.syncKey = this.getConfiguredSyncKey();
      } else if (saved) {
        this.endpoint = saved;
      } else {
        // Try common local addresses
        this.discover();
      }

      if (!navigator.onLine) {
        StatusUI.set('error', 'Status: Offline');
      } else if (this.endpoint) {
        StatusUI.set('warn', 'Status: Sync configured');
      } else if (this.isHostedStatic() && !this.hasCloudConfig()) {
        this.setLocalModeStatus();
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
      const configuredEndpoint = this.getConfiguredEndpoint();
      const configuredKey = this.getConfiguredSyncKey();
      if (configuredEndpoint && configuredKey) {
        this.endpoint = configuredEndpoint;
        this.syncKey = configuredKey;
        try {
          const res = await fetch(this.endpointWithKey(), { method: 'GET', signal: AbortSignal.timeout(2500) });
          if (res.ok) {
            StatusUI.set('ok', 'Status: Sync connected');
            this.flushQueue();
            return;
          }
        } catch {}
        StatusUI.set('warn', 'Status: Sync endpoint unreachable');
        return;
      }

      if (this.isHostedStatic()) {
        this.endpoint = null;
        this.syncKey = null;
        this.setLocalModeStatus();
        return;
      }

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
      await fetch(this.endpointWithKey() || this.endpoint, {
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
        if (!this.endpoint) {
          if (this.isHostedStatic() && !this.hasCloudConfig()) {
            this.setLocalModeStatus();
          }
          return;
        }
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
        if (this.isHostedStatic() && !this.hasCloudConfig()) {
          this.setLocalModeStatus();
          return;
        }
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
        if (this.isHostedStatic() && !this.hasCloudConfig()) {
          this.setLocalModeStatus();
          return;
        }
        StatusUI.set('warn', 'Status: Sync unavailable');
        return;
      }

      try {
        const res = await fetch(this.endpointWithKey() || this.endpoint, { signal: AbortSignal.timeout(5000) });
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
  // Week 3 Review Quiz Module
  // ═══════════════════════════════════════════
  const Week3ReviewQuiz = {
    LESSON_ID: 'Week 3 - Review quiz Answers',
    STORAGE_KEY: 'akamonkai_week3_review_quiz_v1',
    PASS_PERCENT: 80,
    AUDIO_MAP: {
      '135C_zlduagxKDuD-Yc2Dlt25g5nK6ZqE': '../audio/week_03/day_15/3week_test_audio_question6.mp3',
      '10p_eB6TQQjplSlOD_amadiBfQ4crNEhp': '../audio/week_03/day_15/3week_test_audio_question13.mp3',
      '1JoFzFTY72sQ2UNZ_6o9OrdamZxPop4GK': '../audio/week_03/day_15/3week_test_audio_question15.mp3',
      '1jICJ9A8qDd78PXBQV98He73MSkMlZmvw': '../audio/week_03/day_15/3week_test_audio_question16.mp3',
      '1ga-7X6hR_EAmBJo1UTMCpOSExnTAo9bk': '../audio/week_03/day_15/3week_test_audio_question17.mp3',
      '19KRJTt5xW859hUDy-EiU_3iAaFxXMIUz': '../audio/week_03/day_15/3week_test_audio_question24.mp3'
    },
    VIDEO_MAP: {
      btlb4fmh0ra1r4jeb550: '../videos/week_03/day_15/D1L4Q1.mp4',
      bt52pbp9tnhu54jp2afg: '../videos/week_03/day_15/new_question.mp4'
    },

    init() {
      const lesson = document.querySelector('.lesson[data-lesson-id]');
      if (!lesson || lesson.dataset.lessonId !== this.LESSON_ID) return;

      this.lessonBody = lesson.querySelector('.lesson-body');
      if (!this.lessonBody) return;

      this.injectStyles();
      this.questions = this.parseQuestions(this.lessonBody.innerHTML);
      if (!this.questions.length) return;

      this.state = this.loadState();
      this.renderShell();
      this.cacheNodes();
      this.bindEvents();
      this.render();
    },

    injectStyles() {
      if (document.getElementById('w3rqStyles')) return;

      const style = document.createElement('style');
      style.id = 'w3rqStyles';
      style.textContent = `
        .w3rq-shell {
          background: var(--bg-secondary);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          box-shadow: 0 4px 14px var(--shadow);
          padding: 16px;
        }

        .w3rq-header {
          display: grid;
          grid-template-columns: 1fr auto;
          gap: 12px;
          align-items: center;
          margin-bottom: 14px;
          padding-bottom: 12px;
          border-bottom: 1px solid var(--border);
        }

        .w3rq-progress-track {
          width: 100%;
          height: 10px;
          background: var(--bg-tertiary);
          border-radius: 999px;
          overflow: hidden;
          margin-bottom: 6px;
        }

        .w3rq-progress-fill {
          height: 100%;
          background: linear-gradient(90deg, var(--accent), var(--info));
          width: 0%;
          transition: width 0.25s ease;
        }

        .w3rq-progress-label {
          font-size: 0.86rem;
          color: var(--text-secondary);
          font-weight: 600;
        }

        .w3rq-score {
          font-size: 0.92rem;
          font-weight: 700;
          color: var(--text-primary);
          background: var(--bg-tertiary);
          border: 1px solid var(--border);
          border-radius: 999px;
          padding: 6px 12px;
          white-space: nowrap;
        }

        .w3rq-card {
          border: 1px solid var(--border);
          border-radius: var(--radius);
          background: color-mix(in srgb, var(--bg-secondary) 86%, var(--bg-primary));
          padding: 16px;
        }

        .w3rq-number {
          color: var(--accent);
          font-size: 0.78rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          margin-bottom: 8px;
        }

        .w3rq-prompt {
          font-size: 1.05rem;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: 8px;
        }

        .w3rq-type {
          display: inline-block;
          margin-bottom: 14px;
          padding: 3px 10px;
          border-radius: 999px;
          font-size: 0.74rem;
          font-weight: 600;
          background: color-mix(in srgb, var(--info) 16%, var(--bg-secondary));
          color: var(--info);
          border: 1px solid color-mix(in srgb, var(--info) 30%, transparent);
        }

        .w3rq-media-wrap {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 14px;
        }

        .w3rq-media-wrap audio,
        .w3rq-media-wrap video {
          width: 100%;
          max-width: 620px;
          border-radius: var(--radius-sm);
          background: #111;
        }

        .w3rq-media-wrap img {
          width: 100%;
          max-width: 520px;
          border: 1px solid var(--border);
          border-radius: var(--radius);
          background: #fff;
        }

        .w3rq-options {
          display: grid;
          gap: 8px;
        }

        .w3rq-option {
          width: 100%;
          text-align: left;
          border: 1px solid var(--border);
          border-radius: var(--radius-sm);
          background: var(--bg-tertiary);
          color: var(--text-primary);
          padding: 11px 14px;
          font-size: 0.95rem;
          line-height: 1.5;
          cursor: pointer;
          transition: all var(--transition);
        }

        .w3rq-option:hover:not(:disabled) {
          border-color: var(--info);
          background: color-mix(in srgb, var(--info) 12%, var(--bg-secondary));
        }

        .w3rq-option.selected {
          border-color: var(--info);
          background: color-mix(in srgb, var(--info) 18%, var(--bg-secondary));
          font-weight: 600;
        }

        .w3rq-option.correct {
          background: var(--success-bg);
          border-color: var(--success);
          color: var(--success);
          font-weight: 700;
        }

        .w3rq-option.incorrect {
          background: var(--accent-light);
          border-color: var(--accent);
          color: var(--accent);
          opacity: 0.85;
        }

        .w3rq-feedback {
          margin-top: 12px;
          padding: 10px 12px;
          border-radius: var(--radius-sm);
          border: 1px solid var(--border);
          background: var(--bg-primary);
          color: var(--text-secondary);
          font-size: 0.9rem;
          display: none;
        }

        .w3rq-feedback.show {
          display: block;
        }

        .w3rq-feedback.good {
          border-color: color-mix(in srgb, var(--success) 40%, var(--border));
          background: color-mix(in srgb, var(--success-bg) 72%, var(--bg-secondary));
          color: var(--success);
        }

        .w3rq-feedback.bad {
          border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
          background: color-mix(in srgb, var(--accent-light) 72%, var(--bg-secondary));
          color: var(--accent);
        }

        .w3rq-actions {
          margin-top: 14px;
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .w3rq-btn {
          border: 1px solid var(--border);
          background: var(--bg-tertiary);
          color: var(--text-primary);
          border-radius: var(--radius-sm);
          padding: 10px 14px;
          font-family: var(--font-sans);
          font-size: 0.9rem;
          font-weight: 600;
          cursor: pointer;
          transition: all var(--transition);
        }

        .w3rq-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          border-color: var(--text-secondary);
        }

        .w3rq-btn:disabled {
          opacity: 0.45;
          cursor: not-allowed;
          transform: none;
        }

        .w3rq-btn.primary {
          background: var(--accent);
          color: #fff;
          border-color: var(--accent);
        }

        .w3rq-btn.primary:hover:not(:disabled) {
          background: var(--accent-hover);
          border-color: var(--accent-hover);
        }

        .w3rq-results {
          margin-top: 16px;
          display: none;
          border: 1px solid var(--border);
          border-radius: var(--radius);
          background: var(--bg-secondary);
          padding: 16px;
        }

        .w3rq-results.show {
          display: block;
        }

        .w3rq-results h3 {
          margin-bottom: 10px;
          font-size: 1.2rem;
        }

        .w3rq-final {
          display: grid;
          grid-template-columns: 90px 1fr;
          gap: 14px;
          align-items: center;
          margin-bottom: 12px;
        }

        .w3rq-grade {
          width: 90px;
          height: 90px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
          font-weight: 700;
          border: 3px solid;
        }

        .w3rq-grade.pass {
          color: var(--success);
          border-color: var(--success);
          background: var(--success-bg);
        }

        .w3rq-grade.fail {
          color: var(--accent);
          border-color: var(--accent);
          background: var(--accent-light);
        }

        .w3rq-final p {
          margin: 0;
          color: var(--text-secondary);
        }

        .w3rq-missed-list {
          margin-top: 12px;
          display: grid;
          gap: 10px;
        }

        .w3rq-missed-item {
          border-left: 4px solid var(--accent);
          border: 1px solid var(--border);
          border-left-width: 4px;
          border-radius: var(--radius-sm);
          padding: 10px 12px;
          background: color-mix(in srgb, var(--accent-light) 45%, var(--bg-secondary));
        }

        .w3rq-missed-item h4 {
          margin: 0 0 6px;
          font-size: 0.9rem;
          color: var(--text-primary);
        }

        .w3rq-missed-item p {
          margin: 0;
          font-size: 0.86rem;
          color: var(--text-secondary);
        }

        .w3rq-missed-item .label {
          color: var(--text-primary);
          font-weight: 700;
        }

        @media (max-width: 768px) {
          .w3rq-shell {
            padding: 12px;
          }

          .w3rq-header {
            grid-template-columns: 1fr;
          }

          .w3rq-final {
            grid-template-columns: 1fr;
            text-align: center;
            justify-items: center;
          }
        }
      `;
      document.head.appendChild(style);
    },

    cacheNodes() {
      this.progressFill = document.getElementById('w3rqProgressFill');
      this.progressLabel = document.getElementById('w3rqProgressLabel');
      this.scoreNode = document.getElementById('w3rqScore');
      this.cardNode = document.getElementById('w3rqCard');
      this.feedbackNode = document.getElementById('w3rqFeedback');
      this.resultsNode = document.getElementById('w3rqResults');
      this.prevBtn = document.getElementById('w3rqPrevBtn');
      this.actionBtn = document.getElementById('w3rqActionBtn');
      this.resetBtn = document.getElementById('w3rqResetBtn');
    },

    bindEvents() {
      this.prevBtn?.addEventListener('click', () => {
        if (this.state.index > 0) {
          this.state.index -= 1;
          this.saveState();
          this.render();
        }
      });

      this.actionBtn?.addEventListener('click', () => {
        const current = this.state.answers[this.state.index];
        if (!current) return;

        if (!current.submitted) {
          this.submitCurrent();
          return;
        }

        if (this.state.index === this.questions.length - 1) {
          this.state.finished = true;
          this.saveState();
          this.renderResults();
          return;
        }

        this.state.index += 1;
        this.saveState();
        this.render();
      });

      this.resetBtn?.addEventListener('click', () => {
        if (!window.confirm('Reset quiz and clear all answers?')) return;
        this.state = this.createEmptyState();
        localStorage.removeItem(this.STORAGE_KEY);
        this.render();
      });
    },

    renderShell() {
      this.lessonBody.innerHTML = [
        '<div class="w3rq-shell">',
        '<div class="w3rq-header">',
        '<div>',
        '<div class="w3rq-progress-track"><div id="w3rqProgressFill" class="w3rq-progress-fill"></div></div>',
        '<div id="w3rqProgressLabel" class="w3rq-progress-label"></div>',
        '</div>',
        '<div id="w3rqScore" class="w3rq-score"></div>',
        '</div>',
        '<div id="w3rqCard" class="w3rq-card"></div>',
        '<div id="w3rqFeedback" class="w3rq-feedback"></div>',
        '<div class="w3rq-actions">',
        '<button id="w3rqPrevBtn" class="w3rq-btn" type="button">← Previous</button>',
        '<button id="w3rqActionBtn" class="w3rq-btn primary" type="button">Confirm</button>',
        '<button id="w3rqResetBtn" class="w3rq-btn" type="button">Reset Quiz</button>',
        '</div>',
        '<div id="w3rqResults" class="w3rq-results"></div>',
        '</div>'
      ].join('');
    },

    render() {
      if (this.state.finished) {
        this.renderResults();
        return;
      }

      const q = this.questions[this.state.index];
      const a = this.state.answers[this.state.index];
      if (!q || !a) return;

      const prompt = this.escapeHtml(q.prompt || 'Choose the best answer.');
      let mediaHtml = '';

      if (q.media.video) {
        mediaHtml += '<video controls preload="metadata"><source src="' + this.escapeAttr(q.media.video) + '" type="video/mp4"></video>';
      }
      if (q.media.audio) {
        mediaHtml += '<audio controls preload="metadata" src="' + this.escapeAttr(q.media.audio) + '"></audio>';
      }
      if (q.media.image) {
        mediaHtml += '<img src="' + this.escapeAttr(q.media.image) + '" alt="Question ' + q.number + ' image">';
      }

      let optionsHtml = '<div class="w3rq-options">';
      q.options.forEach((option) => {
        const selected = a.selected.includes(option.letter);
        const classes = ['w3rq-option'];
        if (selected) classes.push('selected');

        if (a.submitted) {
          if (option.correct) classes.push('correct');
          if (selected && !option.correct) classes.push('incorrect');
        }

        optionsHtml += '<button type="button" class="' + classes.join(' ') + '" data-letter="' + option.letter + '" ' + (a.submitted ? 'disabled' : '') + '>';
        optionsHtml += '<strong>' + option.letter + '.</strong> ' + this.escapeHtml(option.text);
        optionsHtml += '</button>';
      });
      optionsHtml += '</div>';

      this.cardNode.innerHTML = [
        '<div class="w3rq-number">Question ' + q.number + ' of ' + this.questions.length + '</div>',
        '<div class="w3rq-prompt">' + prompt + '</div>',
        '<div class="w3rq-type">' + (q.multi ? 'Select all that apply' : 'Select one answer') + '</div>',
        mediaHtml ? '<div class="w3rq-media-wrap">' + mediaHtml + '</div>' : '',
        optionsHtml
      ].join('');

      this.cardNode.querySelectorAll('.w3rq-option').forEach((btn) => {
        btn.addEventListener('click', () => this.selectOption(btn.dataset.letter));
      });

      this.renderFeedback(q, a);
      this.updateHeader();
      this.updateActions();
    },

    renderFeedback(question, answer) {
      if (!answer.submitted) {
        this.feedbackNode.className = 'w3rq-feedback';
        this.feedbackNode.textContent = '';
        return;
      }

      const correctText = question.options.filter((o) => o.correct).map((o) => o.letter + '. ' + o.text).join(' / ');
      if (answer.correct) {
        this.feedbackNode.className = 'w3rq-feedback show good';
        this.feedbackNode.textContent = 'Correct. Nice work.';
      } else {
        this.feedbackNode.className = 'w3rq-feedback show bad';
        this.feedbackNode.textContent = 'Not quite. Correct answer: ' + correctText;
      }
    },

    renderResults() {
      const total = this.questions.length;
      const score = this.getScore();
      const percent = Math.round((score / total) * 100);
      const pass = percent >= this.PASS_PERCENT;

      const missed = [];
      this.questions.forEach((q, idx) => {
        const ans = this.state.answers[idx];
        if (!ans || ans.correct) return;
        const selected = ans.selected.length ? ans.selected.join(', ') : '(none)';
        const correct = q.options.filter((o) => o.correct).map((o) => o.letter).join(', ');
        missed.push({
          number: q.number,
          prompt: q.prompt || 'Question',
          selected,
          correct
        });
      });

      let missedHtml = '';
      if (missed.length) {
        missedHtml = '<div class="w3rq-missed-list">';
        missed.forEach((item) => {
          missedHtml += '<div class="w3rq-missed-item">';
          missedHtml += '<h4>Q' + item.number + ' · ' + this.escapeHtml(item.prompt) + '</h4>';
          missedHtml += '<p><span class="label">Your answer:</span> ' + this.escapeHtml(item.selected) + '</p>';
          missedHtml += '<p><span class="label">Correct:</span> ' + this.escapeHtml(item.correct) + '</p>';
          missedHtml += '<p><span class="label">Study tip:</span> replay the media and compare counters/particles carefully.</p>';
          missedHtml += '</div>';
        });
        missedHtml += '</div>';
      } else {
        missedHtml = '<p>Perfect score. You answered every question correctly.</p>';
      }

      this.resultsNode.innerHTML = [
        '<h3>Week 3 Review Quiz Results</h3>',
        '<div class="w3rq-final">',
        '<div class="w3rq-grade ' + (pass ? 'pass' : 'fail') + '">' + percent + '%</div>',
        '<div>',
        '<p><strong>Score:</strong> ' + score + ' / ' + total + '</p>',
        '<p><strong>Status:</strong> ' + (pass ? 'Pass' : 'Needs review') + ' (target: ' + this.PASS_PERCENT + '%)</p>',
        '<p><strong>Helpful review:</strong> check the missed questions below, then use Reset Quiz to try again.</p>',
        '</div>',
        '</div>',
        '<h4>Questions to review</h4>',
        missedHtml
      ].join('');
      this.resultsNode.classList.add('show');

      this.cardNode.style.display = 'none';
      this.feedbackNode.className = 'w3rq-feedback';
      this.feedbackNode.textContent = '';

      this.prevBtn.disabled = true;
      this.actionBtn.disabled = true;
      this.actionBtn.textContent = 'Completed';
      this.updateHeader();
    },

    selectOption(letter) {
      const q = this.questions[this.state.index];
      const a = this.state.answers[this.state.index];
      if (!q || !a || a.submitted) return;

      if (q.multi) {
        if (a.selected.includes(letter)) {
          a.selected = a.selected.filter((l) => l !== letter);
        } else {
          a.selected = a.selected.concat(letter);
        }
      } else {
        a.selected = [letter];
      }

      this.saveState();
      this.render();
    },

    submitCurrent() {
      const q = this.questions[this.state.index];
      const a = this.state.answers[this.state.index];
      if (!q || !a || !a.selected.length) return;

      const chosen = a.selected.slice().sort().join('|');
      const correct = q.options.filter((o) => o.correct).map((o) => o.letter).sort().join('|');

      a.submitted = true;
      a.correct = chosen === correct;

      this.saveState();
      this.render();
    },

    updateHeader() {
      const answered = this.state.answers.filter((a) => a.submitted).length;
      const total = this.questions.length;
      const score = this.getScore();
      const pct = total > 0 ? Math.round((answered / total) * 100) : 0;

      if (this.progressFill) this.progressFill.style.width = pct + '%';
      if (this.progressLabel) {
        if (this.state.finished) {
          this.progressLabel.textContent = 'Finished · ' + answered + ' of ' + total + ' answered';
        } else {
          this.progressLabel.textContent = 'Question ' + (this.state.index + 1) + ' of ' + total + ' · ' + answered + ' answered';
        }
      }
      if (this.scoreNode) this.scoreNode.textContent = 'Score: ' + score + ' / ' + total;
    },

    updateActions() {
      const a = this.state.answers[this.state.index];
      if (!a) return;

      this.prevBtn.disabled = this.state.index === 0;

      if (!a.submitted) {
        this.actionBtn.textContent = 'Confirm';
        this.actionBtn.disabled = a.selected.length === 0;
        return;
      }

      if (this.state.index === this.questions.length - 1) {
        this.actionBtn.textContent = 'See Results';
      } else {
        this.actionBtn.textContent = 'Next →';
      }
      this.actionBtn.disabled = false;
    },

    createEmptyState() {
      return {
        index: 0,
        finished: false,
        answers: this.questions.map(() => ({
          selected: [],
          submitted: false,
          correct: false
        }))
      };
    },

    loadState() {
      try {
        const raw = localStorage.getItem(this.STORAGE_KEY);
        if (!raw) return this.createEmptyState();
        const parsed = JSON.parse(raw);
        if (!parsed || !Array.isArray(parsed.answers) || parsed.answers.length !== this.questions.length) {
          return this.createEmptyState();
        }
        parsed.index = Math.min(Math.max(parsed.index || 0, 0), this.questions.length - 1);
        return parsed;
      } catch {
        return this.createEmptyState();
      }
    },

    saveState() {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.state));
    },

    getScore() {
      return this.state.answers.reduce((sum, answer) => sum + (answer.correct ? 1 : 0), 0);
    },

    parseQuestions(rawHtml) {
      const questions = [];
      const normalized = rawHtml.replace(/<h3[^>]*>[\s\S]*?<\/h3>/i, '');
      const questionPattern = /(\d+)\)\s*<strong>([\s\S]*?)<\/strong>\s*Explanation:\s*<br\s*\/?>\s*<br\s*\/?>\s*([\s\S]*?)(?=(?:\d+\)\s*<strong>)|$)/gi;

      let match;
      while ((match = questionPattern.exec(normalized)) !== null) {
        const number = Number(match[1]);
        const promptHtml = match[2] || '';
        const optionsHtml = (match[3] || '').replace(/<br\s*\/?>\s*$/i, '');
        const options = this.parseOptions(optionsHtml);
        if (!options.length) continue;

        const media = this.extractMedia(promptHtml);
        const prompt = this.extractPrompt(promptHtml);
        const correctCount = options.filter((o) => o.correct).length;

        questions.push({
          number,
          prompt,
          media,
          options,
          multi: correctCount > 1
        });
      }

      questions.sort((a, b) => a.number - b.number);
      return questions;
    },

    parseOptions(optionsHtml) {
      const options = [];
      const optionPattern = /(<em[^>]*>)?\s*([A-E])\)\s*([\s\S]*?)(?=(?:(?:<\/em>\s*)?(?:<em[^>]*>)?\s*[A-E]\)\s*)|$)/gi;

      let match;
      while ((match = optionPattern.exec(optionsHtml)) !== null) {
        const letter = match[2].toUpperCase();
        const raw = (match[3] || '').trim();
        if (!raw) continue;

        const correct = Boolean(match[1]) || /<em\b/i.test(raw);
        const withoutEmphasis = raw.replace(/<\/?em[^>]*>/gi, '');
        const text = this.normalizeText(this.stripHtml(withoutEmphasis));
        if (!text) continue;

        options.push({ letter, text, correct });
      }

      return options;
    },

    extractPrompt(promptHtml) {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = promptHtml;
      wrapper.querySelectorAll('iframe, video, audio, img').forEach((node) => node.remove());
      return this.normalizeText(wrapper.textContent || 'Choose the correct answer.');
    },

    extractMedia(promptHtml) {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = promptHtml;

      const iframe = wrapper.querySelector('iframe');
      const audio = wrapper.querySelector('audio');
      const image = wrapper.querySelector('img');

      return {
        video: this.resolveVideoSrc(iframe?.getAttribute('src') || ''),
        audio: this.resolveAudioSrc(audio?.getAttribute('src') || ''),
        image: this.resolveImageSrc(image?.getAttribute('src') || '')
      };
    },

    resolveAudioSrc(src) {
      if (!src) return '';
      if (src.startsWith('../audio/')) return src;

      const id = this.extractGoogleFileId(src);
      if (id && this.AUDIO_MAP[id]) return this.AUDIO_MAP[id];
      return src;
    },

    resolveVideoSrc(src) {
      if (!src) return '';
      if (src.startsWith('../videos/')) return src;

      const key = Object.keys(this.VIDEO_MAP).find((token) => src.includes(token));
      return key ? this.VIDEO_MAP[key] : src;
    },

    resolveImageSrc(src) {
      if (!src) return '';
      if (src.startsWith('../images/')) return src;

      const filename = src.split('/').pop()?.split('?')[0] || '';
      if (/^week3_test_question\d+\.jpg$/i.test(filename)) {
        return '../images/week_03/day_15/' + filename;
      }
      return src;
    },

    extractGoogleFileId(url) {
      const match = url.match(/[?&]id=([^&]+)/i);
      return match ? match[1] : '';
    },

    stripHtml(html) {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = html.replace(/<br\s*\/?>/gi, ' ');
      return wrapper.textContent || '';
    },

    normalizeText(text) {
      return (text || '')
        .replace(/\u00a0/g, ' ')
        .replace(/\s+/g, ' ')
        .replace(/\s+([.,!?;:])/g, '$1')
        .trim();
    },

    escapeHtml(text) {
      return (text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    },

    escapeAttr(text) {
      return this.escapeHtml(text).replace(/`/g, '&#96;');
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
    ensureBrandIcons();
    StatusUI.init();
    Theme.init();
    Nav.init();
    Sync.init();
    Progress.init();
    Search.init();
    Quiz.init();
    Week3ReviewQuiz.init();
    Notes.init();
    Bookmarks.init();
    Resume.init();
    registerSW();
  });
})();
