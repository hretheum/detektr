# 🎨 Frontend Services Deployment Guide

This guide covers deploying frontend applications (React, Vue, Angular) as part of the Detektor system.

## Prerequisites

- [ ] Service name decided (e.g., `management-ui`)
- [ ] Port allocated for serving static files (typically 80XX range)
- [ ] Framework chosen (React/Vue/Angular/Vanilla)

## Frontend Build Strategy

### Multi-Stage Docker Build

Frontend services use multi-stage builds to:
1. Build the application in a Node.js environment
2. Serve static files using nginx

### Example Dockerfile

```dockerfile
# Stage 1: Build
FROM node:18-alpine as builder

WORKDIR /app

# Cache dependencies
COPY package*.json ./
RUN npm ci --only=production

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

## Nginx Configuration

Create `nginx.conf` for your frontend:

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Cache static assets
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API proxy (if needed)
    location /api {
        proxy_pass http://api-gateway:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy (if needed)
    location /ws {
        proxy_pass http://api-gateway:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # SPA routing - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## Environment Configuration

### Build-Time Variables

For build-time configuration, use `.env.production`:

```bash
# .env.production
VITE_API_URL=http://nebula:8000
VITE_WS_URL=ws://nebula:8000/ws
VITE_APP_TITLE=Detektor Management
```

### Runtime Variables

For runtime configuration, use a config injection script:

```html
<!-- public/index.html -->
<script>
  window.ENV = {
    API_URL: '%VITE_API_URL%',
    WS_URL: '%VITE_WS_URL%',
    APP_TITLE: '%VITE_APP_TITLE%'
  };
</script>
```

## Service Structure

```
services/management-ui/
├── src/                    # Source code
│   ├── components/         # React/Vue components
│   ├── pages/             # Page components
│   ├── services/          # API clients
│   └── utils/             # Utilities
├── public/                # Static assets
├── tests/                 # Tests
├── Dockerfile             # Multi-stage build
├── nginx.conf             # Nginx configuration
├── package.json           # Dependencies
└── vite.config.js         # Build configuration
```

## Build Optimization

### 1. Code Splitting

```javascript
// Lazy load routes
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));
```

### 2. Tree Shaking

```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          charts: ['chart.js', 'react-chartjs-2']
        }
      }
    }
  }
}
```

### 3. Asset Optimization

```bash
# In Dockerfile
RUN npm run build && \
    find dist -name "*.js" -exec gzip -k {} \; && \
    find dist -name "*.css" -exec gzip -k {} \;
```

## Docker Compose Integration

```yaml
management-ui:
  image: ghcr.io/hretheum/detektr/management-ui:latest
  container_name: management-ui
  restart: unless-stopped
  ports:
    - "8080:80"
  environment:
    # Runtime environment variables if needed
    API_URL: http://api-gateway:8000
  networks:
    - detektor-network
  depends_on:
    - api-gateway
  healthcheck:
    test: ["CMD", "wget", "--spider", "-q", "http://localhost"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## Testing Frontend Services

### Unit Tests

```javascript
// src/components/Dashboard.test.jsx
import { render, screen } from '@testing-library/react';
import Dashboard from './Dashboard';

test('renders dashboard title', () => {
  render(<Dashboard />);
  const title = screen.getByText(/Dashboard/i);
  expect(title).toBeInTheDocument();
});
```

### E2E Tests

```javascript
// tests/e2e/dashboard.spec.js
import { test, expect } from '@playwright/test';

test('dashboard loads', async ({ page }) => {
  await page.goto('http://localhost:8080');
  await expect(page).toHaveTitle(/Detektor/);
  await expect(page.locator('h1')).toContainText('Dashboard');
});
```

## Performance Optimization

### 1. Enable HTTP/2

```nginx
server {
    listen 80 http2;
    # ... rest of config
}
```

### 2. Preload Critical Resources

```html
<link rel="preload" href="/fonts/main.woff2" as="font" crossorigin>
<link rel="preload" href="/js/app.js" as="script">
```

### 3. Service Worker for Offline

```javascript
// src/sw.js
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('v1').then((cache) => {
      return cache.addAll([
        '/',
        '/index.html',
        '/static/css/main.css',
        '/static/js/main.js'
      ]);
    })
  );
});
```

## Monitoring Frontend Performance

### 1. Add RUM (Real User Monitoring)

```javascript
// src/utils/monitoring.js
export function trackPageLoad() {
  if (window.performance) {
    const perfData = window.performance.timing;
    const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;

    // Send to monitoring service
    fetch('/api/metrics/rum', {
      method: 'POST',
      body: JSON.stringify({
        page_load_time: pageLoadTime,
        url: window.location.href
      })
    });
  }
}
```

### 2. Error Tracking

```javascript
// src/utils/errorBoundary.jsx
class ErrorBoundary extends React.Component {
  componentDidCatch(error, errorInfo) {
    // Log to monitoring service
    console.error('UI Error:', error, errorInfo);

    fetch('/api/errors', {
      method: 'POST',
      body: JSON.stringify({
        error: error.toString(),
        stack: error.stack,
        component: errorInfo.componentStack
      })
    });
  }
}
```

## Security Best Practices

### 1. Content Security Policy

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self' ws://nebula:8000";
```

### 2. Security Headers

```nginx
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Referrer-Policy "strict-origin-when-cross-origin";
```

## Deployment Checklist

- [ ] Frontend builds successfully locally
- [ ] All tests pass
- [ ] Dockerfile uses multi-stage build
- [ ] nginx.conf configured correctly
- [ ] Environment variables documented
- [ ] Added to GitHub workflows
- [ ] Added to docker-compose.yml
- [ ] Security headers configured
- [ ] Caching strategy implemented
- [ ] Error tracking setup
- [ ] Performance monitoring enabled

## Common Issues

### Build Failures

```bash
# Clear npm cache
npm cache clean --force

# Use specific Node version
FROM node:18.17.0-alpine as builder
```

### Large Bundle Size

```bash
# Analyze bundle
npm run build -- --analyze

# Check for duplicates
npm ls --depth=0
```

### CORS Issues

```nginx
# In nginx.conf
location /api {
    # Add CORS headers
    add_header 'Access-Control-Allow-Origin' '$http_origin' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Accept,Authorization,Content-Type' always;

    if ($request_method = 'OPTIONS') {
        return 204;
    }

    proxy_pass http://api-gateway:8000;
}
```

## Next Steps

1. Set up CI/CD pipeline for frontend tests
2. Configure CDN for static assets
3. Implement A/B testing framework
4. Add performance budgets
5. Set up synthetic monitoring
