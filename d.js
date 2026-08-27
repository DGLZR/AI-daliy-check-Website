
        const email = '0';
        const serverData = {
            focus: parseFloat('0') || 0,
            todayRecords: parseInt('0') || 0,
            totalRecords: parseInt('0') || 0,
            todayReports: parseInt('0') || 0
        };
        const FOCUS_GOAL = 480;

        let allRecords = [];
        let isPieMode = false;
        let isPercentageMode = false;
        let pieChart = null;
        let currentTimelinePage = 1;
        const timelinePerPage = 15;

        let allReports = [];
        let filteredReports = [];
        let currentReportType = '全部';
        let currentReportPage = 1;
        const reportsPerPage = 5;

        const TYPE_COLORS = {
            '开发': '#a9e34b', '沟通': '#4dabf7', '生活': '#ffa94d', '学习': '#b197fc',
            '设计': '#f783ac', '管理': '#63e6be', '文档': '#9775fa', '娱乐': '#ff6b6b',
            '产品': '#748ffc', '会议': '#ffd43b', '运维': '#868e96', '测试': '#94d82d',
            '数据分析': '#ff922b', '其他': '#6f8a75'
        };

        /* ============ 粒子星空 ============ */
        (function initParticles() {
            const canvas = document.getElementById('particleCanvas');
            const ctx = canvas.getContext('2d');
            let W, H, particles = [];
            const COUNT = 70, LINK_DIST = 130;
            function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
            window.addEventListener('resize', resize); resize();
            for (let i = 0; i < COUNT; i++) {
                particles.push({ x: Math.random()*W, y: Math.random()*H, vx:(Math.random()-0.5)*0.4, vy:(Math.random()-0.5)*0.4, r: Math.random()*1.8+0.6, hue: Math.random()>0.75?'169,227,75':'47,158,68' });
            }
            function draw() {
                ctx.clearRect(0,0,W,H);
                for (let i=0;i<particles.length;i++) for (let j=i+1;j<particles.length;j++) {
                    const a=particles[i], b=particles[j], dx=a.x-b.x, dy=a.y-b.y, dist=Math.sqrt(dx*dx+dy*dy);
                    if (dist < LINK_DIST) { ctx.strokeStyle=`rgba(169,227,75,${(1-dist/LINK_DIST)*0.12})`; ctx.lineWidth=0.6; ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); }
                }
                particles.forEach(p => {
                    p.x+=p.vx; p.y+=p.vy;
                    if (p.x<0||p.x>W) p.vx*=-1; if (p.y<0||p.y>H) p.vy*=-1;
                    ctx.fillStyle=`rgba(${p.hue},0.55)`; ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,Math.PI*2); ctx.fill();
                });
                requestAnimationFrame(draw);
            }
            draw();
        })();

        /* ============ 时钟 / 显现 ============ */
        function tickClock() {
            const el = document.getElementById('liveClock'); if (!el) return;
            const n = new Date();
            el.textContent = `${String(n.getHours()).padStart(2,'0')}:${String(n.getMinutes()).padStart(2,'0')}:${String(n.getSeconds()).padStart(2,'0')}`;
        }
        setInterval(tickClock, 1000); tickClock();

        function initReveal() {
            const obs = new IntersectionObserver(entries => {
                entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
            }, { threshold: 0.06 });
            document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
        }

        /* ============ 计数器 / 专注环 ============ */
        function animateCount(el, target, duration, fmt) {
            const start = performance.now();
            function tick(now) {
                const p = Math.min((now - start) / duration, 1);
                const eased = 1 - Math.pow(1 - p, 3);
                el.textContent = fmt(target * eased);
                if (p < 1) requestAnimationFrame(tick);
            }
            requestAnimationFrame(tick);
        }

        function animateHero() {
            animateCount(document.getElementById('focusRingValue'), serverData.focus, 1300, v => Math.round(v));
            animateCount(document.getElementById('miniTodayRecords'), serverData.todayRecords, 1100, v => Math.round(v));
            animateCount(document.getElementById('miniTotalRecords'), serverData.totalRecords, 1200, v => Math.round(v));
            animateCount(document.getElementById('miniTodayReports'), serverData.todayReports, 1100, v => Math.round(v));
            const pct = Math.min(serverData.focus / FOCUS_GOAL, 1);
            setTimeout(() => { document.getElementById('focusRingFill').style.strokeDashoffset = 439.8 * (1 - pct); }, 250);
        }

        /* ============ 初始化 ============ */
        document.addEventListener('DOMContentLoaded', () => {
            initReveal();
            initDates();
            animateHero();
            loadData();
            loadReports();
            loadTokenStats();
        });

        function initDates() {
            const today = new Date();
            const weekAgo = new Date(today); weekAgo.setDate(weekAgo.getDate() - 7);
            document.getElementById('startDate').value = weekAgo.toISOString().split('T')[0];
            document.getElementById('endDate').value = today.toISOString().split('T')[0];
            ['startDate','endDate'].forEach(id => document.getElementById(id).addEventListener('change', () => { currentTimelinePage = 1; loadData(); }));
            document.getElementById('tagFilter').addEventListener('change', () => { currentTimelinePage = 1; loadData(); });
            document.getElementById('searchInput').addEventListener('input', () => { currentTimelinePage = 1; loadData(); });
        }

        function quickFilter(type) {
            const today = new Date();
            const start = document.getElementById('startDate'), end = document.getElementById('endDate');
            end.value = today.toISOString().split('T')[0];
            if (type === 'today') start.value = today.toISOString().split('T')[0];
            else if (type === 'week') { const d = new Date(today); d.setDate(d.getDate()-7); start.value = d.toISOString().split('T')[0]; }
            else if (type === 'month') { const d = new Date(today); d.setDate(d.getDate()-30); start.value = d.toISOString().split('T')[0]; }
            currentTimelinePage = 1; loadData();
        }

        /* ============ 图表 ============ */
        function toggleChartMode(mode, btn) {
            isPieMode = mode === 'pie';
            document.getElementById('barChart').classList.toggle('active', !isPieMode);
            document.getElementById('pieChart').classList.toggle('active', isPieMode);
            document.querySelectorAll('.seg-mini button').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            updateDistribution();
        }
        function toggleValueMode(btn) {
            isPercentageMode = !isPercentageMode;
            if (btn) btn.querySelector('.vs-text').textContent = isPercentageMode ? '占比' : '时长';
            updateDistribution();
        }

        /* ============ 数据 ============ */
        async function loadData() {
            const startDate = document.getElementById('startDate').value;
            const endDate = document.getElementById('endDate').value;
            const response = await fetch(`/api/user/records/${encodeURIComponent(email)}?start=${startDate}&end=${endDate}`);
            const data = await response.json();
            if (data.success) { allRecords = data.records; updateStats(); updateDistribution(); updateTimeline(); }
        }

        function getFilteredRecords() {
            let records = [...allRecords];
            const tag = document.getElementById('tagFilter').value;
            if (tag !== '全部标签') records = records.filter(r => r['工作类型'] === tag);
            const keyword = document.getElementById('searchInput').value.trim().toLowerCase();
            if (keyword) records = records.filter(r => (r['工作描述'] || '').toLowerCase().includes(keyword));
            return records;
        }

        function updateStats() {
            const records = getFilteredRecords();
            document.getElementById('recordCount').textContent = records.length;
            let totalMinutes = 0;
            records.forEach(r => { totalMinutes += parseFloat(r['持续时长(分钟)'] || 0); });
            document.getElementById('totalDuration').textContent = (totalMinutes / 60).toFixed(1) + 'h';
            const times = records.map(r => r['时间']).filter(t => t);
            document.getElementById('activeTime').textContent = times.length
                ? `${times.reduce((a,b)=>a<b?a:b).substring(0,5)} — ${times.reduce((a,b)=>a>b?a:b).substring(0,5)}`
                : '--:-- — --:--';
        }

        function updateDistribution() {
            const records = getFilteredRecords();
            const typeHours = {}; let totalMinutes = 0;
            records.forEach(r => { const t = r['工作类型'] || '其他'; const m = parseFloat(r['持续时长(分钟)'] || 0); typeHours[t] = (typeHours[t] || 0) + m; totalMinutes += m; });
            const sorted = Object.entries(typeHours).sort((a,b) => b[1] - a[1]);

            const barContainer = document.getElementById('barChart');
            if (sorted.length === 0) {
                barContainer.innerHTML = '<div class="empty-state" style="width:100%"><i class="fas fa-inbox"></i>当前筛选条件下暂无数据</div>';
            } else {
                barContainer.innerHTML = sorted.map(([type, minutes], i) => {
                    const hours = minutes / 60;
                    const pct = totalMinutes > 0 ? (minutes / totalMinutes * 100) : 0;
                    const color = TYPE_COLORS[type] || '#6f8a75';
                    const value = isPercentageMode ? pct.toFixed(1) + '%' : hours.toFixed(1) + 'h';
                    return `<div class="bar-row">
                        <span class="bar-rank">${String(i+1).padStart(2,'0')}</span>
                        <span class="bar-label" style="color:${color}">${type}</span>
                        <div class="bar-track"><div class="bar-fill" data-w="${Math.max(3, pct)}" style="background:${color}"></div></div>
                        <span class="bar-value">${value}</span>
                    </div>`;
                }).join('');
                requestAnimationFrame(() => requestAnimationFrame(() => {
                    barContainer.querySelectorAll('.bar-fill').forEach(f => { f.style.width = f.dataset.w + '%'; });
                }));
            }

            if (isPieMode && sorted.length > 0) {
                const ctx = document.getElementById('pieCanvas').getContext('2d');
                if (pieChart) pieChart.destroy();
                pieChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: sorted.map(([t]) => t),
                        datasets: [{
                            data: sorted.map(([,m]) => isPercentageMode ? (m/totalMinutes*100).toFixed(1) : (m/60).toFixed(1)),
                            backgroundColor: sorted.map(([t]) => TYPE_COLORS[t] || '#6f8a75'),
                            borderWidth: 3, borderColor: '#173624', hoverOffset: 10
                        }]
                    },
                    options: {
                        responsive: true, cutout: '58%',
                        plugins: {
                            legend: { position: 'bottom', labels: { color: '#a8c0ab', padding: 16, font: { size: 12, family: 'Noto Sans SC' }, usePointStyle: true, pointStyle: 'circle' } },
                            tooltip: { callbacks: { label: c => ` ${c.label}: ${c.raw}${isPercentageMode ? '%' : 'h'}` } }
                        }
                    }
                });
            }
        }

        /* ============ Token 格式化 ============ */
        function formatTokenCount(n) {
            n = parseFloat(n) || 0;
            if (n >= 1000000000) return (n / 1000000000).toFixed(1) + 'B';
            if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
            if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
            return String(Math.round(n));
        }
        /* ============ Token 用量 ============ */
        let tokenChartInstances = [];

        function getThemeTokenColors() {
            const cs = getComputedStyle(document.documentElement);
            const light = (cs.getPropertyValue('--green') || '#2f9e44').trim();
            const deep = (cs.getPropertyValue('--green-deep') || '#1f6f31').trim();
            return { light: light, deep: deep };
        }

        async function loadTokenStats() {
            try {
                const response = await fetch(`/api/user/token-stats/${encodeURIComponent(email)}`);
                const data = await response.json();
                if (data.success && data.tokens) {
                    const t = data.tokens;
                    animateCount(document.getElementById('udTokenAllTotal'), t.all_total, 1200, v => formatTokenCount(v));
                    animateCount(document.getElementById('udTokenTodayTotal'), t.today_total, 1200, v => formatTokenCount(v));
                    document.getElementById('udTokenAllAnalysis').textContent = formatTokenCount(t.all_analysis);
                    document.getElementById('udTokenAllReport').textContent = formatTokenCount(t.all_report);
                    document.getElementById('udTokenTodayAnalysis').textContent = formatTokenCount(t.today_analysis);
                    document.getElementById('udTokenTodayReport').textContent = formatTokenCount(t.today_report);
                }
            } catch (e) { console.warn('加载 Token 统计失败', e); }
        }

        function tokenChartOptions(stacked) {
            const cs = getComputedStyle(document.documentElement);
            const axisColor = (cs.getPropertyValue('--txt-faint') || '#6f8a75').trim();
            const gridColor = 'rgba(169,227,75,0.1)';
            return {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 700 },
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { position: 'top', labels: { color: axisColor, font: { size: 11 }, usePointStyle: true, pointStyle: 'circle', boxWidth: 8 } },
                    tooltip: {
                        backgroundColor: 'rgba(12,32,19,0.95)',
                        titleColor: '#ffffff',
                        bodyColor: '#eaf4ea',
                        padding: 12,
                        cornerRadius: 10,
                        callbacks: {
                            label: function(ctx) { return ' ' + ctx.dataset.label + '：' + formatTokenCount(ctx.parsed.y || 0); },
                            afterBody: function(items) {
                                let sum = 0;
                                items.forEach(function(it) { sum += (it.parsed.y || 0); });
                                return ['', ' 总计：' + formatTokenCount(sum)];
                            }
                        }
                    }
                },
                scales: {
                    x: { stacked: !!stacked, grid: { display: false }, ticks: { color: axisColor, font: { size: 11 } } },
                    y: { stacked: !!stacked, grid: { color: gridColor }, ticks: { color: axisColor, font: { size: 11 }, callback: function(v) { return formatTokenCount(v); } } }
                }
            };
        }

        async function toggleTokenCharts() {
            const panel = document.getElementById('tokenChartsPanel');
            const btn = document.getElementById('tokenChartBtn');
            if (!panel) return;
            const isOpening = !panel.classList.contains('open');
            if (isOpening) {
                panel.classList.add('open');
                if (btn) btn.classList.add('open');
                tokenChartInstances.forEach(function(c) { try { c.destroy(); } catch(e) {} });
                tokenChartInstances = [];
                await renderTokenCharts();
            } else {
                panel.classList.remove('open');
                if (btn) btn.classList.remove('open');
            }
        }

        async function renderTokenCharts() {
            try {
                const response = await fetch(`/api/user/token-daily/${encodeURIComponent(email)}`);
                const data = await response.json();
                if (!data.success || !data.daily) return;
                const d = data.daily;
                const colors = getThemeTokenColors();
                const labels = (d.dates || []).map(function(x) { const p = x.split('-'); return p.length === 3 ? (p[1] + '/' + p[2]) : x; });
                const analysisTotal = (d.analysis_input || []).map(function(v, i) { return (v || 0) + (d.analysis_output[i] || 0); });
                const reportTotal = (d.report_input || []).map(function(v, i) { return (v || 0) + (d.report_output[i] || 0); });

                const ov = document.getElementById('tokenOverviewChart');
                if (ov) {
                    tokenChartInstances.push(new Chart(ov, {
                        type: 'bar',
                        data: { labels: labels, datasets: [
                            { label: '截图分析', data: analysisTotal, backgroundColor: colors.light, borderRadius: 5, maxBarThickness: 26 },
                            { label: '报告输出', data: reportTotal, backgroundColor: colors.deep, borderRadius: 5, maxBarThickness: 26 }
                        ] },
                        options: tokenChartOptions(false)
                    }));
                }

                const an = document.getElementById('tokenAnalysisChart');
                if (an) {
                    tokenChartInstances.push(new Chart(an, {
                        type: 'bar',
                        data: { labels: labels, datasets: [
                            { label: '输出', data: d.analysis_output, backgroundColor: colors.deep, maxBarThickness: 34 },
                            { label: '输入', data: d.analysis_input, backgroundColor: colors.light, borderRadius: { topLeft: 5, topRight: 5 }, maxBarThickness: 34 }
                        ] },
                        options: tokenChartOptions(true)
                    }));
                }

                const rp = document.getElementById('tokenReportChart');
                if (rp) {
                    tokenChartInstances.push(new Chart(rp, {
                        type: 'bar',
                        data: { labels: labels, datasets: [
                            { label: '输出', data: d.report_output, backgroundColor: colors.deep, maxBarThickness: 34 },
                            { label: '输入', data: d.report_input, backgroundColor: colors.light, borderRadius: { topLeft: 5, topRight: 5 }, maxBarThickness: 34 }
                        ] },
                        options: tokenChartOptions(true)
                    }));
                }
            } catch (e) { console.warn('渲染 Token 柱状图失败', e); }
        }

        /* ============ 时间线 ============ */
        function updateTimeline() {
            const records = getFilteredRecords().reverse();
            const container = document.getElementById('timelineList');
            const pagination = document.getElementById('timelinePagination');
            if (records.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="fas fa-inbox"></i>暂无记录，调整筛选条件试试</div>';
                pagination.innerHTML = '';
                return;
            }
            const totalPages = Math.ceil(records.length / timelinePerPage);
            if (currentTimelinePage > totalPages) currentTimelinePage = 1;
            const startIdx = (currentTimelinePage - 1) * timelinePerPage;
            const pageRecords = records.slice(startIdx, startIdx + timelinePerPage);

            container.innerHTML = pageRecords.map((record, index) => {
                const time = record['时间'] || ''; const date = record['日期'] || '';
                const workType = record['工作类型'] || '其他'; const description = record['工作描述'] || '';
                const duration = parseFloat(record['持续时长(分钟)'] || 0);
                const tInput = parseInt(record['输入token数'] || 0) || 0;
                const tOutput = parseInt(record['输出token数'] || 0) || 0;
                const tTotal = parseInt(record['消耗token数'] || 0) || 0;
                const color = TYPE_COLORS[workType] || '#6f8a75';
                let timeRange = '';
                if (time && duration > 0) {
                    const [h,m] = time.split(':').map(Number); const endM = h*60 + m + duration;
                    timeRange = `${time.substring(0,5)} — ${String(Math.floor(endM/60)%24).padStart(2,'0')}:${String(Math.floor(endM%60)).padStart(2,'0')}`;
                }
                const dateDisplay = date ? `${date.split('-')[1]}/${date.split('-')[2]}` : '';
                return `<div class="timeline-item" style="animation-delay:${index * 0.04}s">
                    <div class="timeline-time">${dateDisplay}<br>${time.substring(0,5)}</div>
                    <div class="timeline-dot"><div class="dot" style="background:${color}"></div>${index < pageRecords.length - 1 ? '<div class="line"></div>' : ''}</div>
                    <div class="timeline-content">
                        <div class="timeline-body">
                            <div class="timeline-desc">${description || '无描述'}</div>
                            <div class="timeline-tags">
                                <span class="timeline-tag type" style="background:${color}">${workType}</span>
                                <span class="timeline-tag auto"><i class="fas fa-robot"></i> 自动记录</span>
                                ${timeRange ? `<span class="timeline-tag time"><i class="far fa-clock"></i> ${timeRange}</span>` : ''}
                            </div>
                        </div>
                        <span class="token-chip" title="输入 Token：${tInput}&#10;输出 Token：${tOutput}&#10;总消耗：${tTotal}"><i class="fas fa-coins"></i> ${formatTokenCount(tTotal)}</span>
                    </div>
                </div>`;
            }).join('');

            pagination.innerHTML = buildPagination(totalPages, currentTimelinePage, 'goToTimelinePage', records.length);
        }

        function buildPagination(totalPages, current, fnName, total) {
            let html = `<span class="page-info">共 ${total} 条</span>`;
            html += `<button class="page-btn" onclick="${fnName}(${current-1})" ${current===1?'disabled':''}><i class="fas fa-chevron-left"></i></button>`;
            let s = Math.max(1, current - 2), e = Math.min(totalPages, current + 2);
            if (s > 1) { html += `<button class="page-btn" onclick="${fnName}(1)">1</button>`; if (s > 2) html += `<span class="page-info">…</span>`; }
            for (let i = s; i <= e; i++) html += `<button class="page-btn ${i===current?'active':''}" onclick="${fnName}(${i})">${i}</button>`;
            if (e < totalPages) { if (e < totalPages - 1) html += `<span class="page-info">…</span>`; html += `<button class="page-btn" onclick="${fnName}(${totalPages})">${totalPages}</button>`; }
            html += `<button class="page-btn" onclick="${fnName}(${current+1})" ${current===totalPages?'disabled':''}><i class="fas fa-chevron-right"></i></button>`;
            return html;
        }

        function goToTimelinePage(page) {
            const records = getFilteredRecords().reverse();
            const totalPages = Math.ceil(records.length / timelinePerPage);
            if (page < 1 || page > totalPages) return;
            currentTimelinePage = page; updateTimeline();
        }

        /* ============ 报告 ============ */
        async function loadReports() {
            const response = await fetch(`/api/user/reports/${encodeURIComponent(email)}`);
            const data = await response.json();
            if (data.success) {
                allReports = data.reports; filteredReports = [...allReports];
                document.getElementById('reportCountBadge').textContent = allReports.length + ' 份';
                renderReports();
            }
        }

        function filterReportType(type, btn) {
            currentReportType = type;
            document.querySelectorAll('.type-group .type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterReports();
        }

        function filterReports() {
            const keyword = document.getElementById('reportSearch').value.trim().toLowerCase();
            const startDate = document.getElementById('reportStartDate').value;
            const endDate = document.getElementById('reportEndDate').value;
            filteredReports = allReports.filter(r => {
                if (currentReportType !== '全部' && r.type !== currentReportType) return false;
                if (keyword && !r.title.toLowerCase().includes(keyword)) return false;
                if (startDate && r.date < startDate) return false;
                if (endDate && r.date > endDate) return false;
                return true;
            });
            currentReportPage = 1; renderReports();
        }

        function renderReports() {
            const container = document.getElementById('reportList');
            const pagination = document.getElementById('reportPagination');
            const totalPages = Math.ceil(filteredReports.length / reportsPerPage);
            const pageReports = filteredReports.slice((currentReportPage-1)*reportsPerPage, currentReportPage*reportsPerPage);
            if (pageReports.length === 0) {
                container.innerHTML = '<div class="empty-state"><i class="fas fa-file-circle-plus"></i>暂无报告</div>';
                pagination.innerHTML = '';
                return;
            }
            container.innerHTML = pageReports.map((r, i) => `
                <div class="report-item" style="animation-delay:${i * 0.05}s">
                    <div class="report-info">
                        <div class="report-title">${r.title}<span class="report-type-tag ${r.type}">${r.type}</span></div>
                        <div class="report-meta"><span><i class="far fa-calendar"></i> ${r.time || r.date}</span><span><i class="fas fa-pen-nib"></i> ${r.word_count || 0} 字</span><span class="report-token" title="输入 Token：${r.token_input || 0}&#10;输出 Token：${r.token_output || 0}&#10;总消耗：${r.token_total || 0}"><i class="fas fa-coins"></i> ${formatTokenCount(r.token_total || 0)}</span></div>
                    </div>
                    <div class="report-actions">
                        <button class="action-btn view" onclick="viewReport('${r.filename}')"><i class="fas fa-eye"></i> 查看</button>
                        <button class="action-btn copy" onclick="copyReport('${r.filename}')"><i class="fas fa-copy"></i> 复制</button>
                        <button class="action-btn delete" onclick="deleteReport('${r.filename}')"><i class="fas fa-trash"></i></button>
                        <div class="dl-wrap">
                            <button class="action-btn dl"><i class="fas fa-download"></i> 下载 <i class="fas fa-chevron-down" style="font-size:0.6rem;"></i></button>
                            <div class="dl-menu">
                                <button class="dl-pdf" onclick="downloadReport('${r.filename}','pdf')"><i class="fas fa-file-pdf"></i> 下载 PDF</button>
                                <button class="dl-word" onclick="downloadReport('${r.filename}','word')"><i class="fas fa-file-word"></i> 下载 Word</button>
                                <button class="dl-md" onclick="downloadReport('${r.filename}','md')"><i class="fab fa-markdown"></i> 下载 Markdown</button>
                            </div>
                        </div>
                    </div>
                </div>`).join('');
            pagination.innerHTML = totalPages > 1 ? buildPagination(totalPages, currentReportPage, 'goToReportPage', filteredReports.length) : '';
        }

        function goToReportPage(page) {
            const totalPages = Math.ceil(filteredReports.length / reportsPerPage);
            if (page < 1 || page > totalPages) return;
            currentReportPage = page; renderReports();
        }

        async function viewReport(filename) {
            const response = await fetch(`/api/user/report/${encodeURIComponent(email)}/${encodeURIComponent(filename)}`);
            const data = await response.json();
            if (data.success) {
                document.getElementById('modalTitle').textContent = data.title;
                document.getElementById('modalContent').innerHTML = data.content;
                document.getElementById('reportModal').classList.add('active');
            }
        }


        async function downloadReport(filename, format) {
            try {
                const response = await fetch(`/api/user/report/${encodeURIComponent(email)}/${encodeURIComponent(filename)}`);
                const data = await response.json();
                if (!data.success) { alert('获取报告失败'); return; }
                const title = (data.title || filename).replace(/[\\\/:*?"<>|]/g, '_');
                const body = data.content || '';
                if (format === 'pdf') {
                    const el = document.createElement('div');
                    el.style.cssText = "font-family:'Noto Sans SC',sans-serif;line-height:1.9;color:#16301f;padding:24px;max-width:720px;background:#fff;";
                    el.innerHTML = body;
                    document.body.appendChild(el);
                    html2pdf().set({margin:[12,12,12,12],filename:title+'.pdf',image:{type:'jpeg',quality:0.95},html2canvas:{scale:2,useCORS:true},jsPDF:{unit:'mm',format:'a4',orientation:'portrait'}}).from(el).save().then(function(){ document.body.removeChild(el); }).catch(function(){ if(el.parentNode) document.body.removeChild(el); });
                } else {
                    const docHtml = "<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'><head><meta charset='utf-8'><title>"+title+"</title><style>body{font-family:'Noto Sans SC',sans-serif;line-height:1.9;color:#16301f;} table{border-collapse:collapse;} th,td{border:1px solid #999;padding:6px;} h1,h2,h3{color:#1f6f31;} code{background:#f0f0f0;padding:2px 5px;border-radius:3px;}</style></head><body>"+body+"</body></html>";
                    const blob = new Blob(['\ufeff'+docHtml], {type:'application/msword'});
                    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = title+'.doc'; document.body.appendChild(a); a.click(); document.body.removeChild(a);
                    setTimeout(function(){ URL.revokeObjectURL(a.href); }, 2000);
                } else if (format === 'md') {
                    const raw = data.raw || '';
                    const blob = new Blob([raw], {type:'text/markdown;charset=utf-8'});
                    const a2 = document.createElement('a'); a2.href = URL.createObjectURL(blob); a2.download = title+'.md'; document.body.appendChild(a2); a2.click(); document.body.removeChild(a2);
                    setTimeout(function(){ URL.revokeObjectURL(a2.href); }, 2000);
                }
            } catch (e) { alert('下载失败：'+e.message); }
        }
        async function copyReport(filename) {
            const response = await fetch(`/api/user/report/${encodeURIComponent(email)}/${encodeURIComponent(filename)}`);
            const data = await response.json();
            if (data.success) navigator.clipboard.writeText(data.content).then(() => alert('已复制到剪贴板'));
        }

        async function deleteReport(filename) {
            if (!confirm('确定要删除这份报告吗？')) return;
            const response = await fetch(`/api/user/report/${encodeURIComponent(email)}/${encodeURIComponent(filename)}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) { alert('删除成功'); loadReports(); } else { alert('删除失败: ' + data.message); }
        }

        function closeModal() { document.getElementById('reportModal').classList.remove('active'); }
        document.getElementById('reportModal').addEventListener('click', function(e) { if (e.target === this) closeModal(); });

        /* ============ 修改密码 ============ */
        function showChangePasswordModal() {
            document.getElementById('changePasswordModal').classList.add('active');
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
            document.getElementById('changePasswordError').textContent = '';
            document.getElementById('changePasswordSuccess').textContent = '';
        }
        function closeChangePasswordModal() { document.getElementById('changePasswordModal').classList.remove('active'); }
        document.getElementById('changePasswordModal').addEventListener('click', function(e) { if (e.target === this) closeChangePasswordModal(); });

        async function changePassword() {
            const newPassword = document.getElementById('newPassword').value;
            const confirmPassword = document.getElementById('confirmPassword').value;
            const errorEl = document.getElementById('changePasswordError');
            const successEl = document.getElementById('changePasswordSuccess');
            errorEl.textContent = ''; successEl.textContent = '';

            if (!newPassword || !confirmPassword) { errorEl.textContent = '请填写完整信息'; return; }
            if (newPassword.length < 6) { errorEl.textContent = '新密码至少需要 6 位'; return; }
            if (newPassword !== confirmPassword) { errorEl.textContent = '两次输入的新密码不一致'; return; }

            try {
                const response = await fetch('/api/admin/change-user-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, new_password: newPassword })
                });
                const data = await response.json();
                if (data.success) {
                    successEl.textContent = '✓ 密码修改成功！';
                    setTimeout(closeChangePasswordModal, 1500);
                } else { errorEl.textContent = data.message; }
            } catch (e) { errorEl.textContent = '修改失败，请稍后重试'; }
        }

        /* ============ 刷新 / 返回 ============ */
        async function refreshData() {
            const icon = document.getElementById('refreshIcon');
            icon.classList.add('spin');
            await Promise.all([loadData(), loadReports()]);
            const response = await fetch(`/api/admin/user-detail/${encodeURIComponent(email)}`);
            const data = await response.json();
            if (data.success) {
                const u = data.user;
                animateCount(document.getElementById('focusRingValue'), u['今日专注时长(分钟)'] || 0, 900, v => Math.round(v));
                animateCount(document.getElementById('miniTodayRecords'), u['今日记录条数'] || 0, 900, v => Math.round(v));
                animateCount(document.getElementById('miniTotalRecords'), u['总共记录条数'] || 0, 900, v => Math.round(v));
                animateCount(document.getElementById('miniTodayReports'), u['今日生成报告数'] || 0, 900, v => Math.round(v));
                const pct = Math.min((u['今日专注时长(分钟)'] || 0) / FOCUS_GOAL, 1);
                document.getElementById('focusRingFill').style.strokeDashoffset = 439.8 * (1 - pct);
            }
            setTimeout(() => icon.classList.remove('spin'), 600);
        }

        function goBack() { window.location.href = '/superadmin'; }
    