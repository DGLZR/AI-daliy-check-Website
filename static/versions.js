// ==================== 配置 ====================
// GitHub 仓库 releases 实时数据源（公开仓库时前端可直接拉取）
var GITHUB_API = 'https://api.github.com/repos/DGLZR/frog-daliy-check/releases';

// ==================== 粒子背景 ====================
(function () {
    var canvas = document.getElementById('particles');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var W = 0, H = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);
    var particles = [];
    var mouse = { x: -9999, y: -9999, active: false };
    var COLORS = ['#a9e34b', '#3fb950', '#57d46b', '#7fe08a', '#d9ffe0'];

    function resize() {
        W = window.innerWidth; H = window.innerHeight;
        canvas.width = W * dpr; canvas.height = H * dpr;
        canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        initParticles();
    }
    function initParticles() {
        var area = W * H;
        var count = Math.min(90 + Math.floor(area / 30000), 150);
        particles = [];
        for (var i = 0; i < count; i++) {
            particles.push({
                x: Math.random() * W, y: Math.random() * H,
                vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35,
                r: Math.random() * 1.8 + 0.7,
                c: COLORS[Math.floor(Math.random() * COLORS.length)],
                baseAlpha: Math.random() * 0.5 + 0.25,
                tw: Math.random() * 0.02 + 0.005, ph: Math.random() * Math.PI * 2
            });
        }
    }
    var t = 0;
    function draw() {
        t += 0.02;
        ctx.clearRect(0, 0, W, H);
        var i, j, p, pa, pb, dx, dy, d2, d;
        for (i = 0; i < particles.length; i++) {
            p = particles[i];
            p.x += p.vx; p.y += p.vy;
            if (mouse.active) {
                var mx = p.x - mouse.x, my = p.y - mouse.y;
                var md2 = mx * mx + my * my;
                if (md2 < 160 * 160 && md2 > 1) {
                    var md = Math.sqrt(md2), f = (160 - md) / 160 * 0.8;
                    p.x += (mx / md) * f; p.y += (my / md) * f;
                }
            }
            if (p.x < -20) p.x = W + 20; else if (p.x > W + 20) p.x = -20;
            if (p.y < -20) p.y = H + 20; else if (p.y > H + 20) p.y = -20;
        }
        var LINK = 120;
        for (i = 0; i < particles.length; i++) {
            pa = particles[i];
            for (j = i + 1; j < particles.length; j++) {
                pb = particles[j];
                dx = pa.x - pb.x; dy = pa.y - pb.y; d2 = dx * dx + dy * dy;
                if (d2 < LINK * LINK) {
                    d = Math.sqrt(d2);
                    ctx.strokeStyle = 'rgba(169, 227, 75,' + ((1 - d / LINK) * 0.35).toFixed(3) + ')';
                    ctx.lineWidth = 1; ctx.beginPath();
                    ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
                }
            }
        }
        if (mouse.active) {
            for (i = 0; i < particles.length; i++) {
                p = particles[i];
                dx = p.x - mouse.x; dy = p.y - mouse.y; d2 = dx * dx + dy * dy;
                if (d2 < 180 * 180) {
                    d = Math.sqrt(d2);
                    ctx.strokeStyle = 'rgba(169, 227, 75,' + ((1 - d / 180) * 0.5).toFixed(3) + ')';
                    ctx.lineWidth = 1; ctx.beginPath();
                    ctx.moveTo(mouse.x, mouse.y); ctx.lineTo(p.x, p.y); ctx.stroke();
                }
            }
        }
        for (i = 0; i < particles.length; i++) {
            p = particles[i];
            var twinkle = 0.6 + 0.4 * Math.sin(t * p.tw * 100 + p.ph);
            ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = p.c; ctx.globalAlpha = p.baseAlpha * twinkle;
            ctx.fill(); ctx.globalAlpha = 1;
        }
        requestAnimationFrame(draw);
    }
    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', function (e) { mouse.x = e.clientX; mouse.y = e.clientY; mouse.active = true; });
    window.addEventListener('mouseleave', function () { mouse.active = false; mouse.x = -9999; mouse.y = -9999; });
    window.addEventListener('touchmove', function (e) { if (e.touches.length) { mouse.x = e.touches[0].clientX; mouse.y = e.touches[0].clientY; mouse.active = true; } }, { passive: true });
    window.addEventListener('touchend', function () { mouse.active = false; });
    resize(); requestAnimationFrame(draw);
})();

// ==================== 工具函数 ====================
function formatSize(bytes) {
    if (!bytes || bytes <= 0) return '';
    var units = ['B', 'KB', 'MB', 'GB'];
    var n = bytes, i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return n.toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
}

var TYPE_CLASS = {
    '新增': 'chg-new', '优化': 'chg-opt', '修复': 'chg-fix', '调整': 'chg-adj', '更新': 'chg-upd'
};

function changeBadge(type) {
    var cls = TYPE_CLASS[type] || 'chg-upd';
    return '<span class="chg-type ' + cls + '">' + type + '</span>';
}

