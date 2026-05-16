/* ── PYQNova — app.js ───────────────────────────────────────────────────── */

/* ── MathJax Config (must be before MathJax CDN loads) ─────────────────── */
window.MathJax = {
  tex: { inlineMath: [['\\(', '\\)'], ['$', '$']], displayMath: [['\\[', '\\]'], ['$$', '$$']] },
  options: { skipHtmlTags: ['script', 'noscript', 'style', 'textarea'] },
  startup: { typeset: false }
};

/* ── LocalStorage Progress Manager ─────────────────────────────────────── */
const Progress = {
  key: 'pyqnova_progress',

  load() {
    try { return JSON.parse(localStorage.getItem(this.key) || '{}'); }
    catch { return {}; }
  },

  save(data) {
    try { localStorage.setItem(this.key, JSON.stringify(data)); }
    catch { }
  },

  markSolved(chapter, questionId, isCorrect) {
    const d = this.load();
    if (!d[chapter]) d[chapter] = { solved: [], correct: 0, total: 0 };
    if (!d[chapter].solved.includes(questionId)) {
      d[chapter].solved.push(questionId);
      d[chapter].total++;
      if (isCorrect) d[chapter].correct++;
    }
    this.save(d);
  },

  getChapterProgress(chapter) {
    const d = this.load();
    return d[chapter] || { solved: [], correct: 0, total: 0 };
  },

  getTotalSolved() {
    const d = this.load();
    return Object.values(d).reduce((sum, c) => sum + (c.total || 0), 0);
  },

  getStreak() {
    try {
      const raw = localStorage.getItem('pyqnova_streak');
      return raw ? JSON.parse(raw) : { days: [], count: 0 };
    } catch { return { days: [], count: 0 }; }
  },

  recordToday() {
    const streak = this.getStreak();
    const today = new Date().toISOString().slice(0, 10);
    if (!streak.days.includes(today)) {
      streak.days.push(today);
      streak.count = streak.days.slice(-30).length;
      localStorage.setItem('pyqnova_streak', JSON.stringify(streak));
    }
  }
};

/* ── Toast Notification ─────────────────────────────────────────────────── */
function toast(message, type = 'info') {
  const colors = { info: '#14B8A6', success: '#34D399', error: '#F43F5E', warn: '#F97316' };
  const el = document.getElementById('toast');
  if (!el) return;
  el.innerHTML = `<span style="color:${colors[type]};margin-right:8px;">●</span>${message}`;
  el.classList.add('show');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), 3000);
}

/* ── Removed renderMath in favor of global typesetPromise ── */

/* ── Chapter Progress Bars (chapters.html) ──────────────────────────────── */
function initChapterProgress() {
  document.querySelectorAll('[data-chapter]').forEach(card => {
    const slug = card.dataset.chapter;
    const p = Progress.getChapterProgress(slug);
    const total = parseInt(card.dataset.total || 0);
    const pct = total > 0 ? Math.round(p.total / total * 100) : 0;

    const bar = card.querySelector('.progress-fill');
    if (bar) { bar.style.width = '0%'; setTimeout(() => bar.style.width = pct + '%', 100); }

    const label = card.querySelector('.progress-label');
    if (label) label.textContent = `${p.total}/${total} solved`;

    const badge = card.querySelector('.solved-badge');
    if (badge && p.total > 0) { badge.textContent = pct + '%'; badge.style.display = 'inline-flex'; }
  });
}

