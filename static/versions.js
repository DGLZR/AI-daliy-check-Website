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
        W = window.innerWidth;
        H = window.innerHeight;
        canvas.width = W * dpr;
        canvas.height = H * dpr;
        canvas.style.width = W + 'px';
        canvas.style.height = H + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        initParticles();
    }

    function initParticles() {
        var area = W * H;
        var count = Math.min(90 + Math.floor(area / 30000), 150);
        particles = [];
        for (var i = 0; i < count; i++) {
            particles.push({
                x: Math.random() * W,
                y: Math.random() * H,
                vx: (Math.random() - 0.5) * 0.35,
                vy: (Math.random() - 0.5) * 0.35,
                r: Math.random() * 1.8 + 0.7,
                c: COLORS[Math.floor(Math.random() * COLORS.length)],
                baseAlpha: Math.random() * 0.5 + 0.25,
                tw: Math.random() * 0.02 + 0.005,
                ph: Math.random() * Math.PI * 2
            });
        }
    }

    var t = 0;
    function draw() {
        t += 0.02;
        ctx.clearRect(0, 0, W, H);

        for (var i = 0; i < particles.length; i++) {
            var p = particles[i];
            p.x += p.vx;
            p.y += p.vy;

            if (mouse.active) {
                var mx = p.x - mouse.x;
                var my = p.y - mouse.y;
                var md2 = mx * mx + my * my;
                if (md2 < 160 * 160 && md2 > 1) {
                    var md = Math.sqrt(md2);
                    var f = (160 - md) / 160 * 0.8;
                    p.x += (mx / md) * f;
                    p.y += (my / md) * f;
                }
            }

            if (p.x < -20) p.x = W + 20; else if (p.x > W + 20) p.x = -20;
            if (p.y < -20) p.y = H + 20; else if (p.y > H + 20) p.y = -20;
        }

        var LINK = 120;
        for (var a = 0; a < particles.length; a++) {
            var pa = particles[a];
            for (var b = a + 1; b < particles.length; b++) {
                var pb = particles[b];
                var dx = pa.x - pb.x, dy = pa.y - pb.y;
                var d2 = dx * dx + dy * dy;
                if (d2 < LINK * LINK) {
                    var d = Math.sqrt(d2);
                    var alpha = (1 - d / LINK) * 0.35;
                    ctx.strokeStyle = 'rgba(169, 227, 75,' + alpha.toFixed(3) + ')';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(pa.x, pa.y);
                    ctx.lineTo(pb.x, pb.y);
                    ctx.stroke();
                }
            }
        }

        if (mouse.active) {
            for (var m = 0; m < particles.length; m++) {
                var pm = particles[m];
                var mdx = pm.x - mouse.x, mdy = pm.y - mouse.y;
                var md2b = mdx * mdx + mdy * mdy;
                if (md2b < 180 * 180) {
                    var md2c = Math.sqrt(md2b);
                    var malpha = (1 - md2c / 180) * 0.5;
                    ctx.strokeStyle = 'rgba(169, 227, 75,' + malpha.toFixed(3) + ')';
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(mouse.x, mouse.y);
                    ctx.lineTo(pm.x, pm.y);
                    ctx.stroke();
                }
            }
        }

        for (var k = 0; k < particles.length; k++) {
            var pk = particles[k];
            var twinkle = 0.6 + 0.4 * Math.sin(t * pk.tw * 100 + pk.ph);
            var alpha2 = pk.baseAlpha * twinkle;
            ctx.beginPath();
            ctx.arc(pk.x, pk.y, pk.r, 0, Math.PI * 2);
            ctx.fillStyle = pk.c;
            ctx.globalAlpha = alpha2;
            ctx.fill();
            ctx.globalAlpha = 1;
        }

        requestAnimationFrame(draw);
    }

    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', function (e) {
        mouse.x = e.clientX; mouse.y = e.clientY; mouse.active = true;
    });
    window.addEventListener('mouseleave', function () {
        mouse.active = false; mouse.x = -9999; mouse.y = -9999;
    });
    window.addEventListener('touchmove', function (e) {
        if (e.touches.length) {
            mouse.x = e.touches[0].clientX; mouse.y = e.touches[0].clientY; mouse.active = true;
        }
    }, { passive: true });
    window.addEventListener('touchend', function () { mouse.active = false; });

    resize();
    requestAnimationFrame(draw);
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
    '新增': 'chg-new',
    '优化': 'chg-opt',
    '修复': 'chg-fix',
    '调整': 'chg-adj'
};

