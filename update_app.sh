#!/bin/bash

# Caminho do projeto
APP_DIR=~/mapeamento_criminal
APP_NAME=meu-app-mapa
IMAGE_NAME=mapa-criminal-streamlit:latest

echo "🔄 Atualizando repositório..."
cd $APP_DIR || exit
git pull origin main

echo "🔨 Build da imagem Docker..."
docker build -t $IMAGE_NAME .

echo "🛑 Parando e removendo container antigo (se existir)..."
docker stop $APP_NAME 2>/dev/null || true
docker rm $APP_NAME 2>/dev/null || true

echo "🚀 Rodando container atualizado na porta 8052..."
docker run -d \
  -p 8052:8501 \
  --name $APP_NAME \
  $IMAGE_NAME \
  streamlit run app.py --server.address=0.0.0.0 --server.port=8501

echo "✅ Atualização concluída! Acesse o app em http://SEU-IP:8052"