/* ── Dashboard Stats ────────────────────────────────────────────────────── */
function initDashboard() {
  const el = document.getElementById('personal-solved');
  if (el) el.textContent = Progress.getTotalSolved().toLocaleString();
  Progress.recordToday();

  const streak = Progress.getStreak();
  const streakEl = document.getElementById('streak-count');
  if (streakEl) streakEl.textContent = streak.count;

  // Render streak dots (last 7 days)
  const dotsEl = document.getElementById('streak-dots');
  if (dotsEl) {
    const days = streak.days || [];
    const labels = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
    const now = new Date();
    dotsEl.innerHTML = labels.map((l, i) => {
      const d = new Date(now); d.setDate(now.getDate() - (6 - i));
      const ds = d.toISOString().slice(0, 10);
      const done = days.includes(ds);
      return `<div class="streak-dot${done ? ' done' : ''}">${done ? '✓' : l}</div>`;
    }).join('');
  }

  // Progress chart
  const ctx = document.getElementById('progressChart');
  if (ctx && window.Chart) {
    const data = { Physics: 0, Chemistry: 0, Biology: 0 };
    const prog = Progress.load();
    Object.values(prog).forEach(c => {
      // crude subject detection not available in localStorage — just show totals
    });
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Solved', 'Remaining'],
        datasets: [{
          data: [Progress.getTotalSolved(), Math.max(0, 6521 - Progress.getTotalSolved())],
          backgroundColor: ['#14B8A6', 'rgba(255,255,255,0.06)'],
          borderColor: ['#14B8A6', 'rgba(255,255,255,0.04)'],
          borderWidth: 2,
        }]
      },
      options: {
        cutout: '72%',
        plugins: {
          legend: { display: false }, tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.parsed.toLocaleString()} questions`
            }
          }
        },
        animation: { duration: 1200, easing: 'easeInOutQuart' }
      }
    });
  }
}

/* ── Practice Page Logic ────────────────────────────────────────────────── */
const Practice = {
  chapter: null,
  questions: [],
  currentIndex: 0,
  answered: false,
  timer: null,
  seconds: 0,
  total: 0,
  page: 1,

  // Global status store — page change hone pe bhi survive karta hai
  questionStatuses: {},  // { globalIndex: 'correct'|'wrong'|'skipped'|'unseen' }
  pillOffset: 0,         // pill window ka starting index
  PILL_VISIBLE: 13,      // ek baar mein kitne pills dikhein

  async init(chapter) {
    this.chapter = chapter;

    if (window.USER_LOGGED_IN) {
      try {
        const res = await fetch(`/api/progress/chapter/${chapter}`);
        if (res.ok) {
          const data = await res.json();
          const key = `pyqnova_ans_${this.chapter}`;
          const localAns = JSON.parse(localStorage.getItem(key) || '{}');
          let changed = false;
          
          for (const [qId, prog] of Object.entries(data.progress)) {
            if (!localAns[qId] && prog.status) {
              // We infer the answer state. If 'correct', selected == correct.
              // If 'wrong', we just store it. _restoreAnsweredUI expects correct/selected.
              // For a wrong answer fetched from DB, we don't know correctKey until questions load,
              // but we store what we know so it renders as answered.
              localAns[qId] = {
                selected: prog.selected_option,
                correct: prog.status === 'correct' ? prog.selected_option : null,
                solutionShown: true // Show solution since they answered it on another device
              };
              changed = true;
            }
          }
          if (changed) localStorage.setItem(key, JSON.stringify(localAns));
        }
      } catch(e) { console.error('Error fetching progress:', e); }
    }

    this.loadStatuses();
    this.pillOffset = 0;
    this.questionStatuses = this.questionStatuses || {};
    
    // Check URL parameters for direct question linking
    const urlParams = new URLSearchParams(window.location.search);
    const targetQ = urlParams.get('q');
    
    if (targetQ !== null) {
      const globalIndex = parseInt(targetQ, 10);
      if (!isNaN(globalIndex) && globalIndex >= 0) {
        const targetPage = Math.floor(globalIndex / 20) + 1;
        const targetIndex = globalIndex % 20;
        await this.loadQuestions(targetPage, targetIndex);
        return;
      }
    }
    
    const state = this.loadState();
    if (state) {
      await this.loadQuestions(state.page || 1, state.index || 0);
    } else {
      await this.loadQuestions(1, 0);
    }
  },

  saveState() {
    try {
      localStorage.setItem(`pyqnova_last_${this.chapter}`, JSON.stringify({
        page: this.page,
        index: this.currentIndex
      }));
    } catch { }
  },

  // Save the answer the user gave for a specific question
  saveAnswerState(qId, selectedKey, correctKey, solutionShown = false) {
    try {
      const key = `pyqnova_ans_${this.chapter}`;
      const all = JSON.parse(localStorage.getItem(key) || '{}');
      all[qId] = { selected: selectedKey, correct: correctKey, solutionShown };
      localStorage.setItem(key, JSON.stringify(all));

      // Async sync to backend
      if (window.USER_LOGGED_IN) {
        fetch('/api/progress/upsert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question_id: qId.toString(),
            status: selectedKey === correctKey ? 'correct' : 'wrong',
            selected_option: selectedKey
          })
        }).catch(e => console.error("Sync error:", e));
      }
    } catch { }
  },

  // Load saved answer for a question ID
  loadAnswerState(qId) {
    try {
      const key = `pyqnova_ans_${this.chapter}`;
      const all = JSON.parse(localStorage.getItem(key) || '{}');
      return all[qId] || null;
    } catch { return null; }
  },

  // Save a pending (pre-check) selection so nav doesn't lose the highlight
  savePendingSelection(qId, selectedKey) {
    try {
      const key = `pyqnova_pending_${this.chapter}`;
      const all = JSON.parse(localStorage.getItem(key) || '{}');
      all[qId] = selectedKey;
      localStorage.setItem(key, JSON.stringify(all));
    } catch { }
  },

  loadPendingSelection(qId) {
    try {
      const key = `pyqnova_pending_${this.chapter}`;
      const all = JSON.parse(localStorage.getItem(key) || '{}');
      return all[qId] || null;
    } catch { return null; }
  },

  clearPendingSelection(qId) {
    try {
      const key = `pyqnova_pending_${this.chapter}`;
      const all = JSON.parse(localStorage.getItem(key) || '{}');
      delete all[qId];
      localStorage.setItem(key, JSON.stringify(all));
    } catch { }
  },

  loadState() {
    try {
      return JSON.parse(localStorage.getItem(`pyqnova_last_${this.chapter}`)) || null;
    } catch {
      return null;
    }
  },

  async loadQuestions(page = 1, startingIndex = 0) {
    const yearFilter = document.getElementById('year-filter')?.value || '';
    const url = `/api/questions/${this.chapter}?page=${page}&limit=20${yearFilter ? '&year=' + yearFilter : ''}`;
    try {
      const res = await fetch(url);
      const data = await res.json();
      this.questions = data.questions || [];
      this.total = data.total || 0;
      this.page = page;
      this.currentIndex = startingIndex < this.questions.length ? startingIndex : 0;
      this.answered = false;

      // Patch missing correct keys from DB fetched progress
      const key = `pyqnova_ans_${this.chapter}`;
      const localAns = JSON.parse(localStorage.getItem(key) || '{}');
      let patched = false;
      this.questions.forEach(q => {
        if (localAns[q.id] && localAns[q.id].correct === null) {
          const correctOpt = q.options && q.options.find(o => o.is_correct);
          if (correctOpt) {
            localAns[q.id].correct = correctOpt.key;
            patched = true;
          }
        }
      });
      if (patched) localStorage.setItem(key, JSON.stringify(localAns));


      // Populate year filter on first load
      if (page === 1 && data.years) this.populateYears(data.years);

      this.saveState();
      this.render();
      this.updatePagination(data.page, data.pages);
    } catch (e) {
      document.getElementById('question-area').innerHTML = '<p style="color:var(--muted);padding:20px">Failed to load questions. Is the server running?</p>';
    }
  },

  populateYears(years) {
    const sel = document.getElementById('year-filter');
    if (!sel || sel.options.length > 1) return;
    years.forEach(y => { const o = document.createElement('option'); o.value = y; o.textContent = y; sel.appendChild(o); });
  },

  render() {
    if (!this.questions.length) {
      document.getElementById('question-area').innerHTML = '<p style="color:var(--muted);padding:40px;text-align:center">No questions found for this filter.</p>';
      return;
    }
    const q = this.questions[this.currentIndex];
    this.answered = false;
    this._selected = null;

    this.startTimer();
    this.renderQuestion(q);

    // Restore answered state OR pending (pre-check) selection
    const savedAns = this.loadAnswerState(q.id);
    if (savedAns) {
      this._selected  = savedAns.selected;
      this._correct   = savedAns.correct;
      this._qId       = q.id;
      this.answered   = true;
      this._restoreAnsweredUI(savedAns.selected, savedAns.correct, savedAns);
    } else {
      // Reset button to default state for a fresh question
      const checkBtn = document.getElementById('btn-check');
      if (checkBtn) {
        checkBtn.textContent = 'Check Answer';
        checkBtn.onclick = () => Practice.checkAnswer();
        checkBtn.disabled = false;
        checkBtn.style.opacity = '';
        checkBtn.classList.add('btn-primary');
        checkBtn.classList.remove('btn-outline');
      }
      // Restore pre-check highlight if user had selected but not checked
      const pending = this.loadPendingSelection(q.id);
      if (pending) {
        this._selected = pending;
        this._qId = q.id;
        const btn = document.getElementById(`opt-${pending}`);
        if (btn) btn.classList.add('selected');
      }
    }

    const qNum = document.getElementById('q-number-display');
    const qYear = document.getElementById('q-year-display');
    const displayIndex = (this.page - 1) * 20 + this.currentIndex + 1;
    if (qNum) qNum.textContent = `Q ${displayIndex}`;
    if (qYear) qYear.textContent = `NEET ${q.year || ''}`;

    this._alignPillOffset();
    this.renderPills();
    
    // Update Bookmark icon state
    this.updateBookmarkIcon(q.id);
  },

  async updateBookmarkIcon(qId) {
    const icon = document.getElementById('bookmark-icon');
    if (!icon) return;
    icon.setAttribute('fill', 'none'); // default outline
    icon.style.color = 'currentColor';
    try {
      const res = await fetch(`/api/notebooks/question/${qId}`);
      const data = await res.json();
      if (data.saved) {
        icon.setAttribute('fill', '#1DD4C0');
        icon.style.color = '#1DD4C0';
      }
    } catch(e) {}
  },

  // Restore option highlights + solution panel without triggering any side-effects
  _restoreAnsweredUI(selectedKey, correctKey, savedAns = null) {
    const isCorrect = selectedKey === correctKey;
    document.querySelectorAll('.option-btn').forEach(b => {
      const k = b.id.replace('opt-', '');
      const badge = document.getElementById(`badge-${k}`);
      if (badge) { badge.className = 'opt-badge'; badge.innerHTML = ''; }

      if (k === correctKey) {
        b.classList.add('correct');
        if (badge) {
          if (k === selectedKey) {
            badge.innerHTML = `<div class="badge-icon green-tick"><i data-lucide="check" style="width:12px;height:12px"></i></div><span>You marked</span>`;
            badge.classList.add('marked');
          } else {
            badge.innerHTML = `<div class="badge-icon green-tick"><i data-lucide="check" style="width:12px;height:12px"></i></div>`;
            badge.classList.add('unmarked');
          }
        }
      } else if (k === selectedKey && !isCorrect) {
        b.classList.add('wrong');
        if (badge) {
          badge.innerHTML = `<div class="badge-icon red-cross"><i data-lucide="x" style="width:12px;height:12px"></i></div><span>You marked</span>`;
          badge.classList.add('marked');
        }
      } else {
        b.classList.add('dimmed');
      }
    });
    if (window.lucide) lucide.createIcons();

    // Restore button text — if solution was shown, set 'Show Solution' as already done
    const btn = document.getElementById('btn-check');
    if (btn) {
      if (savedAns && savedAns.solutionShown) {
        btn.textContent = 'Solution Shown';
        btn.disabled = true;
        btn.style.opacity = '0.6';
        // Show solution panel immediately
        const sp = document.getElementById('solution-panel');
        sp?.classList.add('show');
        if (window.MathJax && MathJax.typesetPromise && sp) {
          MathJax.typesetPromise([sp]).catch(err => console.error(err));
        }
      } else {
        // answered but solution not yet shown — show 'Show Solution'
        btn.textContent = 'Show Solution';
        btn.onclick = () => Practice.showSolution();
      }
    }
  },

  autoBlendImage(img) {
    if (!img.complete) {
      img.onload = () => this.autoBlendImage(img);
      return;
    }
    const canvas = document.createElement('canvas');
    canvas.width = img.naturalWidth || img.width;
    canvas.height = img.naturalHeight || img.height;
    if (canvas.width === 0) return;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0);
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    let r = 0, g = 0, b = 0;
    for (let i = 0, l = data.length; i < l; i += 4) {
      r += data[i]; g += data[i + 1]; b += data[i + 2];
    }
    const avg = (r + g + b) / (3 * (data.length / 4));
    if (avg < 60) {
      img.classList.add('invert-mode');
    }
  },

  renderQuestion(q) {
    console.log("Current Question Data:", q);
    const area = document.getElementById('question-area');
    if (!area) return;

    // Unescape LaTeX utility to handle double backslashes from DB
    const unescapeLatex = (str) => {
      if (!str || typeof str !== 'string') return str;
      let s = str.replace(/\\\\/g, '\\');
      // Fix MathJax parsing error where ~ is invalid inside \mathrm{}
      s = s.replace(/\\mathrm\{([^}]*)\}/g, (match, inner) => {
        return '\\mathrm{' + inner.replace(/~/g, ' ') + '}';
      });
      // Convert $$...$$ display math to inline \(...\) so it renders in option spans
      // (display math blocks break inline flow)
      s = s.replace(/\$\$([^$]+)\$\$/g, (m, inner) => {
        // keep multiline / complex display math as-is if it has \n
        if (inner.includes('\n') || inner.length > 80) return m;
        return '\\(' + inner.trim() + '\\)';
      });
      return s;
    };

    const qText = unescapeLatex(q.question_text || '');
    const qSol = (() => {
      let rawSol = unescapeLatex(q.solution || 'Solution not available.');

      // Step 0: Remove empty \(\) — cause red MathJax errors
      rawSol = rawSol.replace(/\\\(\s*\\\)/g, '');

      // Step 1: Convert $$\bullet$$ to bullet marker
      rawSol = rawSol.replace(/\$\$\\bullet\$\$/g, '\n__BULLET__');

      // ── CRITICAL: Extract multi-line display math blocks BEFORE any \n split ──
      // $$ \begin{aligned} ... \end{aligned} $$ must stay as ONE atomic block
      // otherwise \n split will tear opening $$ from closing $$ into separate <p> tags
      // and MathJax will never find the delimiter pair
      const displayBlocks = [];
      rawSol = rawSol.replace(/\$\$([\s\S]*?)\$\$/g, (m, inner) => {
        const trimmed = inner.trim();
        // Multi-line OR contains \begin{...} → keep as display math block
        if (trimmed.includes('\n') || /\\begin\{/.test(trimmed) || trimmed.length > 80) {
          const idx = displayBlocks.length;
          displayBlocks.push(m);
          return `\n__DISPLAYMATH_${idx}__\n`;
        }
        // Short single-line → convert to inline
        return `\\(${trimmed}\\)`;
      });

      // Step 3: Split and trim
      let lines = rawSol.split('\n').map(l => l.trim()).filter(l => l);

      // Step 4: Smart orphan joining — NEVER merge lines containing DISPLAYMATH tokens
      const visualLen = s => s.replace(/\\\(.*?\\\)/g, 'X').replace(/\s+/g, ' ').trim().length;

      const joined = [];
      for (let i = 0; i < lines.length; i++) {
        const l = lines[i];
        // Never join display math placeholders or bullets
        const isDisplayToken = /DISPLAYMATH/.test(l);
        if (isDisplayToken || l.startsWith('__BULLET__')) {
          joined.push(l);
          continue;
        }
        const vl = visualLen(l);
        const isOrphan = vl < 10
          && !/^\(?\d+\)/.test(l)
          && !/^[A-D]\./.test(l);
        const prevLine = joined[joined.length - 1] || '';
        const prevHasToken = /DISPLAYMATH/.test(prevLine);
        const prevEndsOpen = joined.length > 0
          && !prevHasToken
          && !/[.!?:,]$/.test(prevLine.replace(/\\\(.*?\\\)/g, '').trim());
        if (joined.length > 0 && !prevHasToken && (isOrphan || (vl < 20 && prevEndsOpen))) {
          joined[joined.length - 1] += ' ' + l;
        } else {
          joined.push(l);
        }
      }

      // Step 5: Render
      return joined.map(line => {
        // Restore display math blocks — match exact placeholder OR placeholder embedded in text
        const dmExact = /^__DISPLAYMATH_(\d+)__$/.exec(line);
        if (dmExact) {
          const math = displayBlocks[parseInt(dmExact[1])];
          return `<div style="overflow-x:auto;margin:16px 0;padding:8px 0;text-align:center">${math}</div>`;
        }
        // Fallback: if joiner somehow merged text around the placeholder, split and restore
        if (/DISPLAYMATH/.test(line)) {
          return line.replace(/__DISPLAYMATH_(\d+)__/g, (_, idx) => {
            const math = displayBlocks[parseInt(idx)];
            return `<span style="display:block;overflow-x:auto;margin:16px 0;padding:8px 0;text-align:center">${math}</span>`;
          });
        }

        // Bullet items
        if (line.startsWith('__BULLET__')) {
          const text = line.replace('__BULLET__', '').trim();
          return `<div style="display:flex;gap:10px;align-items:flex-start;margin:8px 0;padding:10px 14px;background:rgba(20,184,166,0.04);border-left:3px solid var(--teal);border-radius:0 8px 8px 0"><span style="color:var(--teal);font-size:18px;line-height:1;flex-shrink:0;margin-top:2px">•</span><span style="flex:1">${text}</span></div>`;
        }

        // Pure math line: \(...\) only — standalone equation, generous margin
        if (/^\\\(.*\\\)[.,;]?$/.test(line)) {
          return `<div style="margin:14px 0 10px 0;font-size:15px;line-height:1.8">${line}</div>`;
        }

        // Equation step: starts with \(
        if (/^\\\(/.test(line) && line.length < 200) {
          return `<div style="margin:10px 0;line-height:1.8">${line}</div>`;
        }

        // Numbered reference dim text
        if (/^\.*\s*\(\d+\)/.test(line)) {
          return `<p style="margin:2px 0;font-size:12px;color:rgba(255,255,255,0.4)">${line}</p>`;
        }

        // "Therefore" conclusion
        if (/^therefore/i.test(line)) {
          return `<p style="margin:16px 0 6px 0;line-height:1.75">${line}</p>`;
        }

        // Section keywords: where/so/given/hence/thus
        if (/^(where,?|so,?|given|now,?|hence|thus)/i.test(line)) {
          return `<p style="margin:14px 0 6px 0;line-height:1.75">${line}</p>`;
        }

        return `<p style="margin:6px 0;line-height:1.75">${line}</p>`;
      }).join('');
    })();




    let qTextHtml = qText;
    if (q.match_list_parsed) {
      const p = q.match_list_parsed;
      let rowsHtml = '';
      p.rows.forEach((row, i) => {
        const isLast = (i === p.rows.length - 1);
        const rowBg = (i % 2 !== 0) ? 'background: rgba(30,41,59,0.5)' : 'background: rgba(30,41,59,0.25)';
        const borderB = !isLast ? 'border-bottom: 1px solid rgba(71,85,105,0.5);' : '';

        rowsHtml += `
            <div style="display: grid; grid-template-columns: 1fr 1fr; ${borderB} ${rowBg}">
                <div style="display: flex; align-items: start; gap: 12px; padding: 14px 20px; border-right: 1px solid rgba(71,85,105,0.5);">
                    ${row.left_key ? `<span style="flex-shrink:0; width:28px; height:28px; border-radius:50%; background:rgba(20,184,166,0.15); border:1px solid rgba(20,184,166,0.3); display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; color:var(--teal)">${row.left_key}</span>` : ''}
                    <span style="font-size:14px; color:#F1F5F9; line-height:1.6; padding-top:4px;">${unescapeLatex(row.left_val)}</span>
                </div>
                <div style="display: flex; align-items: start; gap: 12px; padding: 14px 20px;">
                    ${row.right_key ? `<span style="flex-shrink:0; width:28px; height:28px; border-radius:50%; background:rgba(168,85,247,0.15); border:1px solid rgba(168,85,247,0.3); display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; color:#c084fc">${row.right_key}</span>` : ''}
                    <span style="font-size:14px; color:#F1F5F9; line-height:1.6; padding-top:4px;">${unescapeLatex(row.right_val)}</span>
                </div>
            </div>`;
      });

      qTextHtml = `
        <div style="margin-bottom: 24px;">
            <div style="display:inline-flex; align-items:center; gap:8px; padding:6px 12px; border-radius:8px; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.25); margin-bottom:16px;">
                <svg style="width:14px; height:14px; color:#fbbf24" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"/></svg>
                <span style="font-size:12px; font-weight:600; letter-spacing:0.1em; color:#fbbf24; text-transform:uppercase;">Match The Column</span>
            </div>

            <div style="border-radius:12px; overflow:hidden; border:1px solid rgba(71,85,105,0.4); box-shadow:0 10px 15px -3px rgba(0,0,0,0.1); margin-bottom: 12px;">
                <div style="display: grid; grid-template-columns: 1fr 1fr;">
                    <div style="background: rgba(13,148,136,0.15); padding: 12px 20px; border-bottom: 1px solid rgba(71,85,105,0.4); border-right: 1px solid rgba(71,85,105,0.4);">
                        <p style="font-size:12px; font-weight:700; letter-spacing:0.1em; color:var(--teal); text-transform:uppercase;">List — I</p>
                        <p style="font-size:12px; color:#94a3b8; margin-top:4px">${p.col1_header}</p>
                    </div>
                    <div style="background: rgba(168,85,247,0.15); padding: 12px 20px; border-bottom: 1px solid rgba(71,85,105,0.4);">
                        <p style="font-size:12px; font-weight:700; letter-spacing:0.1em; color:#c084fc; text-transform:uppercase;">List — II</p>
                        <p style="font-size:12px; color:#94a3b8; margin-top:4px">${p.col2_header}</p>
                    </div>
                </div>
                ${rowsHtml}
            </div>
            ${p.footer ? `<p style="font-size:13px; color:#94a3b8; font-style:italic;">${p.footer}</p>` : ''}
        </div>
        `;
    }

  const imgHtml = q.question_image
  ? `<div class="question-figure-container">
      <img src="${q.question_image}"
     </div>`
  : '';

    const optsImgHtml = null
      ? `<div class="question-figure-container" style="margin-bottom: 20px;">
           <img src="${q.options_image_url}" alt="Options Figure" class="question-figure option-image" onload="Practice.autoBlendImage(this)" onerror="this.style.display='none'">
         </div>`
      : '';

    const optHtml = Object.entries(q.options || {}).map(([k, v]) => {
      // Unescape option text before checking if it's an image
      let optContent = unescapeLatex(v);
      if (optContent && (typeof optContent === 'string') && (optContent.startsWith('extracted_images/') || optContent.endsWith('.png') || optContent.endsWith('.jpg') || optContent.endsWith('.jpeg'))) {
     let srcPath = optContent.startsWith('http') ? optContent : `https://dmfvojxpcxqndfudwhmy.supabase.co/storage/v1/object/public/question-images/${optContent.split('/').pop()}`;
        optContent = `<img src="${srcPath}" class="option-image" onload="Practice.autoBlendImage(this)">`;
      }
      return `<button class="option-btn" id="opt-${k}" onclick="Practice.selectAnswer('${k}', '${q.correct_answer}', '${q.id}')">
        <span class="option-label">${k}</span>
        <div class="option-body">
          <span class="option-content">${optContent}</span>
          <div class="opt-badge" id="badge-${k}"></div>
        </div>
      </button>`;
    }).join('');

    const solImgHtml = q.solution_image
      ? `<div class="question-figure-container">
           <img src="${q.solution_image_url}" alt="Solution Figure" class="question-figure" onerror="this.style.display='none'">
         </div>`
      : '';

    area.innerHTML = `
      <div class="question-card card ${this._navDirection === 'left' ? 'slide-left' : ''}">
        <div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap">
          <span class="badge badge-teal">${q.subject?.toUpperCase() || ''}</span>
          <span class="badge badge-coral">NEET ${q.year || ''}</span>
          ${q.data_quality === 'high' ? '<span class="badge badge-violet">★ High Quality</span>' : ''}
        </div>
        <div class="question-text" id="q-text">${qTextHtml}</div>
        ${imgHtml}
        ${optsImgHtml}
        <div class="options-grid" id="options-grid">${optHtml}</div>
        <div class="solution-panel" id="solution-panel">
          <p style="font-weight:700;color:var(--teal);margin-bottom:8px">✅ Solution</p>
          <div style="font-size:14px;line-height:1.7" id="solution-text">${qSol}</div>
          ${solImgHtml}
        </div>
      </div>
    `;
    
    this._navDirection = null;

    if (window.MathJax && MathJax.typesetPromise) {
      MathJax.typesetPromise([area]).catch(err => console.error('MathJax error:', err));
    }
  },

  selectAnswer(key, correct, qId) {
    if (this.answered) return;
    document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
    const btn = document.getElementById(`opt-${key}`);
    if (btn) btn.classList.add('selected');
    this._selected = key;
    this._correct = correct;
    this._qId = qId;
    // Persist selection immediately so navigating away doesn't lose it
    this.savePendingSelection(qId, key);
  },

  checkAnswer() {
    if (this.answered) return;
    if (!this._selected) { toast('Please select an answer first!', 'warn'); return; }
    this.answered = true;
    if (this.timer) clearInterval(this.timer);

    const isCorrect = this._selected === this._correct;

    document.querySelectorAll('.option-btn').forEach(b => {
      const k = b.id.replace('opt-', '');
      const badge = document.getElementById(`badge-${k}`);
      if (badge) { badge.className = 'opt-badge'; badge.innerHTML = ''; }

      if (k === this._correct) {
        b.classList.add('correct');
        if (badge) {
          if (k === this._selected) {
            badge.innerHTML = `
              <div class="badge-icon green-tick animate-pop-in">
                <i data-lucide="check" style="width:12px;height:12px"></i>
              </div>
              <span>You marked</span>
            `;
            badge.classList.add('marked');
          } else {
            badge.innerHTML = `
              <div class="badge-icon green-tick animate-pop-in">
                <i data-lucide="check" style="width:12px;height:12px"></i>
              </div>
            `;
            badge.classList.add('unmarked');
          }
        }
      } else if (k === this._selected && !isCorrect) {
        b.classList.add('wrong');
        if (badge) {
          badge.innerHTML = `
            <div class="badge-icon red-cross animate-pop-in">
              <i data-lucide="x" style="width:12px;height:12px"></i>
            </div>
            <span>You marked</span>
          `;
          badge.classList.add('marked');
        }
      } else {
        b.classList.add('dimmed');
      }
    });
    if (window.lucide) lucide.createIcons();

    // ── Do NOT show solution yet — change button to 'Show Solution' ──
    const btn = document.getElementById('btn-check');
    if (btn) {
      btn.textContent = 'Show Solution';
      btn.onclick = () => Practice.showSolution();
      // Swap colour to a neutral outline style
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-outline');
    }

    Progress.markSolved(this.chapter, this._qId, isCorrect);

    // Persist — solutionShown is false at this point
    this.saveAnswerState(this._qId, this._selected, this._correct, false);
    this.clearPendingSelection(this._qId);

    const currentGlobal = (this.page - 1) * 20 + this.currentIndex;
    if (isCorrect) {
      this.setQuestionStatus(currentGlobal, 'correct');
    } else {
      this.setQuestionStatus(currentGlobal, 'wrong');
    }

    toast(isCorrect ? '🎉 Correct! Great job!' : `❌ Incorrect. Answer: ${this._correct}`, isCorrect ? 'success' : 'error');
  },

  showSolution() {
    const solutionPanel = document.getElementById('solution-panel');
    solutionPanel?.classList.add('show');

    if (window.MathJax && MathJax.typesetPromise && solutionPanel) {
      MathJax.typesetPromise([solutionPanel]).catch(err => console.error(err));
    }

    // Update button to disabled 'Solution Shown'
    const btn = document.getElementById('btn-check');
    if (btn) {
      btn.textContent = 'Solution Shown';
      btn.disabled = true;
      btn.style.opacity = '0.6';
    }

    // Persist that solution is now visible
    if (this._qId) {
      this.saveAnswerState(this._qId, this._selected, this._correct, true);
    }
  },

  async navigate(delta) {
    this._navDirection = delta > 0 ? 'right' : 'left';
    
    // Agar current question unanswered hai aur user skip kar raha hai
    const currentGlobal = (this.page - 1) * 20 + this.currentIndex;
    if (!this.answered && !this.questionStatuses[currentGlobal]) {
      this.setQuestionStatus(currentGlobal, 'skipped');
    }

    let target = this.currentIndex + delta;

    if (target >= 20 || (target >= this.questions.length && this.page < Math.ceil(this.total / 20))) {
      // Need next page
      if (this.page < Math.ceil(this.total / 20)) {
        let newIndex = target % 20;
        await this.loadQuestions(this.page + 1, newIndex);
      } else {
        toast('You reached the end of the questions!', 'info');
      }
    } else if (target < 0) {
      // Need prev page
      if (this.page > 1) {
        let newIndex = 20 + target; // target is negative
        await this.loadQuestions(this.page - 1, newIndex);
      } else {
        toast('You are at the first question!', 'info');
      }
    } else {
      // Within same page
      if (target < this.questions.length) {
        this.currentIndex = target;
        this.saveState();
        this.answered = false;
        this._selected = null;
        this.render();
        this._alignPillOffset();
        this.renderPills();
      } else {
        toast('You reached the end of the questions!', 'info');
      }
    }
  },

  // ── View All Qs Drawer ─────────────────────────────────────────────────────
  _vaqFilter: 'all',   // active filter: all | correct | wrong | unattempted
  _vaqAllQs: [],       // full question list (id, year, globalIndex)

  async viewAll() {
    // Fetch ALL questions for this chapter (no pagination)
    let allQs = this._vaqAllQs;
    if (!allQs.length) {
      try {
        const res = await fetch(`/api/questions/${this.chapter}?page=1&limit=9999`);
        const data = await res.json();
        allQs = (data.questions || []).map((q, i) => ({
          id: q.id, year: q.year, globalIndex: i
        }));
        this._vaqAllQs = allQs;
      } catch {
        toast('Failed to load question list', 'error');
        return;
      }
    }

    this._vaqFilter = 'all';
    this._renderViewAll();

    // Show drawer
    const overlay = document.getElementById('viewall-overlay');
    const drawer  = document.getElementById('viewall-drawer');
    overlay.style.display = 'block';
    drawer.style.display  = 'flex';
    requestAnimationFrame(() => { drawer.style.transform = 'translateX(0)'; });

    // Chapter name
    const cn = document.getElementById('vaq-chapter-name');
    if (cn) cn.textContent = this.chapter.replace(/_/g,' ').replace(/\b\w/g, c => c.toUpperCase());
  },

  closeViewAll() {
    const drawer  = document.getElementById('viewall-drawer');
    const overlay = document.getElementById('viewall-overlay');
    if (drawer) {
      drawer.style.transform = 'translateX(100%)';
      setTimeout(() => {
        drawer.style.display  = 'none';
        overlay.style.display = 'none';
      }, 280);
    }
  },

  resetProgress() {
    if (!confirm('Reset all progress for this chapter? This cannot be undone.')) return;
    // Clear answer states
    localStorage.removeItem(`pyqnova_ans_${this.chapter}`);
    // Clear question statuses
    localStorage.removeItem(`pyqnova_statuses_${this.chapter}`);
    this.questionStatuses = {};
    this._vaqAllQs = [];
    this.closeViewAll();
    toast('Progress reset!', 'info');
    this.render();
    this.renderPills();
  },

  _renderViewAll() {
    const allQs = this._vaqAllQs;
    const filter = this._vaqFilter;

    // Build counts for filter tabs
    const counts = { all: allQs.length, correct: 0, wrong: 0, unattempted: 0 };
    allQs.forEach(q => {
      const s = this.questionStatuses[q.globalIndex];
      if (s === 'correct') counts.correct++;
      else if (s === 'wrong') counts.wrong++;
      else counts.unattempted++;
    });

    // Filter tabs HTML
    const tabs = [
      { key: 'all',         label: `All (${counts.all})`,              color: '#14B8A6' },
      { key: 'wrong',       label: `Incorrect (${counts.wrong})`,       color: '#F43F5E' },
      { key: 'correct',     label: `Correct (${counts.correct})`,       color: '#34D399' },
      { key: 'unattempted', label: `Not Attempted (${counts.unattempted})`, color: '#94A3B8' },
    ];

    const filtersEl = document.getElementById('vaq-filters');
    filtersEl.innerHTML = tabs.map(t => {
      const active = filter === t.key;
      return `<button
        onclick="Practice._setVaqFilter('${t.key}')"
        style="
          padding:6px 12px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;
          border:1.5px solid ${active ? t.color : 'rgba(255,255,255,0.12)'};
          background:${active ? t.color + '22' : 'transparent'};
          color:${active ? t.color : 'var(--muted)'};
          display:flex;align-items:center;gap:5px;
          transition:all 0.15s;
        ">
        ${active ? `<span style="font-size:9px">✓</span>` : ''}${t.label}
      </button>`;
    }).join('');

    // Filter questions
    const filtered = allQs.filter(q => {
      if (filter === 'all') return true;
      const s = this.questionStatuses[q.globalIndex];
      if (filter === 'correct') return s === 'correct';
      if (filter === 'wrong')   return s === 'wrong';
      if (filter === 'unattempted') return s !== 'correct' && s !== 'wrong';
      return true;
    });

    // Group by year
    const byYear = {};
    filtered.forEach(q => {
      const yr = q.year || 'Unknown';
      if (!byYear[yr]) byYear[yr] = [];
      byYear[yr].push(q);
    });
    const years = Object.keys(byYear).sort((a, b) => b - a);

    // Current question global index
    const currentGlobal = (this.page - 1) * 20 + this.currentIndex;

    // Render year groups
    const body = document.getElementById('vaq-body');
    body.innerHTML = years.map(yr => {
      const qs = byYear[yr];
      const pills = qs.map(q => {
        const s = this.questionStatuses[q.globalIndex];
        const isCurrent = q.globalIndex === currentGlobal;
        let bg = 'rgba(255,255,255,0.07)';
        let color = 'var(--text)';
        let border = '1.5px solid rgba(255,255,255,0.1)';
        if (isCurrent) { bg = 'rgba(255,255,255,0.12)'; border = '2px solid #fff'; color = '#fff'; }
        else if (s === 'correct') { bg = '#1D9E7520'; border = '1.5px solid #1D9E75'; color = '#1D9E75'; }
        else if (s === 'wrong')   { bg = '#E24B4A20'; border = '1.5px solid #E24B4A'; color = '#E24B4A'; }
        else if (s === 'skipped') { bg = '#EF9F2720'; border = '1.5px solid #EF9F27'; color = '#EF9F27'; }

        return `<button
          onclick="Practice._vaqGoTo(${q.globalIndex})"
          title="Question ${q.globalIndex + 1} · ${q.year}"
          style="
            width:36px;height:36px;border-radius:50%;
            background:${bg};border:${border};color:${color};
            font-size:12px;font-weight:700;cursor:pointer;
            display:flex;align-items:center;justify-content:center;
            transition:all 0.15s;
            ${isCurrent ? 'transform:scale(1.1);' : ''}
          "
        >${q.globalIndex + 1}</button>`;
      }).join('');

      return `<div>
        <div style="font-size:13px;font-weight:700;color:var(--muted);margin-bottom:10px;letter-spacing:0.5px">${yr}</div>
        <div style="display:flex;flex-wrap:wrap;gap:8px">${pills}</div>
      </div>`;
    }).join('');

    if (!years.length) {
      body.innerHTML = '<p style="color:var(--muted);text-align:center;margin-top:40px">No questions match this filter.</p>';
    }
  },

  _setVaqFilter(f) {
    this._vaqFilter = f;
    this._renderViewAll();
  },

  async _vaqGoTo(globalIndex) {
    this.closeViewAll();
    await this.goToGlobalQuestion(globalIndex);
  },



  startTimer() {
    this.seconds = 0;
    if (this.timer) clearInterval(this.timer);
    this.timer = setInterval(() => {
      this.seconds++;
      const m = String(Math.floor(this.seconds / 60)).padStart(2, '0');
      const s = String(this.seconds % 60).padStart(2, '0');
      const el = document.getElementById('timer-text');
      if (el) el.textContent = `${m}:${s}`;
    }, 1000);
  },

  async goToGlobalQuestion(globalIndex) {
    if (globalIndex < 0 || globalIndex >= this.total) return;
    const targetPage = Math.floor(globalIndex / 20) + 1;
    const localIndex = globalIndex % 20;

    if (this.page === targetPage) {
      this.currentIndex = localIndex;
      this.saveState();
      this.answered = false;
      this._selected = null;
      this.render();
      this._alignPillOffset();
      this.renderPills();
    } else {
      await this.loadQuestions(targetPage, localIndex);
    }
  },

  scrollPills(delta) {
    const maxOffset = Math.max(0, this.total - this.PILL_VISIBLE);
    this.pillOffset = Math.max(0, Math.min(
      this.pillOffset + delta,
      maxOffset
    ));
    this.renderPills();
  },

  setQuestionStatus(globalIndex, status) {
    this.questionStatuses[globalIndex] = status;
    // localStorage mein save karo taaki page reload pe survive kare
    localStorage.setItem(
      `pyqnova_status_${this.chapter}`,
      JSON.stringify(this.questionStatuses)
    );
    this.renderPills();
  },

  loadStatuses() {
    const saved = localStorage.getItem(`pyqnova_status_${this.chapter}`);
    if (saved) {
      try { this.questionStatuses = JSON.parse(saved); }
      catch (e) { this.questionStatuses = {}; }
    }
  },

  renderPills() {
    const container = document.getElementById('pill-container');
    if (!container) return;
    container.innerHTML = '';

    // Current global index calculate karo
    const currentGlobal = (this.page - 1) * 20 + this.currentIndex;

    // pill window slice
    const start = this.pillOffset;
    const end = Math.min(start + this.PILL_VISIBLE, this.total);

    for (let g = start; g < end; g++) {
      const isCurrent = g === currentGlobal;
      const status = isCurrent
        ? 'current'
        : (this.questionStatuses[g] || 'unseen');

      const pill = document.createElement('div');
      pill.className = `pill pill--${status}`;
      pill.textContent = g + 1;
      pill.setAttribute('aria-label', `Question ${g + 1}, ${status}`);
      pill.addEventListener('click', () => this.goToGlobalQuestion(g));
      container.appendChild(pill);
    }

    // Fade edge pills when more questions exist off-screen
    const hasLeft  = start > 0;
    const hasRight = end < this.total;
    const pills = container.querySelectorAll('.pill');
    if (hasLeft && pills.length > 0) {
      pills[0].classList.add('pill--edge-fade');
    }
    if (hasRight && pills.length > 0) {
      pills[pills.length - 1].classList.add('pill--edge-fade');
    }

    // Meta row update
    const numEl = document.getElementById('meta-qnum');
    const yearEl = document.getElementById('meta-year');
    if (numEl) numEl.textContent = currentGlobal + 1;
    if (yearEl && this.questions[this.currentIndex]) {
      yearEl.textContent = this.questions[this.currentIndex].year || '';
    }
  },

  _alignPillOffset() {
    const currentGlobal = (this.page - 1) * 20 + this.currentIndex;
    const mid = Math.floor(this.PILL_VISIBLE / 2);
    const maxOffset = Math.max(0, this.total - this.PILL_VISIBLE);
    this.pillOffset = Math.max(0, Math.min(
      currentGlobal - mid,
      maxOffset
    ));
  },

  goToQuestion(index) {
    if (index >= 0 && index < this.questions.length) {
      this.currentIndex = index;
      this.saveState();
      this.render();
    }
  },

  prev() {
    this.navigate(-1);
  },

  next() {
    this.navigate(1);
  },

  updatePagination(page, pages) {
    // We repurpose updatePagination to do nothing since we use renderTopPagination now
  }
};

