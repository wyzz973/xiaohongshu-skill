// xsec_token 拦截器 — 注入到小红书首页，捕获 homefeed API 中的笔记 ID 和 token
// 用法: playwright-cli -s=xhs eval "$(cat scripts/intercept_homefeed.js)"

window.__xhs_notes = [];
window.__xhs_interceptor_ready = false;

const origFetch = window.fetch;
window.fetch = async (...args) => {
    const resp = await origFetch(...args);
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
    
    if (url.includes('/api/sns/web/v1/homefeed')) {
        try {
            const clone = resp.clone();
            const data = await clone.json();
            if (data.data && data.data.items) {
                data.data.items.forEach(item => {
                    if (item.id && item.xsec_token) {
                        // 去重
                        if (!window.__xhs_notes.find(n => n.id === item.id)) {
                            window.__xhs_notes.push({
                                id: item.id,
                                token: item.xsec_token,
                                title: item.note_card?.display_title || '',
                                author: item.note_card?.user?.nickname || '',
                                likes: item.note_card?.interact_info?.liked_count || '0',
                                type: item.note_card?.type || 'normal',
                                timestamp: Date.now()
                            });
                        }
                    }
                });
            }
        } catch(e) {
            console.error('[xhs-interceptor] Parse error:', e.message);
        }
    }
    return resp;
};

window.__xhs_interceptor_ready = true;
'interceptor installed, notes count: ' + window.__xhs_notes.length;
