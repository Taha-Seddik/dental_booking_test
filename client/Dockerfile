FROM node:20-alpine AS builder
WORKDIR /app

# Copy package.json (and package-lock.json if it exists)
COPY package*.json ./

RUN npm install

# Copy the rest of the app
COPY . .

# Build the Next.js app
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Copy built app from builder
COPY --from=builder /app ./

EXPOSE 3000

# Start Next.js in production mode
CMD ["npm", "start"]
