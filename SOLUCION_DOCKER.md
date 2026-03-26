# 🐳 Solución al Problema de Docker MT5

**Problema**: La imagen `bahadirumutiscimen/pysiliconwine:latest` no existe en Docker Hub.

**Estado**: Bloqueando el setup completo del bot.

---

## 🔍 Diagnóstico

```bash
Error: failed to resolve reference "docker.io/bahadirumutiscimen/pysiliconwine:latest": not found
```

**Causa**: La imagen especificada en `docker-compose.yml` fue eliminada o nunca existió públicamente.

---

## ✅ Solución Recomendada: Usar Imagen Alternativa

### Paso 1: Probar Imágenes Alternativas

Hay varias imágenes de MT5 en Docker Hub. Vamos a probar la más popular:

```bash
# Opción 1: alfiej04/metatrader5 (recomendada - tiene 1 star)
docker pull alfiej04/metatrader5:latest

# Si falla, probar Opción 2:
docker pull lucaorioli/metatrader5:latest

# Si falla, probar Opción 3:
docker pull elestio/metatrader5:latest
```

### Paso 2: Actualizar docker-compose.yml

Una vez que una imagen se descargue exitosamente, actualizar el archivo:

```yaml
# docker-compose.yml
services:
  mt5:
    image: alfiej04/metatrader5:latest  # ← Cambiar esta línea
    container_name: mt5-trading
    ports:
      - "8001:8001"
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 8G
```

### Paso 3: Levantar Contenedor

```bash
cd "/Users/sebastianosorio/Desktop/trading - IA"
docker-compose up -d
```

### Paso 4: Verificar que Está Corriendo

```bash
docker ps | grep mt5-trading
```

**Salida esperada**:
```
CONTAINER ID   IMAGE                          STATUS         PORTS
abc123def456   alfiej04/metatrader5:latest   Up 10 seconds  0.0.0.0:8001->8001/tcp
```

### Paso 5: Acceder a MT5

```bash
# Abrir en navegador
open http://localhost:8001
```

**Nota**: Algunas imágenes usan VNC, otras usan RDP. Si no funciona el puerto 8001, probar:
- http://localhost:5900 (VNC)
- http://localhost:3389 (RDP)

---

## 🔧 Solución Alternativa 1: Construir Imagen Propia

Si ninguna imagen pública funciona, podemos construir una:

### Crear Dockerfile

```dockerfile
# Dockerfile
FROM ubuntu:22.04

# Instalar Wine y dependencias
RUN apt-get update && apt-get install -y \
    wine \
    wine64 \
    wget \
    xvfb \
    x11vnc \
    && rm -rf /var/lib/apt/lists/*

# Descargar MT5
RUN wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe

# Instalar MT5
RUN wine mt5setup.exe /auto

# Exponer puerto VNC
EXPOSE 5900

CMD ["x11vnc", "-forever", "-usepw", "-create"]
```

### Construir y Correr

```bash
cd "/Users/sebastianosorio/Desktop/trading - IA"
docker build -t mt5-custom .
docker run -d --name mt5-trading -p 8001:5900 mt5-custom
```

**Advertencia**: Esta solución es más compleja y puede requerir ajustes.

---

## 🔧 Solución Alternativa 2: Wine Nativo en macOS

Si Docker sigue sin funcionar, instalar Wine directamente:

### Paso 1: Instalar Wine

```bash
brew install wine-stable
```

### Paso 2: Descargar MT5

```bash
cd ~/Downloads
wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe
```

### Paso 3: Instalar MT5

```bash
wine mt5setup.exe
```

### Paso 4: Configurar siliconmetatrader5

Editar `core/market_data.py` para conectar a Wine local en lugar de Docker:

```python
# En MT5Connection.__init__
self._host = "localhost"  # Ya está así
self._port = 8001  # Cambiar a puerto de Wine (verificar cual usa)
```

**Desventaja**: Wine en Apple Silicon puede tener problemas de compatibilidad.

---

## 🔧 Solución Alternativa 3: Usar Datos CSV (Temporal)

Si necesitas validar la estrategia YA, sin esperar Docker:

### Paso 1: Descargar Datos de US30

