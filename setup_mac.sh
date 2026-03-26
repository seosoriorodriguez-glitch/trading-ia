#!/bin/bash
# ============================================================
# SR Trading Bot — Setup para macOS (Apple Silicon / Intel)
# ============================================================
# Este script instala todo lo necesario para correr el bot
# en tu Mac con MT5 dentro de Docker.
#
# Uso: chmod +x setup_mac.sh && ./setup_mac.sh
# ============================================================

set -e

echo "==========================================="
echo " SR Trading Bot — Setup macOS"
echo "==========================================="
echo ""

# --- 1. Verificar Homebrew ---
if ! command -v brew &> /dev/null; then
    echo "📦 Instalando Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "✅ Homebrew ya instalado"
fi

# --- 2. Instalar Docker y dependencias ---
echo ""
echo "📦 Instalando Docker, Colima, QEMU..."
brew install colima docker qemu lima 2>/dev/null || true

# --- 3. Verificar Docker Desktop ---
# Si el usuario tiene Docker Desktop, no necesita Colima
if docker info &> /dev/null 2>&1; then
    echo "✅ Docker ya está corriendo (Docker Desktop detectado)"
    DOCKER_READY=true
else
    echo "🐳 Iniciando Colima con emulación x86_64..."
    echo "   (Esto permite correr MT5 Windows en tu Mac)"
    colima delete -f 2>/dev/null || true
    colima start --arch x86_64 --vm-type=qemu --cpu 4 --memory 8
    DOCKER_READY=true
fi

# --- 4. Descargar imagen de MT5 para Docker ---
echo ""
echo "📥 Descargando imagen de MT5 para Docker..."
echo "   (Esto puede tardar unos minutos la primera vez)"
docker pull bahadirumutiscimen/pysiliconwine:latest

# --- 5. Crear contenedor de MT5 ---
echo ""
echo "🚀 Creando contenedor MT5..."

# Detener contenedor anterior si existe
docker stop mt5-trading 2>/dev/null || true
docker rm mt5-trading 2>/dev/null || true

docker run -d \
    --name mt5-trading \
    -p 8001:8001 \
    --restart unless-stopped \
    bahadirumutiscimen/pysiliconwine:latest

echo "✅ Contenedor MT5 corriendo en puerto 8001"
echo "   El contenedor se reinicia automáticamente si se cae."

# --- 6. Python virtual environment ---
echo ""
echo "🐍 Configurando Python..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Entorno virtual creado"
fi

source venv/bin/activate

# --- 7. Instalar dependencias Python ---
echo ""
echo "📦 Instalando dependencias Python..."
pip install --upgrade pip
pip install siliconmetatrader5
pip install pandas numpy PyYAML requests matplotlib

echo ""
echo "==========================================="
echo " ✅ Setup completado!"
echo "==========================================="
echo ""
echo " Próximos pasos:"
echo ""
echo " 1. Abre MT5 en el contenedor Docker y logueate"
echo "    con tu cuenta de broker (FTMO / BlackBull / etc.)"
echo "    → Accede via VNC: http://localhost:8001"
echo ""
echo " 2. Configura tu .env:"
echo "    cp .env.example .env"
echo "    nano .env  # Agrega tokens de Telegram"
echo ""
echo " 3. Verifica la conexión:"
echo "    python -c \"from siliconmetatrader5 import MetaTrader5; mt5=MetaTrader5(host='localhost',port=8001); print('Ping:', mt5.ping())\""
echo ""
echo " 4. Corre el backtest:"
echo "    python run_backtest.py --from-mt5 US30 --days 365"
echo ""
echo " 5. Corre el bot en simulación:"
echo "    python main.py"
echo ""
