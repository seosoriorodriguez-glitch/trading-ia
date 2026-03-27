import pandas as pd

df = pd.read_csv('strategies/pivot_scalping/data/backtest_A_nolookahead.csv')

print('='*80)
print('ANALISIS DETALLADO DE TRADES')
print('='*80)

print('\n5 PRIMEROS TRADES:\n')

for i in range(min(5, len(df))):
    row = df.iloc[i]
    entry = row['entry_price']
    exit_p = row['exit_price']
    sl = row['stop_loss']
    tp = row['take_profit']
    pnl = row['pnl']
    pnl_pct = row['pnl_pct']
    status = row['status']
    trade_type = row['type']
    
    risk_pts = abs(entry - sl)
    pnl_pts = (entry - exit_p) if trade_type == 'short' else (exit_p - entry)
    
    print(f'Trade {i+1} ({trade_type.upper()}):')
    print(f'  Entry: {entry:.2f} | Exit: {exit_p:.2f} | SL: {sl:.2f} | TP: {tp:.2f}')
    print(f'  Risk pts: {risk_pts:.2f} | PnL pts: {pnl_pts:.2f}')
    print(f'  PnL USD: ${pnl:.2f} | PnL %: {pnl_pct:.4f}%')
    print(f'  Status: {status}')
    
    if pnl_pts != 0:
        implied_size = abs(pnl / pnl_pts)
        print(f'  Implied size: {implied_size:.4f}')
        
        # Calcular size esperado
        risk_usd = 100000 * 0.005  # $500
        expected_size = risk_usd / risk_pts
        print(f'  Expected size (risk-based): {expected_size:.4f}')
        print(f'  Size usado / Size esperado: {implied_size / expected_size:.2f}x')
    print()

print('='*80)
print('SUMARIO GENERAL')
print('='*80)

print(f'\nTotal trades: {len(df)}')
print(f'Wins: {len(df[df.pnl > 0])} ({len(df[df.pnl > 0])/len(df)*100:.1f}%)')
print(f'Losses: {len(df[df.pnl <= 0])} ({len(df[df.pnl <= 0])/len(df)*100:.1f}%)')

print(f'\nTotal PnL USD: ${df["pnl"].sum():.2f}')
print(f'Avg PnL per trade: ${df["pnl"].mean():.2f}')
print(f'Avg Win: ${df[df.pnl > 0]["pnl"].mean():.2f}')
print(f'Avg Loss: ${df[df.pnl <= 0]["pnl"].mean():.2f}')

# Calcular PnL en puntos
df['pnl_points'] = df.apply(
    lambda row: (row['entry_price'] - row['exit_price']) if row['type'] == 'short' 
    else (row['exit_price'] - row['entry_price']), 
    axis=1
)

print(f'\nAvg Win (points): {df[df.pnl > 0]["pnl_points"].mean():.2f}')
print(f'Avg Loss (points): {df[df.pnl <= 0]["pnl_points"].mean():.2f}')

# Calcular PF en puntos
gross_profit_pts = df[df.pnl_points > 0]['pnl_points'].sum()
gross_loss_pts = abs(df[df.pnl_points <= 0]['pnl_points'].sum())
pf_points = gross_profit_pts / gross_loss_pts if gross_loss_pts > 0 else 0

print(f'\nProfit Factor (USD): {df[df.pnl > 0]["pnl"].sum() / abs(df[df.pnl <= 0]["pnl"].sum()):.2f}')
print(f'Profit Factor (Points): {pf_points:.2f}')

# Verificar spread
print(f'\n' + '='*80)
print('VERIFICACION DE SPREAD')
print('='*80)
print('\nNOTA: El spread NO se está restando en el código actual.')
print('Cada trade debería tener -2 puntos de spread.')
print(f'Con {len(df)} trades, eso son {len(df) * 2} puntos = ~${len(df) * 2:.2f} en costos.')
