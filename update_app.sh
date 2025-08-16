#!/bin/bash

# Configurações
REPO_DIR=~/mapeamento_criminal
IMAGE_NAME=mapa-criminal-streamlit
CONTAINER_NAME=meu-app-mapa
HOST_PORT=8052
CONTAINER_PORT=8502

echo "🔄 Atualizando repositório..."
cd $REPO_DIR || { echo "Erro: pasta $REPO_DIR não existe"; exit 1; }
git pull origin main

echo "📦 Build da imagem Docker..."
docker build -t $IMAGE_NAME:latest .

echo "🛑 Parando e removendo container antigo (se existir)..."
docker stop $CONTAINER_NAME 2>/dev/null
docker rm $CONTAINER_NAME 2>/dev/null

echo "🚀 Rodando container atualizado..."
docker run -d -p $HOST_PORT:$CONTAINER_PORT --name $CONTAINER_NAME $IMAGE_NAME:latest

echo "✅ Atualização concluída! Acesse o app em http://SEU-IP:$HOST_PORT"