Fuentes:
- **Dukascopy**: https://www.dukascopy.com/swiss/english/marketwatch/historical/
- **TrueFX**: https://www.truefx.com/
- **MetaQuotes**: Desde MT5 en Windows (si tienes acceso)

### Paso 2: Convertir a Formato Correcto

Los datos deben tener este formato:

```csv
time,open,high,low,close,volume
2024-03-26 00:00:00,44850.5,44920.3,44800.1,44890.7,1250
2024-03-26 01:00:00,44890.7,44950.2,44870.4,44930.1,1180
```

Puedes usar el script `prepare_data.py` (ya copiado) para convertir formatos.

### Paso 3: Colocar en data/

```bash
# Crear carpeta si no existe
mkdir -p "/Users/sebastianosorio/Desktop/trading - IA/data"

# Copiar archivos
cp ~/Downloads/US30_H1.csv "/Users/sebastianosorio/Desktop/trading - IA/data/"
cp ~/Downloads/US30_H4.csv "/Users/sebastianosorio/Desktop/trading - IA/data/"
```

### Paso 4: Ejecutar Backtest

```bash
cd "/Users/sebastianosorio/Desktop/trading - IA"
source venv/bin/activate

python run_backtest.py \
  --data-h1 data/US30_H1.csv \
  --data-h4 data/US30_H4.csv \
  --instrument US30 \
  --balance 100000 \
  --output data/backtest_US30_results.csv
```

**Ventaja**: Puedes validar la estrategia mientras resuelves Docker.

**Desventaja**: Los datos pueden no ser de FTMO, y los nombres de símbolos no están verificados.

---

## 🎯 Recomendación Final

**Para tu caso específico**:

1. **Primero**: Probar imágenes Docker alternativas (5-10 minutos)
   ```bash
   docker pull alfiej04/metatrader5:latest
   ```

2. **Si falla**: Usar datos CSV temporalmente (30 minutos)
   - Descargar datos de Dukascopy
   - Ejecutar backtest
   - Validar estrategia

3. **Mientras tanto**: Investigar solución Docker definitiva
   - Contactar comunidad de trading algorítmico
   - Buscar en GitHub imágenes de MT5
   - Considerar construir imagen propia

---

## 📊 Comparación de Opciones

| Opción | Tiempo | Complejidad | Ventajas | Desventajas |
|--------|--------|-------------|----------|-------------|
| **Imagen alternativa** | 10 min | Baja | Rápido, completo | Puede no existir |
| **Construir imagen** | 1-2 horas | Alta | Control total | Requiere conocimiento Docker |
| **Wine nativo** | 30 min | Media | Sin Docker | Bugs en Apple Silicon |
| **Datos CSV** | 30 min | Baja | Rápido para validar | No verifica símbolos |

---

## 🆘 Si Nada Funciona

**Plan B**: Usar Windows

Si tienes acceso a una máquina Windows (física o VM):

1. Instalar MT5 directamente
2. Instalar Python + dependencias
3. Usar librería `MetaTrader5` nativa (no `siliconmetatrader5`)
4. Ejecutar el bot desde Windows

**Ventaja**: MT5 es nativo en Windows, sin problemas de compatibilidad.

**Desventaja**: Requiere máquina Windows.

---

## 📝 Checklist de Troubleshooting

Antes de pedir ayuda, verificar:

- [ ] Docker Desktop está corriendo
- [ ] Ejecutaste `docker pull` para la imagen
- [ ] El puerto 8001 no está ocupado (`lsof -i :8001`)
- [ ] Tienes suficiente espacio en disco (`df -h`)
- [ ] Docker tiene permisos suficientes
- [ ] Reiniciaste Docker Desktop
- [ ] Probaste las 3 imágenes alternativas
- [ ] Revisaste logs: `docker logs mt5-trading`

---

## 📞 Recursos Adicionales

**Comunidades**:
- r/algotrading (Reddit)
- Stack Overflow: [metatrader5] tag
- GitHub: Buscar "metatrader5 docker"

**Documentación**:
- Docker: https://docs.docker.com/
- Wine: https://www.winehq.org/
- MT5: https://www.metatrader5.com/

---

**Última actualización**: 26 de Marzo 2026  
**Estado**: Esperando resolución del usuario