function channelClass(channel) {
    return channel === '内测版' || channel === '预发布' ? ' beta' : '';
}

function detectType(text) {
    if (/新增|加入|添加|支持|上线|引入|首发|发布/.test(text)) return '新增';
    if (/修复|修正|解决|bug|崩溃|闪退|异常/i.test(text)) return '修复';
    if (/优化|改进|提升|增强|加快|完善|美化|提速/.test(text)) return '优化';
    if (/调整|变更|更改|移除|删除|废弃/.test(text)) return '调整';
    return '更新';
}

function cleanText(s) {
    return (s || '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/[*_`~]/g, '').trim();
}

function parseReleaseBody(body) {
    var result = { summary: '', changes: [] };
    if (!body) return result;
    var lines = body.split(/\r?\n/);
    var summaryParts = [];
    for (var i = 0; i < lines.length; i++) {
        var t = lines[i].trim();
        if (!t) continue;
        if (/^#{1,6}\s/.test(t)) continue;
        var m = t.match(/^[-*+]\s+(.+)$/);
        var m2 = t.match(/^\d+[.)]\s+(.+)$/);
        if (m || m2) {
            var text = cleanText(m ? m[1] : m2[1]);
            if (text) result.changes.push({ type: detectType(text), text: text });
        } else {
            var c = cleanText(t);
            if (c) summaryParts.push(c);
        }
    }
    result.summary = summaryParts.join(' ');
    return result;
}

function formatChinaDate(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    var china = new Date(d.getTime() + 8 * 3600 * 1000);
    function pad(n) { return n < 10 ? '0' + n : '' + n; }
    return china.getUTCFullYear() + '-' + pad(china.getUTCMonth() + 1) + '-' + pad(china.getUTCDate());
}

function pickAsset(assets) {
    if (!assets || !assets.length) return null;
    var exts = ['.exe', '.zip', '.7z', '.rar', '.msi', '.dmg'];
    for (var i = 0; i < exts.length; i++) {
        for (var j = 0; j < assets.length; j++) {
            var n = (assets[j].name || '').toLowerCase();
            if (n.indexOf(exts[i]) !== -1) return assets[j];
        }
    }
    return assets[0];
}

function githubToVersion(g) {
    var tag = (g.tag_name || '').trim();
    var name = (g.name || '').trim();
    var parsed = parseReleaseBody(g.body);
    var asset = pickAsset(g.assets);
    var title = (name && !/^v?\d+(\.\d+)*$/.test(name)) ? name : tag;
    return {
        version: tag || 'v0',
        date: formatChinaDate(g.published_at),
        title: title || tag || '版本',
        channel: g.prerelease ? '预发布' : '稳定版',
        summary: parsed.summary || ('本次发布共包含 ' + parsed.changes.length + ' 项改动。'),
        changes: parsed.changes,
        download_url: asset ? asset.browser_download_url : null,
        size: asset ? (asset.size || 0) : 0,
        is_current: false,
        html_url: g.html_url || null
    };
}

// ==================== 数据加载 ====================
async function fetchGitHubReleases() {
    try {
        var res = await fetch(GITHUB_API, { headers: { 'Accept': 'application/vnd.github+json' } });
        if (!res.ok) return null;
        var data = await res.json();
        if (!Array.isArray(data) || !data.length) return null;
        return data.filter(function (r) { return !r.draft; }).map(function (g, i) {
            var v = githubToVersion(g);
            v.is_current = (i === 0);
            return v;
        });
    } catch (err) {
        console.warn('GitHub releases 拉取失败，回退到本地数据:', err);
        return null;
    }
}

async function loadVersions() {
    try {
        var res = await fetch('/api/versions');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        var data = await res.json();
        if (!data.success || !data.versions) throw new Error('bad data');
        renderAll(data.versions, 'github');
    } catch (err) {
        console.error('加载版本历史失败:', err);
        showError();
    }
}

function renderAll(versions, source) {
    renderHeroStats(versions);
    renderCurrent(versions[0]);
    renderTimeline(versions);
    renderSource(source, versions.length);
}

// ==================== 渲染 ====================
function renderHeroStats(versions) {
    var count = versions.length;
    var latest = versions[0] ? versions[0].version : '—';
    var first = versions[versions.length - 1] ? versions[versions.length - 1].date : '—';

    document.getElementById('latestVersion').textContent = latest;

    var firstDateEl = document.getElementById('firstDate');
    if (first && first !== '—') {
        var parts = first.split('-');
        if (parts.length === 3) firstDateEl.textContent = parts[0] + '.' + parts[1] + '.' + parts[2];
        else firstDateEl.textContent = first;
    }
    animateNumber(document.getElementById('versionCount'), count, 1400);
}

function renderCurrent(v) {
    var card = document.getElementById('currentCard');
    if (!v) { card.innerHTML = '<div class="current-loading"><p>暂无版本记录</p></div>'; return; }
    var sizeText = formatSize(v.size);
    var changes = (v.changes || []).map(function (c) { return '<li>' + changeBadge(c.type) + '<span>' + c.text + '</span></li>'; }).join('');
    var downloadHtml = v.download_url
        ? '<a class="btn-download" href="' + v.download_url + '" target="_blank" rel="noopener"><i class="fas fa-download"></i> 下载 ' + v.version + '</a>'
        : '<span class="tl-archived">该版本暂无安装包</span>';
    card.innerHTML =
        '<div class="current-head">' +
            '<span class="current-version">' + v.version + '</span>' +
            '<span class="latest-badge"><i class="fas fa-star"></i> 最新版本</span>' +
            '<span class="current-date"><i class="far fa-calendar-alt"></i> ' + (v.datetime || v.date) + '</span>' +
        '</div>' +
        '<h3 class="current-title">' + v.title + '</h3>' +
        '<p class="current-summary">' + v.summary + '</p>' +
        '<ul class="tl-changes">' + changes + '</ul>' +
        '<div class="current-actions">' + downloadHtml + (sizeText ? '<span class="current-size"><i class="fas fa-hdd"></i> ' + sizeText + '</span>' : '') + '</div>';
}

function renderTimeline(versions) {
    var container = document.getElementById('timelineItems');
    if (!container) return;
    container.innerHTML = '';
    versions.forEach(function (v, i) {
        var item = document.createElement('article');
        item.className = 'tl-item reveal';
        var sizeText = formatSize(v.size);
        var changes = (v.changes || []).map(function (c) { return '<li>' + changeBadge(c.type) + '<span>' + c.text + '</span></li>'; }).join('');
        var foot = v.download_url
            ? '<a class="tl-download" href="' + v.download_url + '" target="_blank" rel="noopener"><i class="fas fa-download"></i> 下载安装包</a>' + (sizeText ? '<span class="tl-size">' + sizeText + '</span>' : '')
            : '<span class="tl-archived"><i class="fas fa-box-archive"></i> 该版本暂无安装包</span>';
        item.innerHTML =
            '<div class="tl-node"><span class="tl-dot"></span></div>' +
            '<div class="tl-card' + (v.is_current ? ' is-current' : '') + '">' +
                '<div class="tl-meta">' +
                    '<span class="tl-version">' + v.version + '</span>' +
                    '<span class="tl-channel' + channelClass(v.channel) + '">' + v.channel + '</span>' +
                    '<span class="tl-date">' + (v.datetime || v.date) + '</span>' +
                '</div>' +
                '<h3 class="tl-title">' + v.title + '</h3>' +
                '<p class="tl-summary">' + v.summary + '</p>' +
                '<ul class="tl-changes">' + changes + '</ul>' +
                '<div class="tl-foot">' + foot + '</div>' +
            '</div>';
        container.appendChild(item);
    });
    initReveal();
}

function renderSource(source, count) {
    var el = document.getElementById('sourceIndicator');
    if (!el) return;
    if (source === 'github') {
        el.innerHTML = '<i class="fab fa-github"></i> 已同步 GitHub Releases · ' + count + ' 个版本（含发布时间）';
        el.className = 'source-indicator si-github';
    } else {
        el.innerHTML = '<i class="fas fa-database"></i> 已加载版本数据 · ' + count + ' 个版本';
        el.className = 'source-indicator si-local';
    }
}

function showError() {
    var card = document.getElementById('currentCard');
    card.innerHTML = '<div class="current-loading"><p><i class="fas fa-exclamation-triangle"></i> 加载失败，请刷新页面重试</p></div>';
    var items = document.getElementById('timelineItems');
    if (items) items.innerHTML = '';
    var el = document.getElementById('sourceIndicator');
    if (el) el.innerHTML = '<i class="fas fa-plug-circle-xmark"></i> 版本数据加载失败';
}

// ==================== 数字滚动动画 ====================
function animateNumber(el, target, duration) {
    var start = performance.now();
    function tick(now) {
        var p = Math.min((now - start) / duration, 1);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased);
        if (p < 1) requestAnimationFrame(tick); else el.textContent = target;
    }
    requestAnimationFrame(tick);
}

// ==================== 滚动显现 ====================
function initReveal() {
    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry, i) {
            if (entry.isIntersecting) {
                setTimeout(function () { entry.target.classList.add('visible'); }, (i % 4) * 80);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('.reveal:not(.visible)').forEach(function (el) { observer.observe(el); });
}

// ==================== 进度条 / 导航 / 回到顶部 ====================
function initScroll() {
    var progressBar = document.getElementById('progressBar');
    var navbar = document.querySelector('.navbar');
    var backTop = document.getElementById('backTop');
    window.addEventListener('scroll', function () {
        var scrollTop = window.scrollY;
        var docHeight = document.documentElement.scrollHeight - window.innerHeight;
        var pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
        if (progressBar) progressBar.style.width = pct + '%';
        if (navbar) navbar.classList.toggle('scrolled', scrollTop > 40);
        if (backTop) backTop.classList.toggle('show', scrollTop > 500);
    }, { passive: true });
    if (backTop) backTop.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function () {
    initScroll();
    initReveal();
    loadVersions();
});
