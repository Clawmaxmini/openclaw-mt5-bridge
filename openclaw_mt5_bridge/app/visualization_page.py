"""Market visualization page - fixed data handling."""

PAGE_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>市场行情看板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0f;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2em; color: #fff; margin-bottom: 10px; }
        .header .time { color: #888; font-size: 14px; }
        .tabs {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 24px;
            background: #1a1a2e;
            border: 1px solid #2a2a4a;
            border-radius: 8px;
            cursor: pointer;
            color: #888;
            transition: all 0.2s;
        }
        .tab.active { background: #e94560; color: #fff; border-color: #e94560; }
        .tab:hover { border-color: #e94560; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 16px;
        }
        .card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid #2a2a4a;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .symbol {
            font-size: 1.3em;
            font-weight: bold;
            color: #e94560;
            cursor: pointer;
        }
        .symbol:hover { text-decoration: underline; }
        .state-badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: bold;
        }
        .state-TREND_UP { background: #00c853; color: #000; }
        .state-TREND_DOWN { background: #ff1744; color: #fff; }
        .state-RANGE { background: #ff9800; color: #000; }
        .state-V_SHAPE { background: #2196f3; color: #fff; }
        .state-INVERSE_V { background: #9c27b0; color: #fff; }
        .state-UNKNOWN { background: #666; color: #fff; }
        .price-row {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 8px;
        }
        .bid { font-size: 1.6em; font-weight: bold; color: #fff; }
        .ask { font-size: 1em; color: #888; margin-left: 8px; }
        .spread { font-size: 12px; color: #666; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #2a2a4a;
        }
        .metric { text-align: center; padding: 8px; background: rgba(255,255,255,0.03); border-radius: 8px; }
        .metric-label { font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 4px; }
        .metric-value { font-size: 14px; font-weight: bold; }
        .confidence-bar { height: 4px; background: #333; border-radius: 2px; margin-top: 8px; overflow: hidden; }
        .confidence-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
        .section-title {
            font-size: 14px;
            color: #888;
            margin: 24px 0 12px;
            padding-left: 8px;
            border-left: 3px solid #e94560;
        }
        .loading { text-align: center; padding: 40px; color: #888; }
        .error {
            text-align: center;
            padding: 20px;
            color: #ff5252;
            background: rgba(255,82,82,0.1);
            border-radius: 8px;
            margin: 20px 0;
        }
        .refresh-btn {
            background: #e94560;
            color: #fff;
            border: none;
            padding: 10px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }
        .refresh-btn:hover { background: #d63850; }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            overflow: auto;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: #1a1a2e;
            margin: auto;
            padding: 20px;
            border-radius: 12px;
            width: 90%;
            max-width: 900px;
            max-height: 90vh;
            overflow: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-header h2 { color: #e94560; }
        .modal-close { background: none; border: none; color: #888; font-size: 24px; cursor: pointer; }
        .modal-close:hover { color: #fff; }
        .chart-container { background: #0a0a0f; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .chart-canvas { width: 100%; height: 200px; }
        .history-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 16px; }
        .stat-box { background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; text-align: center; }
        .stat-label { font-size: 11px; color: #666; margin-bottom: 4px; }
        .stat-value { font-size: 18px; font-weight: bold; }
        .footer { text-align: center; margin-top: 30px; color: #555; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 市场行情看板</h1>
        <div class="time" id="currentTime">加载中...</div>
        <button class="refresh-btn" onclick="loadData()">🔄 刷新数据</button>
    </div>

    <div class="error" id="error" style="display:none"></div>

    <div class="section-title">🪙 贵金属 & 能源</div>
    <div class="grid" id="metalsGrid"><div class="loading">加载中...</div></div>

    <div class="section-title">💱 外汇</div>
    <div class="grid" id="forexGrid"><div class="loading">加载中...</div></div>

    <div class="section-title">📈 指数</div>
    <div class="grid" id="indicesGrid"><div class="loading">加载中...</div></div>

    <div class="section-title">₿ 加密货币</div>
    <div class="grid" id="cryptoGrid"><div class="loading">加载中...</div></div>

    <div class="footer">数据来源: MT5 Bridge | 每5秒自动刷新</div>

    <div class="modal" id="historyModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalSymbol">XAUUSD 历史</h2>
                <button class="modal-close" onclick="closeModal()">×</button>
            </div>
            <div class="chart-container">
                <canvas id="priceChart" class="chart-canvas"></canvas>
            </div>
            <div class="history-stats" id="historyStats"></div>
        </div>
    </div>

    <script>
        const API_BASE = '';
        const METALS = ['XAUUSD', 'XAGUSD', 'XBRUSD', 'XTIUSD'];
        const FOREX = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD'];
        const INDICES = ['JP225', 'US500'];
        const CRYPTO = ['BTCUSD', 'ETHUSD'];

        let allPrices = {};
        let allStructures = {};
        let historyData = [];

        async function loadData() {
            try {
                // Fetch both APIs
                const [pricesRes, structRes] = await Promise.all([
                    fetch(API_BASE + '/csv/prices').catch(e => null),
                    fetch(API_BASE + '/csv/structure/all').catch(e => null)
                ]);

                console.log('pricesRes status:', pricesRes?.status);
                console.log('structRes status:', structRes?.status);

                if (!pricesRes || !pricesRes.ok) {
                    throw new Error('无法连接价格接口');
                }

                const pricesData = await pricesRes.json();
                console.log('prices raw response:', JSON.stringify(pricesData).substring(0, 500));

                // Handle object format: {prices: {SYMBOL: {...}}}
                const pricesObj = pricesData.prices || pricesData.data || {};
                allPrices = typeof pricesObj === 'object' && !Array.isArray(pricesObj) ? pricesObj : {};
                
                console.log('converted priceList length:', Object.keys(allPrices).length);

                // Handle structure
                if (structRes && structRes.ok) {
                    const structData = await structRes.json();
                    console.log('structure raw response:', JSON.stringify(structData).substring(0, 500));
                    
                    const structObj = structData.structures || structData.data || {};
                    allStructures = typeof structObj === 'object' && !Array.isArray(structObj) ? structObj : {};
                    console.log('converted structureList length:', Object.keys(allStructures).length);
                }

                // Render all categories
                renderCategory('metalsGrid', METALS);
                renderCategory('forexGrid', FOREX);
                renderCategory('indicesGrid', INDICES);
                renderCategory('cryptoGrid', CRYPTO);

                document.getElementById('error').style.display = 'none';
            } catch (err) {
                console.error('Load error:', err);
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = '错误: ' + err.message;
            }
        }

        function renderCategory(gridId, symbols) {
            const grid = document.getElementById(gridId);
            const cards = [];
            
            for (const symbol of symbols) {
                const card = renderCard(symbol);
                if (card) cards.push(card);
            }
            
            if (cards.length === 0) {
                grid.innerHTML = '<div class="loading">暂无数据</div>';
            } else {
                grid.innerHTML = cards.join('');
            }
        }

        function renderCard(symbol) {
            // Get price data - handle object format
            const priceData = allPrices[symbol];
            if (!priceData) return '';

            // Handle multiple field names
            const price = priceData.price || priceData.last_price || priceData.bid || priceData.last || null;
            const bid = priceData.bid || price;
            const ask = priceData.ask || priceData.ask_price || price;
            const spread = priceData.spread || priceData.spread_points || 0;

            // Get structure data - handle object format
            const structData = allStructures[symbol] || {};
            const state = structData.state || structData.pattern || structData.structure || 'UNKNOWN';
            const confidence = structData.confidence || structData.score || 0;
            const metrics = structData.metrics || {};
            const slope = metrics.slope || structData.slope || 0;
            const consistency = metrics.consistency || structData.consistency || 0;

            const confidenceColor = confidence > 0.7 ? '#00c853' : confidence > 0.4 ? '#ff9800' : '#ff5252';

            return '<div class="card">' +
                '<div class="card-header">' +
                    '<span class="symbol" onclick="openHistory(\'' + symbol + '\')">' + symbol + '</span>' +
                    '<span class="state-badge state-' + state + '">' + stateName(state) + '</span>' +
                '</div>' +
                '<div class="price-row">' +
                    '<div><span class="bid">' + (bid ? bid.toFixed(priceDigits(symbol)) : 'N/A') + '</span>' +
                    '<span class="ask">' + (ask ? ask.toFixed(priceDigits(symbol)) : '') + '</span></div>' +
                '</div>' +
                '<div class="spread">点差: ' + spread.toFixed(1) + ' | ' + (priceData.last_update || priceData.timestamp || '') + '</div>' +
                '<div class="metrics">' +
                    '<div class="metric"><div class="metric-label">置信度</div><div class="metric-value" style="color:' + confidenceColor + '">' + (confidence * 100).toFixed(0) + '%</div><div class="confidence-bar"><div class="confidence-fill" style="width:' + (confidence * 100) + '%;background:' + confidenceColor + '"></div></div></div>' +
                    '<div class="metric"><div class="metric-label">斜率</div><div class="metric-value">' + (slope > 0 ? '+' : '') + slope.toFixed(4) + '</div></div>' +
                    '<div class="metric"><div class="metric-label">一致性</div><div class="metric-value">' + (consistency * 100).toFixed(0) + '%</div></div>' +
                '</div>' +
            '</div>';
        }

        async function openHistory(symbol) {
            document.getElementById('modalSymbol').textContent = symbol + ' 历史走势';
            document.getElementById('historyModal').classList.add('active');
            
            try {
                const res = await fetch(API_BASE + '/history/' + symbol + '?limit=100');
                const data = await res.json();
                historyData = data.history || [];
                console.log('history loaded:', historyData.length);
                drawChart(symbol);
                drawStats();
            } catch (err) {
                console.error('Failed to load history:', err);
            }
        }

        function closeModal() {
            document.getElementById('historyModal').classList.remove('active');
        }

        function drawChart(symbol) {
            const canvas = document.getElementById('priceChart');
            const ctx = canvas.getContext('2d');
            const w = canvas.width = canvas.offsetWidth * 2;
            const h = canvas.height = 400;
            ctx.clearRect(0, 0, w, h);

            if (historyData.length < 2) {
                ctx.fillStyle = '#666';
                ctx.font = '16px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('数据不足', w/2, h/2);
                return;
            }

            const prices = historyData.map(d => d.bid || d.price || d.last_price).filter(p => p > 0);
            if (prices.length < 2) {
                ctx.fillStyle = '#666';
                ctx.font = '16px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText('价格数据不足', w/2, h/2);
                return;
            }

            const minP = Math.min(...prices);
            const maxP = Math.max(...prices);
            const range = maxP - minP || 1;
            const padding = 40;
            const chartW = w - padding * 2;
            const chartH = h - padding * 2;

            // Draw grid
            ctx.strokeStyle = '#222';
            ctx.lineWidth = 1;
            for (let i = 0; i <= 4; i++) {
                const y = padding + (chartH * i / 4);
                ctx.beginPath();
                ctx.moveTo(padding, y);
                ctx.lineTo(w - padding, y);
                ctx.stroke();
                const priceLabel = maxP - (range * i / 4);
                ctx.fillStyle = '#666';
                ctx.font = '12px sans-serif';
                ctx.textAlign = 'right';
                ctx.fillText(priceLabel.toFixed(priceDigits(symbol)), padding - 5, y + 4);
            }

            // Draw price line
            ctx.strokeStyle = '#e94560';
            ctx.lineWidth = 2;
            ctx.beginPath();
            prices.forEach((p, i) => {
                const x = padding + (i / (prices.length - 1)) * chartW;
                const y = padding + chartH - ((p - minP) / range) * chartH;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();

            // Draw confidence line
            ctx.strokeStyle = '#00c853';
            ctx.lineWidth = 1;
            ctx.setLineDash([5, 5]);
            ctx.beginPath();
            historyData.forEach((d, i) => {
                const conf = d.confidence || 0;
                const x = padding + (i / (historyData.length - 1)) * chartW;
                const y = padding + chartH - conf * chartH;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();
            ctx.setLineDash([]);
        }

        function drawStats() {
            if (historyData.length < 2) {
                document.getElementById('historyStats').innerHTML = '<div class="stat-box"><div class="stat-label">数据不足</div></div>';
                return;
            }

            const prices = historyData.map(d => d.bid || d.price).filter(p => p > 0);
            const confidences = historyData.map(d => d.confidence).filter(c => c != null);
            const slopes = historyData.map(d => d.slope).filter(s => s != null);

            const avgConf = confidences.length ? (confidences.reduce((a,b) => a+b, 0) / confidences.length * 100).toFixed(0) : 0;
            const avgSlope = slopes.length ? (slopes.reduce((a,b) => a+b, 0) / slopes.length).toFixed(4) : 0;
            const priceChange = prices.length >= 2 ? (((prices[prices.length-1] - prices[0]) / prices[0] * 100).toFixed(2) : 0;

            document.getElementById('historyStats').innerHTML = 
                '<div class="stat-box"><div class="stat-label">记录数</div><div class="stat-value">' + historyData.length + '</div></div>' +
                '<div class="stat-box"><div class="stat-label">平均置信度</div><div class="stat-value">' + avgConf + '%</div></div>' +
                '<div class="stat-box"><div class="stat-label">平均斜率</div><div class="stat-value">' + (avgSlope > 0 ? '+' : '') + avgSlope + '</div></div>' +
                '<div class="stat-box"><div class="stat-label">价格变化</div><div class="stat-value" style="color:' + (priceChange >= 0 ? '#00c853' : '#ff1744') + '">' + (priceChange >= 0 ? '+' : '') + priceChange + '%</div></div>';
        }

        function stateName(state) {
            const names = {
                'TREND_UP': '单边涨', 'TREND_DOWN': '单边跌',
                'RANGE': '震荡', 'V_SHAPE': 'V型反转',
                'INVERSE_V': '倒V反转', 'UNKNOWN': '未知'
            };
            return names[state] || state;
        }

        function priceDigits(symbol) {
            if (symbol.includes('JPY')) return 3;
            if (symbol.includes('BTC')) return 2;
            return 5;
        }

        function updateTime() {
            document.getElementById('currentTime').textContent = new Date().toLocaleString('zh-CN');
        }

        document.getElementById('historyModal').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });

        loadData();
        updateTime();
        setInterval(loadData, 5000);
        setInterval(updateTime, 1000);
    </script>
</body>
</html>
"""

def get_visualization_page_html() -> str:
    return PAGE_HTML