/* ── DOMContentLoaded bootstrap ─────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const page = document.body.dataset.page;
  if (page === 'dashboard') initDashboard();
  if (page === 'chapters') initChapterProgress();
  if (page === 'practice') {
    const chapter = document.body.dataset.chapter;
    if (chapter) Practice.init(chapter);
  }
});

/* ── Global Toast ──────────────────────────────────────────────────────── */
window.toast = function(msg, type='info') {
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.position = 'fixed';
  t.style.bottom = '20px';
  t.style.left = '50%';
  t.style.transform = 'translateX(-50%)';
  t.style.padding = '12px 24px';
  t.style.background = type === 'error' ? '#E24B4A' : type === 'warn' ? '#EF9F27' : '#1D9E75';
  t.style.color = '#fff';
  t.style.borderRadius = '8px';
  t.style.zIndex = '9999';
  t.style.fontSize = '14px';
  t.style.fontWeight = '600';
  t.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
  document.body.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transition = 'opacity 0.3s ease';
    setTimeout(() => t.remove(), 300);
  }, 2700);
};

/* ── NotebookPanel ─────────────────────────────────────────────────── */
const NotebookPanel = {
  currentQuestionId: null,
  selectedNotebooks: new Set(),
  selectedTags: new Set(),
  allTags: ['Easy', 'Tricky', 'Do Again', 'Hard'],
  notebooks: [],

  async open(questionId) {
    if (!questionId) { toast('Question load ho raha hai...', 'warn'); return; }
    this.currentQuestionId = questionId;
    this.selectedNotebooks = new Set();
    this.selectedTags = new Set();

    // Check if already saved
    try {
      const res = await fetch(`/api/notebooks/question/${questionId}`);
      const data = await res.json();
      if (data.saved) {
        data.entries.forEach(e => {
          this.selectedNotebooks.add(e.notebook_id);
          (e.tags || []).forEach(t => this.selectedTags.add(t));
        });
        document.getElementById('nb-note').value = data.entries[0]?.note || '';
      } else {
        document.getElementById('nb-note').value = '';
      }
    } catch(e) {}

    // Q info update karo
    const q = Practice.questions[Practice.currentIndex];
    document.getElementById('nb-q-info').textContent = 
      q ? `Q${Practice.currentIndex + 1} · NEET ${q.year || ''}` : questionId;

    await this.loadNotebooks();
    this.renderTags();

    // Panel show karo
    document.getElementById('nb-overlay').style.display = 'block';
    const panel = document.getElementById('nb-panel');
    panel.style.display = 'flex';
    requestAnimationFrame(() => { panel.style.transform = 'translateX(0)'; });

    // Bookmark icon filled karo
    const icon = document.getElementById('bookmark-icon');
    if (icon) icon.setAttribute('fill', 'currentColor');
  },

  close() {
    const panel = document.getElementById('nb-panel');
    if (panel) {
      panel.style.transform = 'translateX(100%)';
      setTimeout(() => {
        panel.style.display = 'none';
        document.getElementById('nb-overlay').style.display = 'none';
      }, 280);
    }
  },

  async loadNotebooks() {
    try {
      const res = await fetch('/api/notebooks/');
      const data = await res.json();
      this.notebooks = data.notebooks || [];
      this.renderNotebooks();
    } catch(e) { console.error('Notebooks load failed', e); }
  },

  renderNotebooks() {
    const list = document.getElementById('nb-list');
    if (!list) return;
    list.innerHTML = this.notebooks.map(nb => {
      const checked = this.selectedNotebooks.has(nb.id);
      return `<label style="display:flex;align-items:center;gap:10px;cursor:pointer;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07)">
        <input type="checkbox" value="${nb.id}" ${checked ? 'checked' : ''}
          onchange="NotebookPanel.toggleNotebook(${nb.id}, this.checked)"
          style="width:16px;height:16px;accent-color:#1DD4C0;cursor:pointer">
        <span style="font-size:14px;color:#E8EDF5;font-weight:500">${nb.name}</span>
        <span style="margin-left:auto;width:10px;height:10px;border-radius:50%;background:${nb.color}"></span>
      </label>`;
    }).join('');
  },

  toggleNotebook(id, checked) {
    if (checked) this.selectedNotebooks.add(id);
    else this.selectedNotebooks.delete(id);
  },

  renderTags() {
    const row = document.getElementById('nb-tags-row');
    if (!row) return;
    row.innerHTML = this.allTags.map(tag => {
      const active = this.selectedTags.has(tag);
      return `<button onclick="NotebookPanel.toggleTag('${tag}')" id="tag-btn-${tag}" style="
        padding:6px 16px;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;
        border:1.5px solid ${active ? '#1DD4C0' : 'rgba(255,255,255,0.15)'};
        background:${active ? 'rgba(29,212,192,0.15)' : 'rgba(255,255,255,0.04)'};
        color:${active ? '#1DD4C0' : '#A0AABA'};
        transition:all 0.15s;font-family:'Plus Jakarta Sans',sans-serif
      ">${tag}</button>`;
    }).join('');
  },

  toggleTag(tag) {
    if (this.selectedTags.has(tag)) this.selectedTags.delete(tag);
    else this.selectedTags.add(tag);
    this.renderTags();
  },

  showCreate() {
    const wrap = document.getElementById('nb-create-wrap');
    if (wrap) { wrap.style.display = 'flex'; document.getElementById('nb-new-name').focus(); }
  },

  async createNotebook() {
    const nameEl = document.getElementById('nb-new-name');
    const name = nameEl.value.trim();
    if (!name) { toast('Notebook ka naam do!', 'warn'); return; }
    try {
      const res = await fetch('/api/notebooks/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, color: '#1DD4C0' })
      });
      const nb = await res.json();
      this.notebooks.push(nb);
      this.selectedNotebooks.add(nb.id);
      this.renderNotebooks();
      nameEl.value = '';
      document.getElementById('nb-create-wrap').style.display = 'none';
      toast(`"${name}" notebook bana diya! ✅`, 'success');
    } catch(e) { toast('Error creating notebook', 'error'); }
  },

  async save() {
    if (this.selectedNotebooks.size === 0) {
      toast('Koi notebook select karo!', 'warn'); return;
    }
    const note = document.getElementById('nb-note').value.trim();
    try {
      await fetch('/api/notebooks/save-question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: this.currentQuestionId,
          notebook_ids: [...this.selectedNotebooks],
          note,
          tags: [...this.selectedTags]
        })
      });
      toast('Saved to Notebook! 🔖', 'success');
      this.close();
      // Bookmark icon filled rakhna
      const icon = document.getElementById('bookmark-icon');
      if (icon) icon.setAttribute('fill', 'currentColor');
    } catch(e) { toast('Save failed!', 'error'); }
  }
};

document.addEventListener('DOMContentLoaded', () => {
  // Background Sync to PostgreSQL for first-time login
  if (window.USER_LOGGED_IN && !localStorage.getItem('pyqnova_synced_to_db')) {
    const allProgress = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith('pyqnova_ans_')) {
        try {
          const val = JSON.parse(localStorage.getItem(key));
          for (const [qId, data] of Object.entries(val)) {
            allProgress.push({
              qId: qId,
              status: data.selected === data.correct ? 'correct' : 'wrong',
              selected_option: data.selected
            });
          }
        } catch(e) {}
      }
    }
    if (allProgress.length > 0) {
      fetch('/api/progress/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ progress: allProgress })
      }).then(res => {
        if (res.ok) localStorage.setItem('pyqnova_synced_to_db', 'true');
      }).catch(e => console.error('Sync fail:', e));
    } else {
      localStorage.setItem('pyqnova_synced_to_db', 'true');
    }
  }
});
