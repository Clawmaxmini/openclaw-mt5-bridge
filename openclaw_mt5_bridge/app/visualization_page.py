"""Market visualization page with history charts."""

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
        .header h1 {
            font-size: 2em;
            color: #fff;
            margin-bottom: 10px;
        }
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
        .tab.active {
            background: #e94560;
            color: #fff;
            border-color: #e94560;
        }
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
        .metric {
            text-align: center;
            padding: 8px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
        }
        .metric-label { font-size: 10px; color: #666; text-transform: uppercase; margin-bottom: 4px; }
        .metric-value { font-size: 14px; font-weight: bold; }
        .confidence-bar {
            height: 4px;
            background: #333;
            border-radius: 2px;
            margin-top: 8px;
            overflow: hidden;
        }
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
        
        /* History Modal */
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
        .modal-close {
            background: none;
            border: none;
            color: #888;
            font-size: 24px;
            cursor: pointer;
        }
        .modal-close:hover { color: #fff; }
        .chart-container {
            background: #0a0a0f;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .chart-canvas { width: 100%; height: 200px; }
        .history-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-top: 16px;
        }
        .stat-box {
            background: rgba(255,255,255,0.05);
            padding: 12px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-label { font-size: 11px; color: #666; margin-bottom: 4px; }
        .stat-value { font-size: 18px; font-weight: bold; }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #555;
            font-size: 12px;
        }
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

    <!-- History Modal -->
    <div class="modal" id="historyModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modalSymbol">XAUUSD 历史</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
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

        let allData = {};
        let allStructures = {};
        let historyData = {};

        async function loadData() {
            try {
                const [pricesRes, structRes] = await Promise.all([
                    fetch(API_BASE + '/csv/prices'),
                    fetch(API_BASE + '/csv/structure/all').catch(() => null)
                ]);

                if (!pricesRes.ok) throw new Error('无法获取价格数据');

                allData = (await pricesRes.json()).prices || {};
                if (structRes && structRes.ok) {
                    allStructures = (await structRes.json()).structures || {};
                }

                renderCategory('metalsGrid', METALS);
                renderCategory('forexGrid', FOREX);
                renderCategory('indicesGrid', INDICES);
                renderCategory('cryptoGrid', CRYPTO);

                document.getElementById('error').style.display = 'none';
            } catch (err) {
                document.getElementById('error').style.display = 'block';
                document.getElementById('error').textContent = '错误: ' + err.message;
            }
        }

        function renderCategory(gridId, symbols) {
            const grid = document.getElementById(gridId);
            grid.innerHTML = symbols.map(s => renderCard(s)).filter(c => c).join('') || '<div class="loading">暂无数据</div>';
        }

        function renderCard(symbol) {
            const price = allData[symbol];
            const struct = allStructures[symbol];
            if (!price) return '';

            const state = struct?.state || 'UNKNOWN';
            const confidence = struct?.confidence || 0;
            const slope = struct?.metrics?.slope || 0;
            const consistency = struct?.metrics?.consistency || 0;

            const bid = price.bid || 0;
            const ask = price.ask || 0;
            const spread = price.spread || 0;

            const confidenceColor = confidence > 0.7 ? '#00c853' : confidence > 0.4 ? '#ff9800' : '#ff5252';

            return '<div class="card">' +
                '<div class="card-header">' +
                    '<span class="symbol" onclick="openHistory(\'' + symbol + '\')">' + symbol + '</span>' +
                    '<span class="state-badge state-' + state + '">' + stateName(state) + '</span>' +
                '</div>' +
                '<div class="price-row">' +
                    '<div><span class="bid">' + bid.toFixed(priceDigits(symbol)) + '</span>' +
                    '<span class="ask">' + ask.toFixed(priceDigits(symbol)) + '</span></div>' +
                '</div>' +
                '<div class="spread">点差: ' + spread.toFixed(1) + ' | ' + (price.last_update ? timeAgo(price.last_update) : '') + '</div>' +
                '<div class="metrics">' +
                    '<div class="metric"><div class="metric-label">置信度</div><div class="metric-value" style="color:' + confidenceColor + '">' + (confidence*100).toFixed(0) + '%</div><div class="confidence-bar"><div class="confidence-fill" style="width:' + (confidence*100) + '%;background:' + confidenceColor + '"></div></div></div>' +
                    '<div class="metric"><div class="metric-label">斜率</div><div class="metric-value">' + (slope > 0 ? '+' : '') + slope.toFixed(4) + '</div></div>' +
                    '<div class="metric"><div class="metric-label">一致性</div><div class="metric-value">' + (consistency*100).toFixed(0) + '%</div></div>' +
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

            // Get price data
            const prices = historyData.map(d => d.bid || 0).filter(p => p > 0);
            const states = historyData.map(d => d.state);

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

            // Draw state colors background
            const stateColors = {
                'TREND_UP': 'rgba(0,200,83,0.1)',
                'TREND_DOWN': 'rgba(255,23,68,0.1)',
                'RANGE': 'rgba(255,152,0,0.1)',
                'V_SHAPE': 'rgba(33,150,243,0.1)',
                'INVERSE_V': 'rgba(156,39,176,0.1)',
            };

            let lastState = states[0];
            let stateStart = 0;
            
            for (let i = 1; i <= states.length; i++) {
                if (i === states.length || states[i] !== lastState) {
                    const color = stateColors[lastState] || 'rgba(100,100,100,0.1)';
                    const x1 = padding + (stateStart / (prices.length - 1)) * chartW;
                    const x2 = padding + ((i-1) / (prices.length - 1)) * chartW;
                    ctx.fillStyle = color;
                    ctx.fillRect(x1, padding, x2 - x1, chartH);
                    if (i < states.length) {
                        lastState = states[i];
                        stateStart = i;
                    }
                }
            }

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

            const prices = historyData.map(d => d.bid).filter(p => p > 0);
            const confidences = historyData.map(d => d.confidence).filter(c => c != null);
            const slopes = historyData.map(d => d.slope).filter(s => s != null);

            const avgConf = confidences.length ? (confidences.reduce((a,b) => a+b, 0) / confidences.length * 100).toFixed(0) : 0;
            const avgSlope = slopes.length ? (slopes.reduce((a,b) => a+b, 0) / slopes.length).toFixed(4) : 0;
            const priceChange = prices.length >= 2 ? (((prices[prices.length-1] - prices[0]) / prices[0] * 100).toFixed(2)) : 0;

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

        function timeAgo(isoTime) {
            if (!isoTime) return '';
            const diff = Date.now() - new Date(isoTime).getTime();
            const secs = Math.floor(diff / 1000);
            if (secs < 60) return secs + '秒前';
            return Math.floor(secs / 60) + '分钟前';
        }

        function updateTime() {
            document.getElementById('currentTime').textContent = new Date().toLocaleString('zh-CN');
        }

        // Click outside modal to close
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
