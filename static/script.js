// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    const navLinks = document.querySelectorAll('.nav-link');

    loadConfig();
    initActivityFeed();
    initReveal();
    initCounters();
    initBentoGlow();

    // 移动端导航菜单切换
    navToggle.addEventListener('click', function() {
        navMenu.classList.toggle('active');
        navToggle.querySelector('i').classList.toggle('fa-bars');
        navToggle.querySelector('i').classList.toggle('fa-times');
    });

    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            navMenu.classList.remove('active');
            navToggle.querySelector('i').classList.remove('fa-times');
            navToggle.querySelector('i').classList.add('fa-bars');
        });
    });

    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                window.scrollTo({ top: target.offsetTop - 72, behavior: 'smooth' });
            }
        });
    });

    // 下载按钮（保留原有逻辑）
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            try {
                const response = await fetch('/api/latest');
                if (response.ok) {
                    const data = await response.json();
                    window.location.href = `/download/${data.filename}`;
                } else {
                    showDownloadModal('暂无可用版本，请稍后再试');
                }
            } catch (error) {
                showDownloadModal('下载失败，请稍后再试');
            }
        });
    }
});

// ==================== 导航栏滚动效果 ====================
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 40);

    // 高亮当前分区
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');
    let current = '';
    sections.forEach(section => {
        const top = section.offsetTop - 120;
        if (window.scrollY >= top && window.scrollY < top + section.clientHeight) {
            current = section.getAttribute('id');
        }
    });
    navLinks.forEach(link => {
        link.classList.toggle('active', link.getAttribute('href') === `#${current}`);
    });
});

// ==================== 产品实况模拟 ====================
const ACTIVITIES = [
    { icon: 'fa-code',        color: '#2f9e44', title: '开发',   desc: '正在编辑项目核心模块，调试接口逻辑' },
    { icon: 'fa-comments',    color: '#1c7ed6', title: '沟通',   desc: '参与团队群聊，同步项目进度' },
    { icon: 'fa-file-alt',    color: '#f08c00', title: '文档',   desc: '撰写产品需求文档，整理功能要点' },
    { icon: 'fa-chart-line',  color: '#e64980', title: '数据分析', desc: '查看运营数据看板，分析转化趋势' },
    { icon: 'fa-pen-ruler',   color: '#9c36b5', title: '设计',   desc: '调整界面原型，优化交互细节' },
    { icon: 'fa-users',       color: '#0ca678', title: '会议',   desc: '参加产品评审会议，记录待办事项' },
    { icon: 'fa-graduation-cap', color: '#5c940d', title: '学习', desc: '阅读技术文章，学习新方法' },
    { icon: 'fa-tasks',       color: '#364fc7', title: '管理',   desc: '规划迭代任务，分配工作重点' }
];

let liveCount = 0;

function initActivityFeed() {
    const feed = document.getElementById('activityFeed');
    if (!feed) return;

    // 预填 3 条
    for (let i = 0; i < 3; i++) pushActivity(feed, false);

    // 持续推送
    setInterval(() => pushActivity(feed, true), 2600);
}

function pushActivity(feed, animate) {
    const a = ACTIVITIES[Math.floor(Math.random() * ACTIVITIES.length)];
    const mins = (Math.random() * 40 + 5).toFixed(0);
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;

    const card = document.createElement('div');
    card.className = 'activity-card';
    card.style.setProperty('--ac', a.color);
    if (!animate) card.style.animation = 'none';
    card.innerHTML = `
        <div class="ac-icon" style="background:${a.color}"><i class="fas ${a.icon}"></i></div>
        <div class="ac-body">
            <div class="ac-title">${a.title}</div>
            <div class="ac-desc">${a.desc}</div>
        </div>
        <div class="ac-time">${time} · ${mins}min</div>
    `;

    feed.insertBefore(card, feed.firstChild);
    while (feed.children.length > 3) feed.removeChild(feed.lastChild);

    liveCount++;
    const counter = document.getElementById('liveCount');
    if (counter) counter.textContent = liveCount;
}

// ==================== 滚动显现 ====================
function initReveal() {
    const observer = new IntersectionObserver(entries => {
        entries.forEach((entry, i) => {
            if (entry.isIntersecting) {
                setTimeout(() => entry.target.classList.add('visible'), (i % 4) * 90);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
}

// ==================== 数字滚动 ====================
function initCounters() {
    const counters = document.querySelectorAll('[data-count]');
    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCount(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });
    counters.forEach(el => observer.observe(el));
}

function animateCount(el) {
    const target = parseInt(el.dataset.count, 10);
    const duration = 1400;
    const start = performance.now();
    function tick(now) {
        const p = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased);
        if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ==================== Bento 卡片光斑 ====================
function initBentoGlow() {
    document.querySelectorAll('.bento-card').forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            card.style.setProperty('--mx', `${e.clientX - rect.left}px`);
            card.style.setProperty('--my', `${e.clientY - rect.top}px`);
        });
    });
}

// ==================== 加载配置（保留原有逻辑）====================
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (response.ok) {
            const config = await response.json();
            const downloadButtonText = document.getElementById('downloadButtonText');
            const downloadButtonSubtext = document.getElementById('downloadButtonSubtext');
            const downloadNote = document.getElementById('downloadNote');
            if (downloadButtonText && config.download) downloadButtonText.textContent = config.download.button_text;
            if (downloadButtonSubtext && config.download) downloadButtonSubtext.textContent = config.download.button_subtext;
            if (downloadNote && config.download) downloadNote.textContent = config.download.note;
            if (config.site) document.title = config.site.name + ' - ' + config.site.description;
        }
    } catch (error) {
        console.log('加载配置失败:', error);
    }
}

// ==================== 下载提示模态框 ====================
function showDownloadModal(message = '绿豆蛙日报助手即将开始下载') {
    const modal = document.createElement('div');
    modal.style.cssText = `position:fixed;inset:0;background:rgba(18,43,28,0.55);display:flex;justify-content:center;align-items:center;z-index:2000;opacity:0;transition:opacity .3s ease;backdrop-filter:blur(4px);`;
    const content = document.createElement('div');
    content.style.cssText = `background:#fff;padding:44px 40px;border-radius:18px;text-align:center;max-width:400px;width:90%;transform:scale(.92);transition:transform .3s ease;box-shadow:0 24px 60px rgba(18,43,28,.3);`;
    content.innerHTML = `
        <i class="fas fa-download" style="font-size:2.8rem;color:#2f9e44;margin-bottom:20px;"></i>
        <h3 style="margin-bottom:12px;color:#16301f;font-family:'Noto Serif SC',serif;">准备下载</h3>
        <p style="color:#4a6253;margin-bottom:26px;font-size:.95rem;">${message}</p>
        <button style="background:#2f9e44;color:#fff;border:none;padding:12px 34px;border-radius:10px;font-size:1rem;font-weight:600;cursor:pointer;">确定</button>
    `;
    content.querySelector('button').addEventListener('click', () => modal.remove());
    modal.appendChild(content);
    document.body.appendChild(modal);
    requestAnimationFrame(() => { modal.style.opacity = '1'; content.style.transform = 'scale(1)'; });
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}
