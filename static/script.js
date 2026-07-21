// 导航栏交互
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    const navLinks = document.querySelectorAll('.nav-link');

    // 加载配置信息
    loadConfig();

    // 移动端导航菜单切换
    navToggle.addEventListener('click', function() {
        navMenu.classList.toggle('active');
        navToggle.querySelector('i').classList.toggle('fa-bars');
        navToggle.querySelector('i').classList.toggle('fa-times');
    });

    // 点击导航链接关闭菜单
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            navMenu.classList.remove('active');
            navToggle.querySelector('i').classList.remove('fa-times');
            navToggle.querySelector('i').classList.add('fa-bars');
        });
    });

    // 导航栏滚动效果
    window.addEventListener('scroll', function() {
        const navbar = document.querySelector('.navbar');
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(255, 255, 255, 0.98)';
            navbar.style.boxShadow = '0 2px 20px rgba(46, 125, 50, 0.15)';
        } else {
            navbar.style.background = 'rgba(255, 255, 255, 0.95)';
            navbar.style.boxShadow = '0 2px 10px rgba(46, 125, 50, 0.1)';
        }
    });

    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const offsetTop = target.offsetTop - 70;
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });

    // 滚动动画
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // 观察需要动画的元素
    document.querySelectorAll('.feature-card, .screenshot-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });

    // 下载按钮点击效果
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            
            try {
                // 检查是否有可用版本
                const response = await fetch('/api/latest');
                if (response.ok) {
                    const data = await response.json();
                    // 直接下载文件
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

// 加载配置信息
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (response.ok) {
            const config = await response.json();
            
            // 更新下载按钮文本
            const downloadButtonText = document.getElementById('downloadButtonText');
            const downloadButtonSubtext = document.getElementById('downloadButtonSubtext');
            const downloadNote = document.getElementById('downloadNote');
            
            if (downloadButtonText && config.download) {
                downloadButtonText.textContent = config.download.button_text;
            }
            if (downloadButtonSubtext && config.download) {
                downloadButtonSubtext.textContent = config.download.button_subtext;
            }
            if (downloadNote && config.download) {
                downloadNote.textContent = config.download.note;
            }
            
            // 更新页面标题
            if (config.site) {
                document.title = config.site.name + ' - ' + config.site.description;
            }
        }
    } catch (error) {
        console.log('加载配置失败:', error);
    }
}

// 显示下载模态框
function showDownloadModal(message = '绿豆蛙日报助手即将开始下载') {
    // 创建模态框
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 2000;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;

    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: white;
        padding: 40px;
        border-radius: 12px;
        text-align: center;
        max-width: 400px;
        width: 90%;
        transform: scale(0.9);
        transition: transform 0.3s ease;
    `;

    modalContent.innerHTML = `
        <i class="fas fa-download" style="font-size: 3rem; color: #4caf50; margin-bottom: 20px;"></i>
        <h3 style="margin-bottom: 15px; color: #333;">准备下载</h3>
        <p style="color: #666; margin-bottom: 25px;">${message}</p>
        <button onclick="this.closest('div').parentElement.remove()" style="
            background: #4caf50;
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 6px;
            font-size: 1rem;
            cursor: pointer;
            transition: background 0.3s ease;
        ">确定</button>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // 动画显示
    setTimeout(() => {
        modal.style.opacity = '1';
        modalContent.style.transform = 'scale(1)';
    }, 10);

    // 点击背景关闭
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// 导航栏高亮当前部分
window.addEventListener('scroll', function() {
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');
    
    let current = '';
    sections.forEach(section => {
        const sectionTop = section.offsetTop - 100;
        const sectionHeight = section.clientHeight;
        if (window.scrollY >= sectionTop && window.scrollY < sectionTop + sectionHeight) {
            current = section.getAttribute('id');
        }
    });

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${current}`) {
            link.classList.add('active');
        }
    });
});