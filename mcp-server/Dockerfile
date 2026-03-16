# Imagen base liviana de Node.js
FROM node:20-alpine

# Directorio de trabajo
WORKDIR /app

# Copiar package files primero (aprovecha caché de Docker)
COPY package*.json ./

# Instalar solo dependencias de producción
RUN npm ci --only=production

# Copiar el resto del código
COPY . .

# Cloud Run espera el puerto en la variable PORT
ENV PORT=8080
EXPOSE 8080

# Arrancar el servidor
CMD ["node", "mcp_server.js"]
