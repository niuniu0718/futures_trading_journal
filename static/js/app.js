// 前端交互逻辑

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    initTooltips();

    // 初始化表单验证
    initFormValidation();

    // 自动保存草稿（交易表单）
    if (document.getElementById('tradeForm')) {
        initAutoSave();
    }
});

// 工具提示初始化
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseenter', function(e) {
            const tooltipText = this.getAttribute('data-tooltip');
            const tooltipEl = document.createElement('div');
            tooltipEl.className = 'absolute bg-gray-900 text-white text-xs rounded px-2 py-1 -mt-8 ml-2 whitespace-nowrap z-50';
            tooltipEl.textContent = tooltipText;
            tooltipEl.id = 'tooltip-' + Math.random().toString(36).substr(2, 9);
            this.style.position = 'relative';
            this.appendChild(tooltipEl);
        });

        tooltip.addEventListener('mouseleave', function() {
            const tooltipEl = this.querySelector('[id^="tooltip-"]');
            if (tooltipEl) {
                tooltipEl.remove();
            }
        });
    });
}

// 表单验证
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            const requiredFields = form.querySelectorAll('[required]');

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('border-red-500');
                    showFieldError(field, '此字段为必填项');
                } else {
                    field.classList.remove('border-red-500');
                    hideFieldError(field);
                }
            });

            if (!isValid) {
                e.preventDefault();
            }
        });
    });
}

// 显示字段错误
function showFieldError(field, message) {
    let errorEl = field.parentElement.querySelector('.field-error');
    if (!errorEl) {
        errorEl = document.createElement('p');
        errorEl.className = 'field-error text-red-500 text-xs mt-1';
        field.parentElement.appendChild(errorEl);
    }
    errorEl.textContent = message;
}

// 隐藏字段错误
function hideFieldError(field) {
    const errorEl = field.parentElement.querySelector('.field-error');
    if (errorEl) {
        errorEl.remove();
    }
}

// 自动保存草稿
function initAutoSave() {
    const form = document.getElementById('tradeForm');
    const formId = form.id || 'trade-form';
    const storageKey = 'draft-' + formId;

    // 加载草稿
    const draft = localStorage.getItem(storageKey);
    if (draft) {
        const data = JSON.parse(draft);
        Object.keys(data).forEach(key => {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) {
                field.value = data[key];
            }
        });
    }

    // 自动保存
    let saveTimeout;
    form.addEventListener('input', function() {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            const formData = new FormData(form);
            const data = {};
            formData.forEach((value, key) => {
                data[key] = value;
            });
            localStorage.setItem(storageKey, JSON.stringify(data));
        }, 1000);
    });

    // 提交后清除草稿
    form.addEventListener('submit', function() {
        localStorage.removeItem(storageKey);
    });
}

// 确认对话框
function confirmAction(message) {
    return window.confirm(message);
}

// 显示通知
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-6 py-4 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500' :
        type === 'error' ? 'bg-red-500' :
        type === 'warning' ? 'bg-yellow-500' :
        'bg-blue-500'
    } text-white`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 格式化货币
function formatCurrency(value) {
    return new Intl.NumberFormat('zh-CN', {
        style: 'currency',
        currency: 'CNY'
    }).format(value);
}

// 格式化百分比
function formatPercentage(value) {
    return value.toFixed(2) + '%';
}

// 复制到剪贴板
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('已复制到剪贴板', 'success');
    }).catch(() => {
        showNotification('复制失败', 'error');
    });
}

// 导出功能
function exportData(format) {
    window.location.href = `/export/${format}`;
}

// 筛选功能
function applyFilters(filters) {
    const url = new URL(window.location);
    Object.keys(filters).forEach(key => {
        if (filters[key]) {
            url.searchParams.set(key, filters[key]);
        } else {
            url.searchParams.delete(key);
        }
    });
    window.location = url.toString();
}

// 排序功能
function sortTable(column) {
    const currentOrder = new URL(window.location).searchParams.get('order') || 'DESC';
    const newOrder = currentOrder === 'ASC' ? 'DESC' : 'ASC';
    const url = new URL(window.location);
    url.searchParams.set('order_by', column);
    url.searchParams.set('order', newOrder);
    window.location = url.toString();
}