function changeBadge(type) {
    var cls = TYPE_CLASS[type] || 'chg-adj';
    return '<span class="chg-type ' + cls + '">' + type + '</span>';
}

function channelClass(channel) {
    return channel === '内测版' ? ' beta' : '';
}

// ==================== 数据加载与渲染 ====================
async function loadVersions() {
    try {
        var res = await fetch('/api/versions');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        var data = await res.json();
        if (!data.success || !data.versions) throw new Error('bad data');
        var versions = data.versions;
        renderHeroStats(versions);
        renderCurrent(versions[0]);
        renderTimeline(versions);
    } catch (err) {
        console.error('加载版本历史失败:', err);
        showError();
    }
}

function renderHeroStats(versions) {
    var count = versions.length;
    var latest = versions[0] ? versions[0].version : '—';
    var first = versions[versions.length - 1] ? versions[versions.length - 1].date : '—';

    document.getElementById('latestVersion').textContent = latest;

    var firstDateEl = document.getElementById('firstDate');
    if (first !== '—') {
        var d = new Date(first + 'T00:00:00');
        firstDateEl.textContent = d.getFullYear() + '.' + (d.getMonth() + 1) + '.' + d.getDate();
    }

    animateNumber(document.getElementById('versionCount'), count, 1400);
}

function renderCurrent(v) {
    var card = document.getElementById('currentCard');
    if (!v) {
        card.innerHTML = '<div class="current-loading"><p>暂无版本记录</p></div>';
        return;
    }

    var sizeText = formatSize(v.size);
    var changes = (v.changes || []).map(function (c) {
        return '<li>' + changeBadge(c.type) + '<span>' + c.text + '</span></li>';
    }).join('');

    var downloadHtml = v.download_url
        ? '<a class="btn-download" href="' + v.download_url + '"><i class="fas fa-download"></i> 下载 ' + v.version + '</a>'
        : '<span class="tl-archived">该版本已归档</span>';

    card.innerHTML =
        '<div class="current-head">' +
            '<span class="current-version">' + v.version + '</span>' +
            '<span class="latest-badge"><i class="fas fa-star"></i> 最新版本</span>' +
            '<span class="current-date"><i class="far fa-calendar-alt"></i> ' + v.date + '</span>' +
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
        var changes = (v.changes || []).map(function (c) {
            return '<li>' + changeBadge(c.type) + '<span>' + c.text + '</span></li>';
        }).join('');

        var foot = v.download_url
            ? '<a class="tl-download" href="' + v.download_url + '"><i class="fas fa-download"></i> 下载安装包</a>' + (sizeText ? '<span class="tl-size">' + sizeText + '</span>' : '')
            : '<span class="tl-archived"><i class="fas fa-box-archive"></i> 历史版本已归档</span>';

        item.innerHTML =
            '<div class="tl-node"><span class="tl-dot"></span></div>' +
            '<div class="tl-card' + (v.is_current ? ' is-current' : '') + '">' +
                '<div class="tl-meta">' +
                    '<span class="tl-version">' + v.version + '</span>' +
                    '<span class="tl-channel' + channelClass(v.channel) + '">' + v.channel + '</span>' +
                    '<span class="tl-date">' + v.date + '</span>' +
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

function showError() {
    var card = document.getElementById('currentCard');
    card.innerHTML = '<div class="current-loading"><p><i class="fas fa-exclamation-triangle"></i> 加载失败，请刷新页面重试</p></div>';
    var items = document.getElementById('timelineItems');
    if (items) items.innerHTML = '';
}

// ==================== 数字滚动动画 ====================
function animateNumber(el, target, duration) {
    var start = performance.now();
    function tick(now) {
        var p = Math.min((now - start) / duration, 1);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased);
        if (p < 1) requestAnimationFrame(tick);
        else el.textContent = target;
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

    if (backTop) {
        backTop.addEventListener('click', function () {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function () {
    initScroll();
    initReveal();
    loadVersions();
});
