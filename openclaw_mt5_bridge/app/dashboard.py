"""Dashboard HTML page for market state visualization."""
from datetime import datetime

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>市场状态面板</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 30px;
            color: #fff;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #0f3460;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .symbol {{
            font-size: 1.4em;
            font-weight: bold;
            color: #e94560;
        }}
        .state-badge {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .state-quiet {{ background: #4a5568; }}
        .state-range {{ background: #2d3748; }}
        .state-candidate_impulse {{ background: #d69e2e; color: #000; }}
        .state-confirmed_impulse {{ background: #38a169; }}
        .state-false_impulse {{ background: #e53e3e; }}
        .direction {{
            font-size: 0.9em;
            color: #a0aec0;
            margin-bottom: 15px;
        }}
        .direction.up {{ color: #48bb78; }}
        .direction.down {{ color: #fc8181; }}
        .direction.none {{ color: #a0aec0; }}
        .scores {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }}
        .score-item {{
            text-align: center;
        }}
        .score-label {{
            font-size: 0.75em;
            color: #a0aec0;
            margin-bottom: 5px;
        }}
        .score-bar {{
            height: 8px;
            background: #2d3748;
            border-radius: 4px;
            overflow: hidden;
        }}
        .score-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }}
        .score-fill.anomaly {{ background: linear-gradient(90deg, #4299e1, #9f7aea); }}
        .score-fill.quality {{ background: linear-gradient(90deg, #48bb78, #38a169); }}
        .score-fill.resonance {{ background: linear-gradient(90deg, #ed8936, #dd6b20); }}
        .score-value {{
            font-size: 0.85em;
            margin-top: 5px;
        }}
        .strategy {{
            background: #1a202c;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 15px;
        }}
        .strategy-title {{
            font-size: 0.75em;
            color: #a0aec0;
            margin-bottom: 8px;
        }}
        .strategy-items {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .strategy-tag {{
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.8em;
        }}
        .strategy-enabled {{ background: #38a169; }}
        .strategy-reduced {{ background: #d69e2e; color: #000; }}
        .strategy-blocked {{ background: #e53e3e; }}
        .summary {{
            background: #1a202c;
            border-radius: 8px;
            padding: 12px;
            font-size: 0.9em;
            line-height: 1.6;
            color: #e2e8f0;
        }}
        .age {{
            font-size: 0.75em;
            color: #718096;
            margin-top: 10px;
        }}
        .regime {{
            font-size: 0.8em;
            color: #a0aec0;
            margin-bottom: 10px;
        }}
        .no-data {{
            text-align: center;
            color: #718096;
            padding: 40px;
        }}
        .updated {{
            text-align: center;
            color: #718096;
            font-size: 0.8em;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <h1>📊 市场状态面板</h1>
    <div id="content" class="grid">
        <div class="no-data">加载中...</div>
    </div>
    <div class="updated" id="updated"></div>

    <script>
        async function loadData() {{
            try {{
                const response = await fetch('/market_state/latest');
                if (!response.ok) throw new Error('Failed to fetch');
                const data = await response.json();
                render(data);
            }} catch (error) {{
                document.getElementById('content').innerHTML = 
                    '<div class="no-data">数据加载失败: ' + error.message + '</div>';
            }}
        }}

        function stateLabel(state) {{
            const labels = {{
                'quiet': '平静',
                'range': '震荡',
                'candidate_impulse': '候选脉冲',
                'confirmed_impulse': '确认脉冲',
                'false_impulse': '假脉冲'
            }};
            return labels[state] || state;
        }}

        function directionLabel(dir) {{
            const labels = {{ 'up': '↑ 上涨', 'down': '↓ 下跌', 'mixed': '↔ 震荡', 'none': '— 无方向' }};
            return labels[dir] || dir;
        }}

        function regimeLabel(regime) {{
            const labels = {{
                'risk_on': '风险偏好',
                'risk_off': '避险情绪',
                'usd_driven': '美元驱动',
                'commodity_driven': '商品驱动',
                'mixed': '混合',
                'unknown': '未知'
            }};
            return labels[regime] || regime;
        }}

        function render(data) {{
            const container = document.getElementById('content');
            
            if (!data.states || Object.keys(data.states).length === 0) {{
                container.innerHTML = '<div class="no-data">暂无数据</div>';
                return;
            }}

            let html = '';
            for (const [symbol, state] of Object.entries(data.states)) {{
                const stateClass = 'state-' + (state.current_state || 'quiet');
                const dirClass = 'direction ' + (state.impulse_direction || 'none');
                
                const perm = state.strategy_permission || {{}};
                const trend = perm.trend || 'blocked';
                const range_mode = perm.range_mode || 'blocked';
                const event = perm.event || 'blocked';

                html += `
                    <div class="card">
                        <div class="card-header">
                            <span class="symbol">${{symbol}}</span>
                            <span class="state-badge ${{stateClass}}">${{stateLabel(state.current_state)}}</span>
                        </div>
                        <div class="regime">${{regimeLabel(state.macro_regime_hint)}} · ${{directionLabel(state.impulse_direction)}}</div>
                        <div class="${{dirClass}}">方向: ${{directionLabel(state.impulse_direction)}}</div>
                        
                        <div class="scores">
                            <div class="score-item">
                                <div class="score-label">异常度</div>
                                <div class="score-bar"><div class="score-fill anomaly" style="width:${{state.anomaly_score}}%"></div></div>
                                <div class="score-value">${{state.anomaly_score}}/100</div>
                            </div>
                            <div class="score-item">
                                <div class="score-label">结构质量</div>
                                <div class="score-bar"><div class="score-fill quality" style="width:${{state.quality_score}}%"></div></div>
                                <div class="score-value">${{state.quality_score}}/100</div>
                            </div>
                            <div class="score-item">
                                <div class="score-label">共振强度</div>
                                <div class="score-bar"><div class="score-fill resonance" style="width:${{state.resonance_score}}%"></div></div>
                                <div class="score-value">${{state.resonance_score}}/100</div>
                            </div>
                        </div>

                        <div class="strategy">
                            <div class="strategy-title">策略权限</div>
                            <div class="strategy-items">
                                <span class="strategy-tag strategy-${{trend}}">趋势 ${{trend}}</span>
                                <span class="strategy-tag strategy-${{range_mode}}">区间 ${{range_mode}}</span>
                                <span class="strategy-tag strategy-${{event}}">事件 ${{event}}</span>
                            </div>
                        </div>

                        <div class="summary">${{state.human_readable_summary_cn || '暂无摘要'}}</div>
                        <div class="age">状态持续: ${{state.state_age_seconds || 0}}秒</div>
                    </div>
                `;
            }}
            
            container.innerHTML = html;
            document.getElementById('updated').textContent = '更新时间: ' + new Date().toLocaleString('zh-CN');
        }}

        loadData();
        setInterval(loadData, 30000);  // Refresh every 30s
    </script>
</body>
</html>
"""


def get_dashboard_html() -> str:
    """Return the dashboard HTML."""
    return DASHBOARD_HTML
