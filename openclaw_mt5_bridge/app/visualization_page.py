"""Market visualization page - minimal robust version."""

PAGE_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>市场行情看板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 20px; }
        .header { text-align: center; margin-bottom: 20px; }
        .header h1 { font-size: 1.8em; color: #fff; }
        .time { color: #888; font-size: 14px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
        .card { background: #1a1a2e; border-radius: 8px; padding: 14px; border: 1px solid #2a2a4a; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .symbol { font-size: 1.1em; font-weight: bold; color: #e94560; }
        .state-badge { padding: 3px 8px; border-radius: 12px; font-size: 10px; background: #333; }
        .state-TREND_UP { background: #00c853; color: #000; }
        .state-TREND_DOWN { background: #ff1744; color: #fff; }
        .state-RANGE { background: #ff9800; color: #000; }
        .state-V_SHAPE { background: #2196f3; color: #fff; }
        .state-INVERSE_V { background: #9c27b0; color: #fff; }
        .state-UNKNOWN { background: #444; color: #fff; }
        .price { font-size: 1.4em; font-weight: bold; color: #fff; margin-bottom: 4px; }
        .sub-price { font-size: 0.85em; color: #888; }
        .metrics { display: flex; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid #2a2a4a; }
        .metric { flex: 1; text-align: center; padding: 6px; background: rgba(255,255,255,0.03); border-radius: 4px; }
        .metric-label { font-size: 9px; color: #666; text-transform: uppercase; }
        .metric-value { font-size: 13px; font-weight: bold; margin-top: 2px; }
        .section { margin-bottom: 20px; }
        .section-title { font-size: 12px; color: #888; margin-bottom: 8px; padding-left: 6px; border-left: 2px solid #e94560; }
        .loading { text-align: center; padding: 30px; color: #888; }
        .error { text-align: center; padding: 15px; color: #ff5252; background: rgba(255,82,82,0.1); border-radius: 6px; margin: 10px 0; }
        .btn { background: #e94560; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; margin-top: 10px; }
        .btn:hover { background: #d63850; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 市场行情看板</h1>
        <div class="time" id="currentTime">--</div>
        <button class="btn" onclick="loadData()">🔄 刷新</button>
    </div>

    <div id="errorMsg" class="error" style="display:none"></div>

    <div class="section">
        <div class="section-title">🪙 贵金属 & 能源</div>
        <div class="grid" id="metalsGrid"><div class="loading">加载中...</div></div>
    </div>

    <div class="section">
        <div class="section-title">💱 外汇</div>
        <div class="grid" id="forexGrid"><div class="loading">加载中...</div></div>
    </div>

    <div class="section">
        <div class="section-title">📈 指数 & ₿ 加密</div>
        <div class="grid" id="otherGrid"><div class="loading">加载中...</div></div>
    </div>

    <script>
        const METALS = ['XAUUSD', 'XAGUSD', 'XBRUSD', 'XTIUSD'];
        const FOREX = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURJPY'];
        const OTHER = ['JP225', 'US500', 'BTCUSD', 'ETHUSD'];

        // Global data storage
        let priceData = {};
        let structData = {};

        async function loadData() {
            const errorEl = document.getElementById('errorMsg');
            errorEl.style.display = 'none';
            
            try {
                // Fetch prices
                const pricesRes = await fetch('/csv/prices');
                if (!pricesRes.ok) throw new Error('/csv/prices 返回 ' + pricesRes.status);
                
                const pricesJson = await pricesRes.json();
                console.log('prices 原始响应:', JSON.stringify(pricesJson).substring(0, 300));
                
                // Handle object format: {prices: {SYMBOL: {...}}}
                const pricesObj = pricesJson.prices || pricesJson.data || {};
                priceData = typeof pricesObj === 'object' ? pricesObj : {};
                console.log('priceData keys:', Object.keys(priceData).slice(0, 5));
                
                // Fetch structures (optional)
                try {
                    const structRes = await fetch('/csv/structure/all');
                    if (structRes.ok) {
                        const structJson = await structRes.json();
                        console.log('structure 原始响应:', JSON.stringify(structJson).substring(0, 300));
                        const structObj = structJson.structures || structJson.data || {};
                        structData = typeof structObj === 'object' ? structObj : {};
                    }
                } catch (e) {
                    console.log('structure 接口失败（不影响）:', e.message);
                    structData = {};
                }
                
                // Render all grids
                renderGrid('metalsGrid', METALS);
                renderGrid('forexGrid', FOREX);
                renderGrid('otherGrid', OTHER);
                
            } catch (err) {
                console.error('loadData error:', err);
                errorEl.style.display = 'block';
                errorEl.textContent = '加载失败: ' + err.message;
            }
            
            document.getElementById('currentTime').textContent = new Date().toLocaleString('zh-CN');
        }

        function renderGrid(gridId, symbols) {
            const grid = document.getElementById(gridId);
            const cards = [];
            
            for (const sym of symbols) {
                const card = renderCard(sym);
                if (card) cards.push(card);
            }
            
            grid.innerHTML = cards.length > 0 
                ? cards.join('') 
                : '<div class="loading">暂无数据</div>';
        }

        function renderCard(symbol) {
            // Get price - handle both object and legacy field names
            const p = priceData[symbol];
            if (!p) return '';
            
            // Flexible field extraction
            const bid = p.bid ?? p.price ?? p.last ?? p.last_price ?? null;
            const ask = p.ask ?? p.ask_price ?? bid;
            const spread = p.spread ?? p.spread_points ?? 0;
            const updateTime = p.last_update ?? p.timestamp ?? '';
            
            // Get structure
            const s = structData[symbol] || {};
            const state = s.state ?? s.pattern ?? 'UNKNOWN';
            const conf = s.confidence ?? s.score ?? 0;
            const metrics = s.metrics || {};
            const slope = metrics.slope ?? s.slope ?? 0;
            const consist = metrics.consistency ?? s.consistency ?? 0;
            
            const confColor = conf > 0.7 ? '#00c853' : conf > 0.4 ? '#ff9800' : '#888';
            const digits = symbol.includes('JPY') ? 3 : symbol.includes('BTC') ? 2 : 5;
            
            return '<div class="card">' +
                '<div class="card-header">' +
                    '<span class="symbol">' + symbol + '</span>' +
                    '<span class="state-badge state-' + state + '">' + stateName(state) + '</span>' +
                '</div>' +
                '<div class="price">' + (bid ? bid.toFixed(digits) : 'N/A') + '</div>' +
                '<div class="sub-price">Ask: ' + (ask ? ask.toFixed(digits) : 'N/A') + ' | 点差: ' + spread.toFixed(1) + '</div>' +
                '<div class="metrics">' +
                    '<div class="metric"><div class="metric-label">置信度</div><div class="metric-value" style="color:' + confColor + '">' + (conf * 100).toFixed(0) + '%</div></div>' +
                    '<div class="metric"><div class="metric-label">斜率</div><div class="metric-value">' + (slope > 0 ? '+' : '') + slope.toFixed(4) + '</div></div>' +
                    '<div class="metric"><div class="metric-label">一致性</div><div class="metric-value">' + (consist * 100).toFixed(0) + '%</div></div>' +
                '</div>' +
            '</div>';
        }

        function stateName(s) {
            return {
                'TREND_UP': '单边涨', 'TREND_DOWN': '单边跌',
                'RANGE': '震荡', 'V_SHAPE': 'V型', 'INVERSE_V': '倒V', 'UNKNOWN': '未知'
            }[s] || s;
        }

        // Start
        loadData();
        setInterval(loadData, 5000);
        setInterval(() => {
            document.getElementById('currentTime').textContent = new Date().toLocaleString('zh-CN');
        }, 1000);
    </script>
</body>
</html>
"""

def get_visualization_page_html() -> str:
    return PAGE_HTML
