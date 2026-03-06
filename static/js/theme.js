// Data Studio Neo-Brutalist Interaction Engine
document.addEventListener('DOMContentLoaded', () => {
  // 1. Tooltip Implementation
  const tooltip = document.createElement('div');
  tooltip.className = 'custom-tooltip';
  document.body.appendChild(tooltip);

  const showTooltip = (content, x, y) => {
    tooltip.innerHTML = content;
    tooltip.style.display = 'block';

    const width = tooltip.offsetWidth;
    const height = tooltip.offsetHeight;
    const windowWidth = window.innerWidth;
    const windowHeight = window.innerHeight;

    let finalX = x + 15;
    let finalY = y + 15;

    if (finalX + width > windowWidth) finalX = x - width - 15;
    if (finalY + height > windowHeight) finalY = y - height - 15;

    tooltip.style.left = finalX + 'px';
    tooltip.style.top = finalY + 'px';
  };

  const hideTooltip = () => {
    tooltip.style.display = 'none';
  };

  // Expose to window for external chart libraries (like Plotly)
  window.DataStudio = {
    showTooltip,
    hideTooltip
  };

  // Global click to hide any stuck tooltips
  window.addEventListener('mousedown', (e) => {
    if (tooltip.style.display === 'block') {
      hideTooltip();
    }
  });

  // Attach to all statistical markers in DOM
  const attachListeners = () => {
    const statElements = document.querySelectorAll('.stat-card, .chart-box, [data-tooltip], [data-value], [data-insight]');
    statElements.forEach(el => {
      el.addEventListener('mouseenter', (e) => {
        const title = el.getAttribute('data-tooltip');
        const value = el.getAttribute('data-value');
        const insight = el.getAttribute('data-insight');

        if (!title && !value && !insight) return;

        const content = `
          ${title ? `<div class="tooltip-title">${title}</div>` : ''}
          ${value ? `<div class="tooltip-value">${value}</div>` : ''}
          ${insight ? `<div class="mt-2 small fw-bold text-uppercase">${insight}</div>` : ''}
        `;
        showTooltip(content, e.clientX, e.clientY);
      });
      el.addEventListener('mousemove', (e) => {
        if (tooltip.style.display === 'block') {
          showTooltip(tooltip.innerHTML, e.clientX, e.clientY);
        }
      });
      el.addEventListener('mouseleave', hideTooltip);
    });
  };


  attachListeners();

  // 2. Brutalist Snap Interactions
  document.querySelectorAll('.btn-neo, .btn-neo-outline').forEach(btn => {
    btn.addEventListener('mousedown', () => {
      btn.style.transform = 'translate(2px, 2px)';
      btn.style.boxShadow = '0px 0px 0px var(--shadow-color)';
    });
    btn.addEventListener('mouseup', () => {
      btn.style.transform = '';
      btn.style.boxShadow = '';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.transform = '';
      btn.style.boxShadow = '';
    });
  });

  // 3. Dark Mode Toggle
  const toggleBtn = document.getElementById('theme-toggle');

  const updateToggleBtnUI = (isDark) => {
    if (!toggleBtn) return;

    // Check if the button has a span (like in settings.html) or is just an icon
    const spanElement = toggleBtn.querySelector('span');
    if (spanElement || toggleBtn.innerText.includes('Toggle')) {
      toggleBtn.innerHTML = `<span>Toggle ${isDark ? 'Light' : 'Dark'} Mode</span> ${isDark ? '☀️' : '🌙'}`;
    } else {
      toggleBtn.innerHTML = isDark ? '☀️' : '🌙';
    }
  };

  // Check for saved theme preference
  const currentTheme = localStorage.getItem("theme");
  if (currentTheme === "dark") {
    document.documentElement.setAttribute("data-theme", "dark");
    updateToggleBtnUI(true);
  } else {
    updateToggleBtnUI(false);
  }

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      let theme = "light";
      if (document.documentElement.getAttribute("data-theme") === "dark") {
        document.documentElement.removeAttribute("data-theme");
        updateToggleBtnUI(false);
      } else {
        document.documentElement.setAttribute("data-theme", "dark");
        updateToggleBtnUI(true);
        theme = "dark";
      }
      localStorage.setItem("theme", theme);
    });
  }
});


