# Estado del Setup - Bot de Trading

**Fecha**: 26 de Marzo 2026  
**Estado General**: ⚠️ PARCIALMENTE COMPLETADO - Bloqueado por Docker

---

## ✅ Completado

### 1. Entorno Python
- ✅ Virtual environment creado en `venv/`
- ✅ Dependencias instaladas:
  - siliconmetatrader5
  - pandas
  - numpy
  - PyYAML
  - requests
  - matplotlib
- ✅ Archivo `.env` creado (basado en `.env.example`)

### 2. Bugfix y Scripts
- ✅ `core/market_data.py` actualizado con import de `Any` (línea 9)
- ✅ `verify_mt5.py` copiado al proyecto
- ✅ `analyze_backtest.py` copiado (análisis de resultados)
- ✅ `prepare_data.py` copiado (preparación de datos)

### 3. Configuración
- ✅ `config/instruments.yaml` - Configurado para 3 índices (US30, NAS100, SPX500)
- ✅ `config/strategy_params.yaml` - Parámetros de estrategia listos
- ✅ `config/ftmo_rules.yaml` - Reglas FTMO configuradas

---

## ❌ Bloqueado

### 1. Docker + MT5
**Problema**: La imagen Docker `bahadirumutiscimen/pysiliconwine:latest` no existe en Docker Hub.

**Error**:
```
failed to resolve reference "docker.io/bahadirumutiscimen/pysiliconwine:latest": not found
```

**Impacto**: No se puede:
- Levantar contenedor MT5
- Loguearse en cuenta demo FTMO
- Ejecutar `verify_mt5.py` para descubrir nombres de símbolos
- Exportar datos históricos desde MT5

### 2. Verificación de Símbolos
**Bloqueado por**: Falta de MT5 corriendo

Los nombres en `instruments.yaml` están configurados para BlackBull Markets:
- `US30.raw`
- `NAS100.raw`
- `SPX500.raw`

**FTMO puede usar nombres diferentes**. Sin verificar, el backtest podría fallar.

---

## 🔄 Opciones para Continuar

### Opción A: Resolver Docker (Recomendado)
1. Buscar imagen Docker alternativa de MT5
2. Probar: `docker pull alfiej04/metatrader5`
3. Actualizar `docker-compose.yml` con la nueva imagen
4. Levantar contenedor y loguearse en FTMO

### Opción B: Usar Datos de Muestra
1. Conseguir archivos CSV con datos históricos de US30 (H1 y H4)
2. Colocarlos en `data/`
3. Ejecutar backtest directamente con CSVs
4. Validar estrategia sin necesidad de MT5

### Opción C: Instalar Wine + MT5 Localmente
1. Instalar Wine en macOS: `brew install wine-stable`
2. Descargar MT5 para Windows
3. Instalar MT5 via Wine
4. Conectar con `siliconmetatrader5` (requiere configuración adicional)

---

## 📋 Próximos Pasos (Una vez resuelto Docker)

1. **Levantar MT5**
   ```bash
   docker-compose up -d
   ```

2. **Acceder via VNC**
   - URL: http://localhost:8001
   - Loguearse en cuenta demo FTMO
   - Habilitar Algo Trading (Tools → Options → Expert Advisors)

3. **Verificar Símbolos**
   ```bash
   source venv/bin/activate
   python verify_mt5.py --search US30 NAS100 SPX500
   ```

4. **Actualizar `instruments.yaml`**
   - Usar los nombres exactos descubiertos por verify_mt5.py

5. **Exportar Datos**
   ```bash
   python run_backtest.py --export-mt5 US30 --days 730
   ```

6. **Ejecutar Backtest**
   ```bash
   python run_backtest.py \
     --data-h1 data/US30_raw_H1_730d.csv \
     --data-h4 data/US30_raw_H4_730d.csv \
     --instrument US30 \
     --balance 100000 \
     --output data/backtest_US30_results.csv
   ```

7. **Analizar Resultados**
   - Verificar métricas FTMO (Win Rate, Profit Factor, Max DD)
   - Decidir si proceder a paper trading

---

## 🛠️ Comandos Útiles

### Activar Entorno Virtual
```bash
cd "/Users/sebastianosorio/Desktop/trading - IA"
source venv/bin/activate
```

### Verificar Docker
```bash
docker ps                    # Ver contenedores corriendo
docker images               # Ver imágenes disponibles
docker-compose logs -f      # Ver logs del contenedor MT5
```

### Verificar Instalación Python
```bash
python --version            # Debe ser 3.10+
pip list | grep -E "(silicon|pandas|numpy)"
```

---

## 📝 Notas Importantes

1. **GBP/JPY Pospuesto**: Según el plan revisado, NO agregamos GBP/JPY hasta validar US30 primero.

2. **Nombres de Símbolos**: Los nombres en `instruments.yaml` son para BlackBull Markets. FTMO puede usar nombres diferentes (ej: `US30cash`, `US30_m`, etc.).

3. **Backtest sin MT5**: Es posible ejecutar backtest con datos CSV sin necesidad de MT5 corriendo. Solo necesitas los archivos CSV con formato correcto.

4. **Telegram Opcional**: Para backtest, las notificaciones de Telegram son opcionales. Puedes dejar el `.env` sin configurar tokens.

---

## 🆘 Ayuda

Si necesitas ayuda con:
- **Docker**: Ver [QUICKSTART.md](QUICKSTART.md) sección Troubleshooting
- **Estrategia**: Ver [docs/estrategia_sr_indices.md](docs/estrategia_sr_indices.md)
- **Configuración**: Ver [PROYECTO_OVERVIEW.md](PROYECTO_OVERVIEW.md)

---

**Estado**: Esperando resolución de Docker para continuar con verificación MT5 y backtest.
